from __future__ import annotations

import asyncio
import logging

from app.db.session import SessionLocal
from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.repositories.workflow_health_history_repository import WorkflowHealthHistoryRepository
from app.services.workflow_health_automation_service import WorkflowHealthAutomationService

logger = logging.getLogger(__name__)


async def run_workflow_health_scheduler(interval_seconds: int) -> None:
    while True:
        try:
            with SessionLocal() as db:
                count = WorkflowHealthAutomationService(
                    WorkflowExecutionRepository(db),
                    WorkflowHealthHistoryRepository(db),
                ).create_daily_snapshots()
                logger.info("Workflow health snapshots updated: %s", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to update workflow health snapshots")
        await asyncio.sleep(interval_seconds)
