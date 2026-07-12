from fastapi import APIRouter

from app.api.routes import admin, agents, assistant, diagnosis, exercises, graph, graphrag, profile
from app.auth.routes import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)  # /auth/register, /auth/login, etc.
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(graphrag.router, prefix="/graphrag", tags=["graphrag"])
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
