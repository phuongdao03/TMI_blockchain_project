"""Gated, idempotent payout submission and status reconciliation tasks."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.users.security import SensitiveFieldCipher
from app.modules.wallet.models import PayoutAttempt, WithdrawalRequest
from app.modules.wallet.payout_gateway import (
    PayOSPayoutGateway,
    PayoutOutcomeUnknown,
)
from app.modules.wallet.withdrawal_service import WalletWithdrawalService
from app.workers.celery_app import celery_app


def _gateway() -> PayOSPayoutGateway | None:
    settings = get_settings()
    client_id = settings.payos_payout_client_id
    api_key = settings.payos_payout_api_key
    checksum_key = settings.payos_payout_checksum_key
    if (
        not settings.payout_live_enabled
        or settings.payos_payout_provider != "payos"
        or client_id is None
        or not client_id.get_secret_value()
        or api_key is None
        or not api_key.get_secret_value()
        or checksum_key is None
        or not checksum_key.get_secret_value()
    ):
        return None
    return PayOSPayoutGateway(
        client_id=client_id.get_secret_value(),
        api_key=api_key.get_secret_value(),
        checksum_key=checksum_key.get_secret_value(),
        base_url=settings.payos_payout_base_url,
        timeout_seconds=settings.payos_payout_timeout_seconds,
    )


def _service(session: Any) -> WalletWithdrawalService:
    settings = get_settings()
    secret = settings.pii_encryption_key
    if secret is None or not secret.get_secret_value():
        raise RuntimeError("PII_ENCRYPTION_KEY is not configured.")
    return WalletWithdrawalService(
        session=session,
        cipher=SensitiveFieldCipher.from_base64(secret.get_secret_value()),
        withdrawal_feature_enabled=settings.wallet_withdrawal_enabled,
    )


async def _process_queued_payouts() -> int:
    gateway = _gateway()
    if gateway is None:
        return 0
    processed = 0
    try:
        async with get_session_factory()() as session:
            async with session.begin():
                withdrawal_ids = list(
                    await session.scalars(
                        select(WithdrawalRequest.id)
                        .where(WithdrawalRequest.status == "QUEUED")
                        .order_by(WithdrawalRequest.created_at)
                        .limit(50)
                    )
                )
        for withdrawal_id in withdrawal_ids:
            async with get_session_factory()() as session:
                service = _service(session)
                submission = await service.begin_payout_submission(withdrawal_id)
            if submission is None:
                continue
            processed += 1
            try:
                result = await gateway.create_payout(
                    reference_id=str(submission["reference_id"]),
                    idempotency_key=str(submission["idempotency_key"]),
                    amount_minor=int(submission["amount_minor"]),
                    description=f"Commission {str(submission['reference_id'])[-16:]}",
                    bank_bin=str(submission["bank_bin"]),
                    account_number=str(submission["account_number"]),
                )
            except PayoutOutcomeUnknown:
                async with get_session_factory()() as session:
                    await _service(session).record_payout_state(
                        withdrawal_id=withdrawal_id,
                        provider_payout_id=None,
                        state="UNKNOWN",
                    )
                continue
            async with get_session_factory()() as session:
                await _service(session).record_payout_state(
                    withdrawal_id=withdrawal_id,
                    provider_payout_id=result.provider_payout_id,
                    state=result.state,
                    error_code=result.error_code,
                )
        return processed
    finally:
        await gateway.close()


async def _reconcile_payouts() -> int:
    gateway = _gateway()
    if gateway is None:
        return 0
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=5)
    reconciled = 0
    try:
        async with get_session_factory()() as session:
            async with session.begin():
                rows = list(
                    await session.execute(
                        select(
                            PayoutAttempt.withdrawal_id,
                            PayoutAttempt.provider_payout_id,
                            PayoutAttempt.reference_id,
                        )
                        .where(
                            PayoutAttempt.status.in_(("PROCESSING", "UNKNOWN")),
                            PayoutAttempt.provider_payout_id.is_not(None),
                        )
                        .order_by(PayoutAttempt.updated_at)
                        .limit(100)
                    )
                )
                stale_sending_ids = list(
                    await session.scalars(
                        select(PayoutAttempt.withdrawal_id).where(
                            PayoutAttempt.status == "SENDING",
                            PayoutAttempt.updated_at < cutoff,
                        )
                    )
                )
        for withdrawal_id in stale_sending_ids:
            async with get_session_factory()() as session:
                await _service(session).record_payout_state(
                    withdrawal_id=withdrawal_id,
                    provider_payout_id=None,
                    state="UNKNOWN",
                )
            reconciled += 1
        for withdrawal_id, provider_payout_id, reference_id in rows:
            if not provider_payout_id:
                continue
            try:
                result = await gateway.get_payout(
                    str(provider_payout_id),
                    expected_reference_id=str(reference_id),
                )
            except PayoutOutcomeUnknown:
                continue
            async with get_session_factory()() as session:
                await _service(session).record_payout_state(
                    withdrawal_id=withdrawal_id,
                    provider_payout_id=result.provider_payout_id,
                    state=result.state,
                    error_code=result.error_code,
                )
            reconciled += 1
        return reconciled
    finally:
        await gateway.close()


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.payout_tasks.process_queued_payouts",
    max_retries=0,
)
def process_queued_payouts() -> int:
    """Submit only requests already manually approved and queued by finance."""
    return asyncio.run(_process_queued_payouts())


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.payout_tasks.reconcile_payouts",
    max_retries=0,
)
def reconcile_payouts() -> int:
    return asyncio.run(_reconcile_payouts())
