"""FastAPI应用入口"""
import logging
import os
from contextlib import asynccontextmanager

# 设置HuggingFace镜像（必须在模型加载前）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.core.middleware import RateLimitMiddleware
from app.models import User, UserRole  # noqa: 确保模型被注册
from app.core.security import hash_password

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def ensure_admin_user():
    """确保管理员账号存在"""
    from app.database import async_session_factory
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.username == "jincong"))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                username="jincong",
                password_hash=hash_password("123456"),
                role=UserRole.ADMIN,
            )
            db.add(admin)
            await db.commit()
            logger.info("已创建管理员账号: jincong")
        else:
            logger.info("管理员账号已存在: jincong")


async def _warmup_models():
    """后台预热embedding模型并重新处理卡住的文档"""
    try:
        import asyncio
        await asyncio.sleep(1)  # 等待启动完成
        logger.info("开始预热embedding模型...")
        from app.rag.embeddings import get_embedding_model
        await asyncio.to_thread(get_embedding_model)
        logger.info("embedding模型预热完成")

        # 重新处理卡在processing状态的文档
        await _reprocess_stuck_documents()
    except Exception as e:
        logger.warning(f"模型预热失败（首次请求时会重新加载）: {e}")


async def _reprocess_stuck_documents():
    """重新处理卡在processing状态的文档"""
    from app.database import async_session_factory
    from app.models.document import Document, DocumentStatus
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(Document).where(Document.status == DocumentStatus.PROCESSING)
        )
        docs = result.scalars().all()

    if not docs:
        return

    logger.info(f"发现 {len(docs)} 个未完成的文档，开始重新处理...")
    from app.services.doc_service import process_document
    import asyncio
    for doc in docs:
        file_path = str(settings.upload_dir_path / doc.filename)
        logger.info(f"重新处理文档: id={doc.id}, file={file_path}")
        asyncio.create_task(process_document(doc.id, file_path, doc.file_type))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("正在启动应用...")
    # 初始化数据库
    await init_db()
    # 确保管理员存在
    await ensure_admin_user()
    # 预热embedding模型（后台加载，不阻塞启动）
    import asyncio
    asyncio.create_task(_warmup_models())
    logger.info("应用启动完成")
    yield
    logger.info("应用正在关闭...")


app = FastAPI(
    title="RAG电商知识库问答系统",
    description="基于LangChain + 通义千问的企业级知识库问答API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS配置（前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 频率限制中间件
app.add_middleware(RateLimitMiddleware)

# 注册路由
from app.routers import auth, chat, knowledge

app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "RAG电商知识库问答系统",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
