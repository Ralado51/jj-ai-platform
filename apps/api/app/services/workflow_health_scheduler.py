from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories.notification_repository import NotificationRepository
from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.repositories.workflow_health_history_repository import WorkflowHealthHistoryRepository
from app.services.workflow_health_automation_service import WorkflowHealthAutomationService
from app.services.workflow_health_regression_service import WorkflowHealthRegressionService

logger = logging.getLogger(__name__)


async def run_workflow_health_scheduler(interval_seconds: int) -> None:
    while True:
        try:
            with SessionLocal() as db:
                execution_repository = WorkflowExecutionRepository(db)
                history_repository = WorkflowHealthHistoryRepository(db)
                notification_repository = NotificationRepository(db)
                count = WorkflowHealthAutomationService(
                    execution_repository,
                    history_repository,
                ).create_daily_snapshots()
                threshold = max(1, get_settings().workflow_health_regression_threshold)
                created_notifications = 0
                for user_id in execution_repository.list_user_ids():
                    regressions = WorkflowHealthRegressionService(
                        history_repository,
                        threshold=threshold,
                    ).detect(user_id=user_id)
                    for regression in regressions.items:
                        if regression.severity != "critical":
                            continue
                        key = (
                            f"workflow-health:{regression.workflow_id}:"
                            f"{regression.previous_date}:{regression.current_date}:critical"
                        )
                        notification_repository.create_if_absent(
                            user_id=user_id,
                            type="workflow_health_regression",
                            severity="critical",
                            title=f"Regressão crítica em {regression.workflow_name}",
                            message=(
                                f"O Health Score caiu de {regression.previous_score} para "
                                f"{regression.current_score} ({regression.delta} pontos)."
                            ),
                            workflow_id=regression.workflow_id,
                            deduplication_key=key,
                        )
                        created_notifications += 1
                logger.info(
                    "Workflow health snapshots updated: %s; critical notifications checked: %s",
                    count,
                    created_notifications,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to update workflow health snapshots")
        await asyncio.sleep(interval_seconds)
