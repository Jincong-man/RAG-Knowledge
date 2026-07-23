"""RAG链 - 直接用httpx调用DashScope API，避免LangChain httpx客户端关闭问题"""
import json
import logging
import re
import httpx

from app.config import settings
from app.rag.prompts import RAG_SYSTEM_PROMPT, RAG_USER_TEMPLATE

logger = logging.getLogger(__name__)


def _format_docs(docs) -> str:
    """格式化检索文档为上下文字符串"""
    context_parts = []
    for i, doc in enumerate(docs, 1):
        filename = doc.metadata.get("filename", "未知文档")
        context_parts.append(
            f"[{i}] 来自「{filename}」：\n{doc.page_content}"
        )
    return "\n\n".join(context_parts)


def _extract_referenced_indices(answer: str) -> set:
    """从回答中提取实际引用的文档编号，如 [1] [2] [3]"""
    return {int(m) for m in re.findall(r'\[(\d+)\]', answer)}


async def stream_rag(question: str, chat_history: list[dict]):
    """
    流式RAG：检索知识库 → 构建prompt → 直接调DashScope API流式生成
    引用来源只包含回答中实际引用的文档
    Yields: {"type": "sources"/"token"/"error", "data": ...}
    """
    # Step 1: 检索知识库
    from app.rag.vectorstore import get_retriever
    retriever = await get_retriever()
    docs = await retriever.ainvoke(question)

    # 构建所有候选来源（带编号）
    all_sources = []
    for i, doc in enumerate(docs):
        all_sources.append({
            "index": i + 1,
            "filename": doc.metadata.get("filename", "未知文档"),
            "chunk_index": doc.metadata.get("chunk_index", 0),
            "content": doc.page_content[:200],
            "score": round(doc.metadata.get("relevance_score", 0), 3),
        })

    # Step 2: 构建上下文和prompt
    context = _format_docs(docs)

    messages = [{"role": "system", "content": RAG_SYSTEM_PROMPT.format(context=context)}]

    for msg in chat_history[-10:]:
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": RAG_USER_TEMPLATE.format(question=question)})

    # Step 3: 调DashScope API流式生成
    api_url = f"{settings.QWEN_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.QWEN_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": 0.3,
    }

    full_answer = ""

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=30.0)) as client:
            async with client.stream("POST", api_url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    error_msg = f"API调用失败({response.status_code}): {error_body.decode()[:200]}"
                    logger.error(error_msg)
                    yield {"type": "error", "data": error_msg}
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_answer += content
                            yield {"type": "token", "data": content}
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

        # Step 4: 流式结束后，提取实际引用的文档编号，只发送被引用的来源
        referenced = _extract_referenced_indices(full_answer)
        used_sources = [
            s for s in all_sources if s["index"] in referenced
        ]
        # 移除内部 index 字段
        for s in used_sources:
            s.pop("index", None)

        if used_sources:
            yield {"type": "sources", "data": used_sources}

    except httpx.ConnectError as e:
        error_msg = f"无法连接到模型API: {e}"
        logger.error(error_msg)
        yield {"type": "error", "data": error_msg}
    except httpx.TimeoutException as e:
        error_msg = f"模型API请求超时: {e}"
        logger.error(error_msg)
        yield {"type": "error", "data": error_msg}
    except Exception as e:
        error_msg = f"问答生成失败: {e}"
        logger.error(error_msg, exc_info=True)
        yield {"type": "error", "data": error_msg}
