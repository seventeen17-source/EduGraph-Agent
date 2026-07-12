from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{(PROJECT_ROOT / 'data' / 'edugraph.db').as_posix()}"
DEFAULT_CHROMA_DIR = str(PROJECT_ROOT / "data" / "chroma")


class Settings(BaseSettings):
    """Runtime settings for the FastAPI backend."""

    model_config = SettingsConfigDict(
        # 优先从 backend/.env 加载（绝对路径），其次查找根目录 .env
        env_file=[
            str(PROJECT_ROOT / "backend" / ".env"),  # backend 目录下的 .env
            str(PROJECT_ROOT / ".env"),  # 项目根目录的 .env
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
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
        ],
        alias="CORS_ORIGINS",
    )

    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="edugraph123", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")
    database_url: str = Field(default=DEFAULT_SQLITE_URL, alias="DATABASE_URL")

    default_graph_depth: int = 1
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
