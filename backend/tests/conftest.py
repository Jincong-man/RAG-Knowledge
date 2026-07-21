"""测试配置和fixtures：SQLite内存数据库、测试客户端、认证fixtures"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app.models.user import User, UserRole
from app.core.security import hash_password

# 移除频率限制中间件，避免测试中累积请求触发429
from app.core.middleware import RateLimitMiddleware
app.user_middleware = [
    m for m in app.user_middleware if m.cls != RateLimitMiddleware
]
# 强制重建中间件栈
if hasattr(app, "middleware_stack"):
    app.middleware_stack = None


@pytest_asyncio.fixture
async def client():
    """创建测试客户端，使用SQLite内存数据库，每个测试独立数据库"""
    # 创建测试专用引擎和会话工厂
    # 使用StaticPool确保所有连接共享同一个内存数据库
    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    # 覆盖get_db依赖，使所有API端点使用测试数据库
    async def override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # 手动创建数据库表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 手动创建管理员账号（替代lifespan中的ensure_admin_user）
    async with test_session_factory() as session:
        admin = User(
            username="jincong",
            password_hash=hash_password("123456"),
            role=UserRole.ADMIN,
        )
        session.add(admin)
        await session.commit()

    # Mock掉lifespan中的数据库初始化，避免干扰测试数据库
    with patch("app.main.init_db", new_callable=AsyncMock), \
         patch("app.main.ensure_admin_user", new_callable=AsyncMock):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    # 清理
    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest_asyncio.fixture
async def admin_token(client):
    """获取管理员token（lifespan创建的jincong账号，密码123456）"""
    resp = await client.post("/api/auth/login", json={
        "username": "jincong",
        "password": "123456",
    })
    assert resp.status_code == 200, f"管理员登录失败: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client):
    """注册并获取普通用户token"""
    reg_resp = await client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "test123",
    })
    assert reg_resp.status_code == 201, f"用户注册失败: {reg_resp.text}"
    login_resp = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "test123",
    })
    assert login_resp.status_code == 200, f"用户登录失败: {login_resp.text}"
    return login_resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_headers(admin_token):
    """管理员认证headers"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def user_headers(user_token):
    """普通用户认证headers"""
    return {"Authorization": f"Bearer {user_token}"}
