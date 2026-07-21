"""知识库管理路由：文档上传、列表、删除（仅管理员）"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentOut
from app.core.deps import require_admin
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".html", ".htm", ".md", ".csv"}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库（仅管理员）"""
    # 检查文件扩展名
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，支持: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    # 检查文件大小
    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制: {settings.MAX_FILE_SIZE_MB}MB")

    # 保存文件到磁盘
    save_path = settings.upload_dir_path / file.filename
    with open(save_path, "wb") as f:
        f.write(content)

    # 创建数据库记录
    doc = Document(
        filename=file.filename,
        file_type=ext,
        file_size=file_size,
        upload_user_id=current_user.id,
        status=DocumentStatus.PROCESSING,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # 后台异步处理文档
    from app.services.doc_service import process_document
    background_tasks.add_task(process_document, doc.id, str(save_path), ext)

    return doc


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取所有知识库文档列表"""
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/documents/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    doc_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除知识库文档及其向量数据"""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除Chroma中的向量
    try:
        from app.rag.vectorstore import delete_document_chunks
        await delete_document_chunks(doc_id)
    except Exception as e:
        logger.warning(f"删除向量数据时出错: {e}")

    # 删除磁盘文件
    file_path = settings.upload_dir_path / doc.filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(doc)
    return {"message": f"文档 '{doc.filename}' 已删除"}


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库统计信息"""
    total = await db.execute(select(func.count(Document.id)))
    ready = await db.execute(
        select(func.count(Document.id)).where(Document.status == DocumentStatus.READY)
    )
    total_chunks = await db.execute(select(func.coalesce(func.sum(Document.chunk_count), 0)))

    return {
        "total_documents": total.scalar(),
        "ready_documents": ready.scalar(),
        "total_chunks": total_chunks.scalar(),
    }
