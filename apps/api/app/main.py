from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import engine
from app.events.audit_subscribers import register_audit_subscribers
from app.events.resource_subscribers import register_resource_subscribers
from app.services.storage import StorageError, get_storage_service
from app.services.workflow_health_scheduler import run_workflow_health_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    register_audit_subscribers()
    register_resource_subscribers()
    task: asyncio.Task[None] | None = None
    if settings.workflow_health_snapshot_enabled:
        interval = max(300, settings.workflow_health_snapshot_interval_seconds)
        task = asyncio.create_task(run_workflow_health_scheduler(interval))
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API central da JJ AI Platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jjaiplatform.jjnetwork.com.br",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.app_version, "environment": settings.environment}


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jj-ai-platform-api"}


@app.get("/health/database", tags=["system"])
def database_health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/health/storage", tags=["system"])
def storage_health() -> dict[str, str]:
    try:
        get_storage_service().check_connection()
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Object storage is unavailable.") from exc
    return {"status": "ok", "storage": "connected", "bucket": settings.s3_bucket}
