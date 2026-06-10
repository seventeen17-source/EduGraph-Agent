from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.db.neo4j import neo4j_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await neo4j_client.connect()
    yield
    await neo4j_client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        neo4j_status = await neo4j_client.healthcheck()
        return {"status": "ok", **neo4j_status}

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
