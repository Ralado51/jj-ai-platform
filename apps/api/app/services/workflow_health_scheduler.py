from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.user import User
from app.repositories.notification_email_delivery_repository import NotificationEmailDeliveryRepository
from app.repositories.notification_preference_repository import NotificationPreferenceRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.repositories.workflow_health_history_repository import WorkflowHealthHistoryRepository
from app.services.email_service import EmailService
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
                preference_repository = NotificationPreferenceRepository(db)
                delivery_repository = NotificationEmailDeliveryRepository(db)
                email_service = EmailService()
                count = WorkflowHealthAutomationService(
                    execution_repository,
                    history_repository,
                ).create_daily_snapshots()
                threshold = max(1, get_settings().workflow_health_regression_threshold)
                in_app_count = 0
                email_sent_count = 0
                email_failed_count = 0
                for user_id in execution_repository.list_user_ids():
                    user = db.get(User, user_id)
                    if user is None or not user.is_active:
                        continue
                    preferences = preference_repository.get_or_create(user_id=user_id, default_email=user.email)
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
                        if preferences.in_app_enabled:
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
                            in_app_count += 1
                        recipient = preferences.email_address or user.email
                        if not preferences.email_enabled or not recipient:
                            continue
                        delivery = delivery_repository.get_or_create(
                            user_id=user_id,
                            recipient=recipient,
                            workflow_id=regression.workflow_id,
                            deduplication_key=key,
                        )
                        if delivery.status == "sent":
                            continue
                        try:
                            await asyncio.to_thread(
                                email_service.send_workflow_health_regression,
                                recipient=recipient,
                                workflow_name=regression.workflow_name,
                                previous_score=regression.previous_score,
                                current_score=regression.current_score,
                                delta=regression.delta,
                                workflow_id=str(regression.workflow_id),
                            )
                            delivery_repository.mark_sent(delivery)
                            email_sent_count += 1
                        except Exception as exc:
                            delivery_repository.mark_failed(delivery, str(exc))
                            email_failed_count += 1
                            logger.exception("Failed to send workflow health email to user %s", user_id)
                logger.info(
                    "Workflow health snapshots updated: %s; in-app checked: %s; emails sent: %s; emails failed: %s",
                    count,
                    in_app_count,
                    email_sent_count,
                    email_failed_count,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to update workflow health snapshots")
        await asyncio.sleep(interval_seconds)
