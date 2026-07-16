from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{(PROJECT_ROOT / 'data' / 'edugraph.db').as_posix()}"
DEFAULT_CHROMA_DIR = str(PROJECT_ROOT / "data" / "chroma")
DEFAULT_GENERATED_ASSETS_DIR = str(PROJECT_ROOT / "data" / "generated_assets")


class Settings(BaseSettings):
    """Runtime settings for the FastAPI backend."""

    model_config = SettingsConfigDict(
        # 优先使用 backend/.env 覆盖根目录 .env，便于后端本地联调时临时切换模型。
        env_file=[
            str(PROJECT_ROOT / ".env"),  # 项目根目录的共享 .env
            str(PROJECT_ROOT / "backend" / ".env"),  # backend 目录下的 .env，优先级更高
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EduGraph-Agent Backend"
    api_prefix: str = "/api"
    environment: Literal["local", "dev", "test", "prod"] = "local"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5175",
            "http://127.0.0.1:5176",
            "http://127.0.0.1:5177",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176",
            "http://localhost:5177",
        ],
        alias="CORS_ORIGINS",
    )
    cors_origin_regex: str | None = Field(
        default=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?",
        alias="CORS_ORIGIN_REGEX",
    )

    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="edugraph123", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")
    database_url: str = Field(default=DEFAULT_SQLITE_URL, alias="DATABASE_URL")

    max_graph_depth: int = 2
    max_evidence_items: int = 8

    llm_resolver_enabled: bool = Field(default=False, alias="LLM_RESOLVER_ENABLED")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")

    # Embedding 模型配置（用于语义记忆检索）
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_api_key: str | None = Field(default=None, alias="EMBEDDING_API_KEY")
    embedding_base_url: str | None = Field(default=None, alias="EMBEDDING_BASE_URL")
    # ChromaDB 持久化路径
    chroma_persist_dir: str = Field(default=DEFAULT_CHROMA_DIR, alias="CHROMA_PERSIST_DIR")

    # 科大讯飞图片生成。provider=tti 使用旧 Spark TTI；provider=hidream 使用 HiDream 非实时任务接口。
    xunfei_image_provider: Literal["tti", "hidream"] = Field(
        default="tti",
        alias="XUNFEI_IMAGE_PROVIDER",
    )
    xunfei_tti_enabled: bool = Field(default=False, alias="XUNFEI_TTI_ENABLED")
    xunfei_tti_app_id: str | None = Field(default=None, alias="XUNFEI_TTI_APP_ID")
    xunfei_tti_api_key: str | None = Field(default=None, alias="XUNFEI_TTI_API_KEY")
    xunfei_tti_api_secret: str | None = Field(default=None, alias="XUNFEI_TTI_API_SECRET")
    xunfei_tti_endpoint: str = Field(
        default="https://spark-api.cn-huabei-1.xf-yun.com/v2.1/tti",
        alias="XUNFEI_TTI_ENDPOINT",
    )
    xunfei_hidream_enabled: bool = Field(default=False, alias="XUNFEI_HIDREAM_ENABLED")
    xunfei_hidream_app_id: str | None = Field(default=None, alias="XUNFEI_HIDREAM_APP_ID")
    xunfei_hidream_api_key: str | None = Field(default=None, alias="XUNFEI_HIDREAM_API_KEY")
    xunfei_hidream_api_secret: str | None = Field(default=None, alias="XUNFEI_HIDREAM_API_SECRET")
    xunfei_hidream_create_endpoint: str = Field(
        default="https://cn-huadong-1.xf-yun.com/v1/private/s3fd61810/create",
        alias="XUNFEI_HIDREAM_CREATE_ENDPOINT",
    )
    xunfei_hidream_query_endpoint: str = Field(
        default="https://cn-huadong-1.xf-yun.com/v1/private/s3fd61810/query",
        alias="XUNFEI_HIDREAM_QUERY_ENDPOINT",
    )
    xunfei_hidream_aspect_ratio: str = Field(default="1:1", alias="XUNFEI_HIDREAM_ASPECT_RATIO")
    xunfei_hidream_resolution: str = Field(default="2k", alias="XUNFEI_HIDREAM_RESOLUTION")
    xunfei_hidream_poll_interval_seconds: float = Field(
        default=2.0,
        alias="XUNFEI_HIDREAM_POLL_INTERVAL_SECONDS",
    )
    xunfei_hidream_poll_attempts: int = Field(default=40, alias="XUNFEI_HIDREAM_POLL_ATTEMPTS")
    generated_assets_dir: str = Field(
        default=DEFAULT_GENERATED_ASSETS_DIR,
        alias="GENERATED_ASSETS_DIR",
    )
    generated_assets_base_url: str = Field(
        default="http://127.0.0.1:8000/generated-assets",
        alias="GENERATED_ASSETS_BASE_URL",
    )

    jwt_secret: str | None = Field(default=None, alias="JWT_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_settings(settings: Settings) -> None:
    if settings.environment in ("dev", "prod") and not settings.jwt_secret:
        raise ValueError("JWT_SECRET must be set in non-local environments")
