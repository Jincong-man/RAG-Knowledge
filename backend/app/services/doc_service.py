"""文档处理服务：解析、分块、嵌入、存储"""
import logging
import asyncio
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.document import Document, DocumentStatus
from app.config import settings
from app.rag.embeddings import get_embedding_model
from app.rag.vectorstore import get_vectorstore
from app.rag.splitter import get_splitter

logger = logging.getLogger(__name__)


def load_document_content(file_path: str, file_type: str) -> str:
    """根据文件类型解析文档内容"""
    path = Path(file_path)

    if file_type == ".txt" or file_type == ".md":
        raw = path.read_bytes()
        import chardet
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        return raw.decode(encoding, errors="replace")

    elif file_type == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    elif file_type == ".docx":
        from docx import Document as DocxDoc
        doc = DocxDoc(str(path))
        return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())

    elif file_type in (".xlsx", ".csv"):
        import openpyxl
        wb = openpyxl.load_workbook(str(path), read_only=True)
        rows = []
        for sheet in wb.worksheets:
            headers = None
            for row in sheet.iter_rows(values_only=True):
                if headers is None:
                    headers = [str(h) if h else "" for h in row]
                    continue
                values = [str(v) if v is not None else "" for v in row]
                # 每行拼成 "表头:值, 表头:值, ..." 格式
                row_text = ", ".join(f"{h}: {v}" for h, v in zip(headers, values) if v)
                if row_text.strip():
                    rows.append(row_text)
        wb.close()
        return "\n".join(rows)

    elif file_type in (".html", ".htm"):
        raw = path.read_bytes()
        import chardet
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        content = raw.decode(encoding, errors="replace")
        # 简单去标签
        import re
        return re.sub(r"<[^>]+>", " ", content)

    else:
        raw = path.read_bytes()
        import chardet
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        return raw.decode(encoding, errors="replace")


async def process_document(doc_id: int, file_path: str, file_type: str):
    """异步处理文档：解析 → 分块 → 嵌入 → 存入Chroma"""
    try:
        # 1. 解析文档内容
        logger.info(f"开始处理文档 id={doc_id}")
        content = load_document_content(file_path, file_type)
        if not content.strip():
            raise ValueError("文档内容为空")

        # 2. 分块
        splitter = get_splitter()
        chunks = splitter.split_text(content)
        logger.info(f"文档 id={doc_id} 分块完成: {len(chunks)} 个块")

        # 3. 构建LangChain Document对象
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

        # 4. 存入Chroma
        vectorstore = await get_vectorstore()
        await asyncio.to_thread(vectorstore.add_documents, lc_docs)
        logger.info(f"文档 id={doc_id} 向量存储完成: {len(lc_docs)} 个向量")

        # 5. 更新数据库状态
        async with async_session_factory() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = DocumentStatus.READY
                doc.chunk_count = len(chunks)
                db.add(doc)
                await db.commit()
        logger.info(f"文档 id={doc_id} 处理完成")

    except Exception as e:
        logger.error(f"文档 id={doc_id} 处理失败: {e}", exc_info=True)
        async with async_session_factory() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)[:500]
                db.add(doc)
                await db.commit()
