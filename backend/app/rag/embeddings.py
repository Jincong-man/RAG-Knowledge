"""Embedding模型封装 - 使用ModelScope下载bge-small-zh-v1.5"""
import logging
import os
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_model = None
MODEL_LOCAL_DIR = Path(__file__).parent.parent.parent / "models" / "bge-small-zh-v1.5"


def _download_model():
    """从ModelScope下载模型（如果本地不存在）"""
    if MODEL_LOCAL_DIR.exists() and any(MODEL_LOCAL_DIR.glob("*.bin")):
        logger.info(f"使用本地模型: {MODEL_LOCAL_DIR}")
        return str(MODEL_LOCAL_DIR)

    logger.info("从ModelScope下载bge-small-zh-v1.5模型...")
    from modelscope import snapshot_download
    model_dir = snapshot_download(
        "BAAI/bge-small-zh-v1.5",
        cache_dir=str(Path(__file__).parent.parent.parent / "models"),
    )
    logger.info(f"模型下载完成: {model_dir}")
    return model_dir


def _load_model():
    """加载embedding模型（懒加载，首次调用时初始化）"""
    global _model
    if _model is None:
        model_path = _download_model()
        logger.info(f"正在加载Embedding模型: {model_path} ...")
        from langchain_community.embeddings import HuggingFaceBgeEmbeddings
        _model = HuggingFaceBgeEmbeddings(
            model_name=model_path,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
            query_instruction="为这个句子生成表示以用于检索相关文章：",
        )
        logger.info("Embedding模型加载完成")
    return _model


def get_embedding_model():
    """获取embedding模型实例"""
    return _load_model()


async def get_query_embedding(text: str) -> list[float]:
    """异步获取单条查询的embedding向量"""
    model = get_embedding_model()
    import asyncio
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, lambda: model.embed_query(text))
    return embedding
