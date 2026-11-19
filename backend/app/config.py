"""应用配置管理 - 使用pydantic-settings从环境变量加载配置"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 大模型
    DASHSCOPE_API_KEY: str = ""
    QWEN_MODEL: str = "qwen3.8-flash"
    QWEN_API_BASE: str = "https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1"
    # 关闭思考模式：显著降低首字延迟（qwen3 系列支持 enable_thinking 参数）
    QWEN_ENABLE_THINKING: bool = False

    # Embedding & Reranker
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-for-local-testing"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 存储
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50

    # RAG参数
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 10
    RERANK_TOP_N: int = 5

    # 缓存
    CACHE_SIMILARITY_THRESHOLD: float = 0.95
    CACHE_TTL_SECONDS: int = 3600

    # 频率限制
    RATE_LIMIT_PER_MINUTE: int = 30

    # 部署 / 演示
    ADMIN_USERNAME: str = "jincong"
    ADMIN_PASSWORD: str = "123456"
    # 是否在知识库为空时自动导入 demo_data 下的示例文档（公开演示站建议开启）
    SEED_DEMO_DATA: bool = False
    # 仅当请求携带该密钥（由 Cloudflare Pages Function 注入）时，才信任 x-real-ip 头
    PROXY_SECRET: str = ""

    @property
    def upload_dir_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_dir_path(self) -> Path:
        path = Path(self.CHROMA_PERSIST_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
