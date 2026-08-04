import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.audit.service import AuditService
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.voting.service import VotingCampaignService
from app.modules.voting.telemetry import voting_lifecycle_telemetry
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _reconcile_due_campaigns() -> int:
    settings = get_settings()
    secret = settings.auth_outbox_encryption_key
    async with get_session_factory()() as session:
        service = VotingCampaignService(
            session=session,
            audit=AuditService(session),
            payload_cipher=OutboxPayloadCipher.from_base64(
                encoded_key=secret.get_secret_value() if secret is not None else "",
                key_id=settings.auth_outbox_key_id,
            ),
        )
        return await service.reconcile_due(now=datetime.now(UTC), limit=100)


@celery_app.task(  # type: ignore
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)
def reconcile_voting_campaign_lifecycle() -> int:
    try:
        return asyncio.run(_reconcile_due_campaigns())
    except Exception as error:
        voting_lifecycle_telemetry.record("worker_failure")
        logger.exception(
            "voting_campaign_lifecycle_worker_failed",
            extra={
                "action": "reconcile",
                "error_code": type(error).__name__,
                "outcome": "failure",
            },
        )
        raise
