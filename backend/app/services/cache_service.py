"""缓存服务：语义缓存 + LLM结果缓存"""
import json
import logging
import hashlib
import time
from typing import Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Redis 不可用时的重试间隔（秒），避免每个请求都卡在连接超时
REDIS_RETRY_INTERVAL = 60


class CacheService:
    """RAG问答缓存服务"""

    def __init__(self):
        self._redis = None
        self._last_attempt = 0.0

    async def _get_redis(self):
        """获取Redis连接；不可用时按间隔重试，其余请求直接跳过缓存"""
        if self._redis is not None:
            return self._redis
        if time.monotonic() - self._last_attempt < REDIS_RETRY_INTERVAL:
            return None
        self._last_attempt = time.monotonic()
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            await self._redis.ping()
        except Exception as e:
            logger.warning(f"Redis连接失败，缓存服务不可用: {e}")
            self._redis = None
        return self._redis

    async def _get_embedding(self, text: str) -> list[float]:
        """获取文本的embedding向量"""
        from app.rag.embeddings import get_query_embedding
        return await get_query_embedding(text)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        a_np, b_np = np.array(a), np.array(b)
        dot = np.dot(a_np, b_np)
        norm = np.linalg.norm(a_np) * np.linalg.norm(b_np)
        return float(dot / norm) if norm > 0 else 0.0

    async def get_similar_answer(self, question: str) -> Optional[dict]:
        """语义缓存查找：找到相似度>阈值的已缓存回答"""
        redis = await self._get_redis()
        if not redis:
            return None

        try:
            # 计算问题的embedding
            q_embedding = await self._get_embedding(question)

            # 获取所有缓存条目
            keys = await redis.keys("rag_cache:*")
            if not keys:
                return None

            for key in keys:
                cached_data = await redis.get(key)
                if cached_data:
                    data = json.loads(cached_data)
                    cached_embedding = data.get("embedding")
                    if cached_embedding:
                        sim = self._cosine_similarity(q_embedding, cached_embedding)
                        if sim >= settings.CACHE_SIMILARITY_THRESHOLD:
                            logger.info(f"语义缓存命中，相似度: {sim:.4f}")
                            return {
                                "answer": data["answer"],
                                "references": data.get("references", []),
                            }
            return None
        except Exception as e:
            logger.warning(f"语义缓存查询失败: {e}")
            return None

    async def set_answer(self, question: str, answer: str, references: list = None):
        """缓存问答结果"""
        redis = await self._get_redis()
        if not redis:
            return

        try:
            q_embedding = await self._get_embedding(question)
            cache_key = f"rag_cache:{hashlib.md5(question.encode()).hexdigest()}"
            cache_data = {
                "question": question,
                "answer": answer,
                "embedding": q_embedding,
                "references": references or [],
            }
            await redis.setex(
                cache_key,
                settings.CACHE_TTL_SECONDS,
                json.dumps(cache_data, ensure_ascii=False),
            )
            logger.info(f"问答结果已缓存: {question[:30]}...")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")

    async def get_exact_answer(self, question: str) -> Optional[dict]:
        """精确匹配缓存（更快，不需要计算embedding）"""
        redis = await self._get_redis()
        if not redis:
            return None

        try:
            cache_key = f"rag_cache:{hashlib.md5(question.encode()).hexdigest()}"
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception:
            return None


# 全局单例
cache_service = CacheService()
