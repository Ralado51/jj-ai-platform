from fastapi import APIRouter

from app.api.v1.routers.analytics import router as analytics_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.benchmark import router as benchmark_router
from app.api.v1.routers.content_creator import router as content_creator_router
from app.api.v1.routers.conversations import router as conversations_router
from app.api.v1.routers.documents import (
    documents_router,
    project_documents_router,
    project_search_router,
)
from app.api.v1.routers.projects import router as projects_router
from app.api.v1.routers.prompt_templates import router as prompt_templates_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(conversations_router)
api_router.include_router(prompt_templates_router)
api_router.include_router(content_creator_router)
api_router.include_router(benchmark_router)
api_router.include_router(analytics_router)
api_router.include_router(project_documents_router)
api_router.include_router(project_search_router)
api_router.include_router(documents_router)
