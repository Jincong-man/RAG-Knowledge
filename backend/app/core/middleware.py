"""频率限制中间件"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于滑动窗口的简单频率限制"""

    def __init__(self, app, requests_per_minute: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.requests: dict[str, list[float]] = defaultdict(list)

    @staticmethod
    def _client_key(request: Request) -> str:
        """获取限流用的客户端标识。

        通过 Cloudflare Pages Function 代理时，真实用户IP放在 x-real-ip。
        只有携带正确 PROXY_SECRET 的请求才信任该头，避免直连时伪造IP绕过限流。
        """
        proxy_secret = settings.PROXY_SECRET
        if proxy_secret and request.headers.get("x-proxy-secret") == proxy_secret:
            forwarded = request.headers.get("x-real-ip") or request.headers.get("cf-connecting-ip")
            if forwarded:
                return forwarded.strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next):
        # 获取客户端IP
        client_ip = self._client_key(request)
        now = time.time()
        window_start = now - 60

        # 清理过期记录
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > window_start
        ]

        # 检查频率
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试",
            )

        self.requests[client_ip].append(now)
        response = await call_next(request)
        return response
