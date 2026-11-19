"""Chroma向量数据库管理"""
import logging
from typing import Optional

from app.config import settings
from app.rag.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

_collection_name = "knowledge_base"
_vectorstore = None


def _init_vectorstore():
    """同步初始化Chroma向量库（供请求和启动预热共用）"""
    global _vectorstore
    if _vectorstore is None:
        logger.info(f"正在初始化Chroma向量库: {settings.CHROMA_PERSIST_DIR}")
        from langchain_community.vectorstores import Chroma
        embeddings = get_embedding_model()
        _vectorstore = Chroma(
            collection_name=_collection_name,
            embedding_function=embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        logger.info("Chroma向量库初始化完成")
    return _vectorstore


async def get_vectorstore():
    """获取Chroma向量库实例（单例）"""
    return _init_vectorstore()


async def delete_document_chunks(doc_id: int):
    """删除指定文档的所有向量块"""
    vectorstore = await get_vectorstore()
    try:
        # 通过metadata过滤删除
        collection = vectorstore._collection
        collection.delete(where={"doc_id": doc_id})
        logger.info(f"已删除文档 doc_id={doc_id} 的所有向量块")
    except Exception as e:
        logger.error(f"删除向量块失败: {e}")
        raise


async def get_retriever(top_k: int = None):
    """获取检索器"""
    vectorstore = await get_vectorstore()
    k = top_k or settings.RETRIEVAL_TOP_K
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )
