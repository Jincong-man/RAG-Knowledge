"""演示数据播种：知识库为空时自动导入 demo_data 目录下的示例文档"""
import logging
import shutil
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models.document import Document, DocumentStatus
from app.services.doc_service import process_document

logger = logging.getLogger(__name__)

# backend/app/services/seed_service.py -> backend/demo_data
DEMO_DATA_DIR = Path(__file__).resolve().parents[2] / "demo_data"


async def seed_demo_documents(admin_id: int) -> None:
    """如果知识库中没有任何文档，则导入内置示例文档（仅用于公开演示环境）"""
    if not DEMO_DATA_DIR.exists():
        logger.info("未找到 demo_data 目录，跳过演示数据播种")
        return

    async with async_session_factory() as db:
        result = await db.execute(select(Document.id).limit(1))
        if result.scalar_one_or_none() is not None:
            logger.info("知识库已有文档，跳过演示数据播种")
            return

    demo_files = sorted(DEMO_DATA_DIR.glob("*.md"))
    if not demo_files:
        logger.info("demo_data 目录为空，跳过演示数据播种")
        return

    logger.info(f"开始导入 {len(demo_files)} 个演示文档...")
    for src in demo_files:
        dest = settings.upload_dir_path / src.name
        shutil.copyfile(src, dest)

        async with async_session_factory() as db:
            doc = Document(
                filename=src.name,
                file_type=".md",
                file_size=dest.stat().st_size,
                upload_user_id=admin_id,
                status=DocumentStatus.PROCESSING,
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            doc_id = doc.id

        await process_document(doc_id, str(dest), ".md")

    logger.info("演示文档导入完成")
