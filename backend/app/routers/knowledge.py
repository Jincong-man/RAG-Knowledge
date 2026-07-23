"""知识库管理路由：文档上传、列表、删除（仅管理员）"""
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_factory
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentOut
from app.core.deps import require_admin
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".html", ".htm", ".md", ".csv"}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库（仅管理员）- 同步处理，确保状态正确更新"""
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
    doc_id = doc.id

    # get_db会自动commit，先把PROCESSING状态提交
    # 返回后立即在独立session中处理文档

    # 异步处理文档（在独立session中，避免锁冲突）
    import asyncio
    asyncio.create_task(_process_and_update(doc_id, str(save_path), ext))

    return doc


async def _process_and_update(doc_id: int, file_path: str, file_type: str):
    """在独立session中处理文档并更新状态"""
    import asyncio
    from app.services.doc_service import load_document_content, get_splitter
    from pathlib import Path

    try:
        # 1. 解析文档
        content = await asyncio.to_thread(load_document_content, file_path, file_type)
        if not content.strip():
            raise ValueError("文档内容为空")

        # 2. 分块
        splitter = get_splitter()
        chunks = await asyncio.to_thread(splitter.split_text, content)
        logger.info(f"文档 id={doc_id} 分块完成: {len(chunks)} 个块")

        # 3. 存入Chroma
        from langchain_core.documents import Document as LCDocument
        lc_docs = [
            LCDocument(
                page_content=chunk,
                metadata={
                    "doc_id": doc_id,
                    "filename": Path(file_path).name,
                    "chunk_index": i,
                    "file_type": file_type,
                },
            )
            for i, chunk in enumerate(chunks)
        ]
        from app.rag.vectorstore import get_vectorstore
        vectorstore = await get_vectorstore()
        await asyncio.to_thread(vectorstore.add_documents, lc_docs)
        logger.info(f"文档 id={doc_id} 向量存储完成: {len(lc_docs)} 个向量")

        # 4. 更新状态（重试机制）
        for attempt in range(5):
            try:
                await asyncio.sleep(1 + attempt)  # 递增等待
                async with async_session_factory() as update_db:
                    await update_db.execute(
                        update(Document)
                        .where(Document.id == doc_id)
                        .values(status=DocumentStatus.READY, chunk_count=len(chunks))
                    )
                    await update_db.commit()
                logger.info(f"文档 id={doc_id} 处理完成，状态已更新为READY")
                return
            except Exception as e:
                logger.warning(f"文档 id={doc_id} 状态更新重试 {attempt+1}/5: {e}")
        logger.error(f"文档 id={doc_id} 状态更新最终失败")

    except Exception as e:
        logger.error(f"文档 id={doc_id} 处理失败: {e}", exc_info=True)
        try:
            async with async_session_factory() as update_db:
                await update_db.execute(
                    update(Document)
                    .where(Document.id == doc_id)
                    .values(status=DocumentStatus.FAILED, error_message=str(e)[:500])
                )
                await update_db.commit()
        except Exception:
            pass


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
