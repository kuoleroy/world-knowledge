"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.api.v1 import disciplines, edges, graph, nodes, search, stages, traditions

api_router = APIRouter()
api_router.include_router(stages.router)
api_router.include_router(disciplines.router)
api_router.include_router(traditions.router)
api_router.include_router(nodes.router)
api_router.include_router(edges.router)
api_router.include_router(search.router)
api_router.include_router(graph.router)
