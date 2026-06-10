from fastapi import APIRouter

from app.api.routes import diagnosis, graph, graphrag

api_router = APIRouter()
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(graphrag.router, prefix="/graphrag", tags=["graphrag"])
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
