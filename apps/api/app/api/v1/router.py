from fastapi import APIRouter

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.projects import router as projects_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(projects_router)
