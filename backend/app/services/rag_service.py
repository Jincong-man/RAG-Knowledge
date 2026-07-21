"""RAG检索与生成服务 - 核心问答逻辑"""
import logging
from typing import AsyncGenerator

from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


async def stream_rag_answer(
    question: str,
    chat_history: list[dict],
) -> AsyncGenerator[dict, None]:
    """
    流式RAG问答生成器
    Yields:
        {"type": "sources", "data": [...]}  - 引用来源
        {"type": "token", "data": "..."}    - 生成token
        {"type": "error", "data": "..."}    - 错误
    """
    # 1. 检查语义缓存
    cached = await cache_service.get_similar_answer(question)
    if cached:
        logger.info(f"语义缓存命中: {question[:30]}...")
        yield {"type": "sources", "data": cached.get("references", [])}
        for char in cached["answer"]:
            yield {"type": "token", "data": char}
        return

    # 2. 调用RAG流式生成
    from app.rag.chain import stream_rag
    full_answer = ""
    references = []

    async for event in stream_rag(question, chat_history):
        if event["type"] == "sources":
            references = event["data"]
        yield event
        if event["type"] == "token":
            full_answer += event["data"]

    # 3. 写入缓存
    if full_answer:
        await cache_service.set_answer(question, full_answer, references)
