"""Embedding模型封装 - 使用ModelScope下载bge-small-zh-v1.5"""
import logging
import os
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_model = None
MODEL_ID = "BAAI/bge-small-zh-v1.5"
MODEL_ROOT = Path(__file__).parent.parent.parent / "models"
MODEL_LOCAL_DIR = MODEL_ROOT / "bge-small-zh-v1.5"
# ModelScope的缓存布局：<cache_dir>/models/<owner>--<name>/snapshots/<revision>
MODELSCOPE_CACHE_PATTERN = f"models/{MODEL_ID.replace('/', '--')}/snapshots/*"


def _find_local_model() -> Path | None:
    """在本地查找已下载的模型目录，兼容手动解压与ModelScope缓存两种布局"""
    candidates = [
        MODEL_LOCAL_DIR,
        *sorted(MODEL_ROOT.glob(MODELSCOPE_CACHE_PATTERN)),
    ]
    for path in candidates:
        if (path / "config.json").exists():
            return path
    return None


def _download_model():
    """获取模型目录：优先使用本地已下载的模型，本地没有才下载"""
    local_model = _find_local_model()
    if local_model:
        logger.info(f"使用本地模型: {local_model}")
        return str(local_model)

    logger.info(f"本地未找到模型，开始下载 {MODEL_ID} ...")
    try:
        from modelscope import snapshot_download
        model_dir = snapshot_download(MODEL_ID, cache_dir=str(MODEL_ROOT))
    except ImportError:
        logger.info("未安装modelscope，改用HuggingFace下载...")
        from huggingface_hub import snapshot_download
        model_dir = snapshot_download(MODEL_ID, cache_dir=str(MODEL_ROOT))
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
