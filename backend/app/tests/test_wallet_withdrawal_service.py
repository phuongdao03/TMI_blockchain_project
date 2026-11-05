import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import DomainError
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.users.security import SensitiveFieldCipher
from app.modules.wallet.models import (
    BankAccount,
    FinanceSettings,
    FinancialIdentityVerification,
    PayoutAttempt,
    SupportedBank,
    WithdrawalApproval,
    WithdrawalEvent,
    WithdrawalRequest,
)
from app.modules.wallet.service import FinanceLedger
from app.modules.wallet.withdrawal_service import WalletWithdrawalService
from app.tests.test_payment_service import ADMIN_ID, _service


async def _prepared_withdrawal(
    *,
    withdrawal_enabled: bool = True,
    threshold_minor: int | None = None,
):
    payment_service, sessions, engine, owner = await _service()
    cipher = SensitiveFieldCipher(key=b"f" * 32)
    async with sessions() as session, session.begin():
        user = await session.get(User, owner.user_id)
        assert user is not None
        user.email_verified_at = datetime.now(UTC)
        session.add(
            FinanceSettings(
                id=1,
                withdrawal_enabled=withdrawal_enabled,
                minimum_amount_minor=100_000,
                maximum_amount_minor=1_000_000,
                daily_limit_minor=1_000_000,
                daily_count_limit=3,
                two_person_threshold_minor=threshold_minor,
            )
        )
        session.add(
            SupportedBank(
                bank_bin="970415",
                bank_name="Test Bank",
                source_reference="provider-verified:test",
                is_enabled=True,
            )
        )
        session.add(
            FinancialIdentityVerification(user_id=owner.user_id, status="VERIFIED")
        )
        ledger = FinanceLedger(session)
        available, _reserved = await ledger.user_accounts(owner.user_id)
        expense = await ledger.platform_account("COMMISSION_EXPENSE")
        await ledger.transfer(
            source_account_id=expense.id,
            target_account_id=available.id,
            amount_minor=800_000,
            transaction_type="COMMISSION_CREDIT",
            idempotency_key="seed:commission",
            source_reference="commission:seed",
            description="Test commission",
        )
    async with sessions() as session:
        service = WalletWithdrawalService(
            session=session,
            cipher=cipher,
            withdrawal_feature_enabled=True,
        )
        bank = await service.add_bank_account(
            user_id=owner.user_id,
            bank_bin="970415",
            account_number="0123456789",
            account_name="Nguyen Van A",
            is_default=True,
        )
        bank_id = bank.id
    return payment_service, sessions, engine, owner, cipher, bank_id


def test_withdrawal_request_reserves_only_commission_and_is_idempotent() -> None:
    async def exercise() -> None:
        (
            payment_service,
            sessions,
            engine,
            owner,
            cipher,
            bank_id,
        ) = await _prepared_withdrawal()
        try:
            async with sessions() as session:
                service = WalletWithdrawalService(
                    session=session,
                    cipher=cipher,
                    withdrawal_feature_enabled=True,
                )
                first = await service.request_withdrawal(
                    user_id=owner.user_id,
                    bank_account_id=bank_id,
                    amount_minor=500_000,
                    idempotency_key="user-withdrawal-1",
                )
                replay = await service.request_withdrawal(
                    user_id=owner.user_id,
                    bank_account_id=bank_id,
                    amount_minor=500_000,
                    idempotency_key="user-withdrawal-1",
                )
                assert first.id == replay.id
                assert first.status == "PENDING_REVIEW"
                assert first.fee_minor == 0
                assert first.net_amount_minor == 500_000
                assert first.account_number_last4 == "6789"
                assert cipher.decrypt(first.account_number_ciphertext) == "0123456789"
            async with sessions() as session, session.begin():
                ledger = FinanceLedger(session)
                available, reserved = await ledger.user_accounts(owner.user_id)
                assert await ledger.balance(available.id) == 300_000
                assert await ledger.balance(reserved.id) == 500_000
                assert await session.scalar(select(PayoutAttempt.id)) is None
                assert await session.scalar(select(WithdrawalEvent.id)) is not None
                audit = await session.scalar(
                    select(AuditLog).where(
                        AuditLog.action == "wallet.withdrawal.created"
                    )
                )
                assert audit is not None
                assert "0123456789" not in str(audit.after_json)
        finally:
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_withdrawal_is_blocked_if_feature_or_identity_gate_is_unavailable() -> None:
    async def exercise() -> None:
        (
            payment_service,
            sessions,
            engine,
            owner,
            cipher,
            bank_id,
        ) = await _prepared_withdrawal(withdrawal_enabled=False)
        try:
            async with sessions() as session:
                service = WalletWithdrawalService(
                    session=session,
                    cipher=cipher,
                    withdrawal_feature_enabled=True,
                )
                with pytest.raises(DomainError) as disabled:
                    await service.request_withdrawal(
                        user_id=owner.user_id,
                        bank_account_id=bank_id,
                        amount_minor=100_000,
                        idempotency_key="disabled",
                    )
                assert disabled.value.code == "WITHDRAWAL_UNAVAILABLE"
            async with sessions() as session, session.begin():
                settings = await session.get(FinanceSettings, 1)
                assert settings is not None
                settings.withdrawal_enabled = True
                await session.delete(
                    await session.get(FinancialIdentityVerification, owner.user_id)
                )
            async with sessions() as session:
                service = WalletWithdrawalService(
                    session=session,
                    cipher=cipher,
                    withdrawal_feature_enabled=True,
                )
                with pytest.raises(DomainError) as unverified:
                    await service.request_withdrawal(
                        user_id=owner.user_id,
                        bank_account_id=bank_id,
                        amount_minor=100_000,
                        idempotency_key="unverified",
                    )
                assert unverified.value.code == "WITHDRAWAL_IDENTITY_REQUIRED"
        finally:
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_rejection_releases_reservation_once_and_requires_a_reason() -> None:
    async def exercise() -> None:
        (
            payment_service,
            sessions,
            engine,
            owner,
            cipher,
            bank_id,
        ) = await _prepared_withdrawal()
        try:
            async with sessions() as session:
                service = WalletWithdrawalService(
                    session=session,
                    cipher=cipher,
                    withdrawal_feature_enabled=True,
                )
                request = await service.request_withdrawal(
                    user_id=owner.user_id,
                    bank_account_id=bank_id,
                    amount_minor=200_000,
                    idempotency_key="reject-me",
                )
                rejected = await service.reject_withdrawal(
                    withdrawal_id=request.id,
                    actor_user_id=ADMIN_ID,
                    reason="Account details could not be verified.",
                )
                assert rejected.status == "REJECTED"
                with pytest.raises(DomainError):
                    await service.reject_withdrawal(
                        withdrawal_id=request.id,
                        actor_user_id=ADMIN_ID,
                        reason="Duplicate click.",
                    )
            async with sessions() as session, session.begin():
                ledger = FinanceLedger(session)
                available, reserved = await ledger.user_accounts(owner.user_id)
                assert await ledger.balance(available.id) == 800_000
                assert await ledger.balance(reserved.id) == 0
                assert (
                    await session.scalar(select(WithdrawalRequest.status)) == "REJECTED"
                )
        finally:
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_admin_approval_is_required_and_never_creates_a_payout_inline() -> None:
    async def exercise() -> None:
        (
            payment_service,
            sessions,
            engine,
            owner,
            cipher,
            bank_id,
        ) = await _prepared_withdrawal()
        try:
            async with sessions() as session:
                service = WalletWithdrawalService(
                    session=session,
                    cipher=cipher,
                    withdrawal_feature_enabled=True,
                )
                request = await service.request_withdrawal(
                    user_id=owner.user_id,
                    bank_account_id=bank_id,
                    amount_minor=200_000,
                    idempotency_key="approve-me",
                )
                withdrawal_id = request.id
                with pytest.raises(DomainError) as unverified_bank:
                    await service.approve_withdrawal(
                        withdrawal_id=withdrawal_id,
                        actor_user_id=ADMIN_ID,
                    )
                assert unverified_bank.value.code == "BANK_ACCOUNT_UNVERIFIED"
                await service.verify_bank_account(
                    bank_account_id=bank_id,
                    actor_user_id=ADMIN_ID,
                    evidence_reference="manual-check-2026-11-05",
                )
                approved = await service.approve_withdrawal(
                    withdrawal_id=withdrawal_id,
                    actor_user_id=ADMIN_ID,
                )
                assert approved.status == "APPROVED"
            async with sessions() as session, session.begin():
                assert await session.scalar(select(PayoutAttempt.id)) is None
                assert (
                    await session.scalar(select(WithdrawalRequest.status)) == "APPROVED"
                )
        finally:
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_payout_submission_requires_gates_and_settles_reserved_ledger() -> None:
    async def exercise() -> None:
        payment_service, sessions, engine, owner, cipher, bank_id = (
            await _prepared_withdrawal()
        )
        try:
            async with sessions() as session:
                service = WalletWithdrawalService(
                    session=session,
                    cipher=cipher,
                    withdrawal_feature_enabled=True,
                )
                await service.verify_bank_account(
                    bank_account_id=bank_id,
                    actor_user_id=ADMIN_ID,
                    evidence_reference="manual-check-payout-test",
                )
                request = await service.request_withdrawal(
                    user_id=owner.user_id,
                    bank_account_id=bank_id,
                    amount_minor=200_000,
                    idempotency_key="payout-gated",
                )
                approved = await service.approve_withdrawal(
                    withdrawal_id=request.id,
                    actor_user_id=ADMIN_ID,
                )
                assert approved.status == "APPROVED"
                with pytest.raises(DomainError) as disabled:
                    await service.queue_payout(
                        withdrawal_id=request.id,
                        actor_user_id=ADMIN_ID,
                        environment_live_enabled=False,
                        provider_enabled=True,
                        credentials_configured=True,
                    )
                assert disabled.value.code == "PAYOUT_PROVIDER_NOT_READY"
                async with session.begin():
                    finance_settings = await session.get(FinanceSettings, 1)
                    assert finance_settings is not None
                    finance_settings.payout_live_enabled = True
                queued, attempt = await service.queue_payout(
                    withdrawal_id=request.id,
                    actor_user_id=ADMIN_ID,
                    environment_live_enabled=True,
                    provider_enabled=True,
                    credentials_configured=True,
                )
                assert queued.status == "QUEUED"
                assert attempt.status == "CREATED"
                payload = await service.begin_payout_submission(request.id)
                assert payload is not None
                assert payload["account_number"] == "0123456789"
                assert payload["amount_minor"] == 200_000
                unknown = await service.record_payout_state(
                    withdrawal_id=request.id,
                    provider_payout_id=None,
                    state="UNKNOWN",
                )
                assert (
                    unknown is not None
                    and unknown.status == "RECONCILIATION_REQUIRED"
                )
                async with session.begin():
                    _available, reserved = await FinanceLedger(session).user_accounts(
                        owner.user_id
                    )
                    assert await FinanceLedger(session).balance(reserved.id) == 200_000
                reconciliation = await service.reconciliation_summary()
                assert reconciliation["unbalanced_journals"] == 0
                exceptions = reconciliation["payout_exceptions"]
                assert isinstance(exceptions, list) and len(exceptions) == 1
                assert exceptions[0]["status"] == "UNKNOWN"
                result = await service.record_payout_state(
                    withdrawal_id=request.id,
                    provider_payout_id="payout-mock-1",
                    state="SUCCEEDED",
                )
                assert result is not None and result.status == "SUCCEEDED"
                async with session.begin():
                    available, reserved = await FinanceLedger(session).user_accounts(
                        owner.user_id
                    )
                    payout = await FinanceLedger(session).platform_account(
                        "PAYOUT_SETTLEMENT"
                    )
                    assert await FinanceLedger(session).balance(available.id) == 600_000
                    assert await FinanceLedger(session).balance(reserved.id) == 0
                    assert await FinanceLedger(session).balance(payout.id) == 200_000
        finally:
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_confirmed_payout_failure_releases_reserve_once() -> None:
    async def exercise() -> None:
        payment_service, sessions, engine, owner, cipher, bank_id = (
            await _prepared_withdrawal()
        )
        try:
            async with sessions() as session:
                service = WalletWithdrawalService(
                    session=session,
                    cipher=cipher,
                    withdrawal_feature_enabled=True,
                )
                await service.verify_bank_account(
                    bank_account_id=bank_id,
                    actor_user_id=ADMIN_ID,
                    evidence_reference="manual-check-failed-payout",
                )
                request = await service.request_withdrawal(
                    user_id=owner.user_id,
                    bank_account_id=bank_id,
                    amount_minor=200_000,
                    idempotency_key="failed-payout",
                )
                await service.approve_withdrawal(
                    withdrawal_id=request.id,
                    actor_user_id=ADMIN_ID,
                )
                async with session.begin():
                    finance_settings = await session.get(FinanceSettings, 1)
                    assert finance_settings is not None
                    finance_settings.payout_live_enabled = True
                await service.queue_payout(
                    withdrawal_id=request.id,
                    actor_user_id=ADMIN_ID,
                    environment_live_enabled=True,
                    provider_enabled=True,
                    credentials_configured=True,
                )
                assert await service.begin_payout_submission(request.id) is not None
                first = await service.record_payout_state(
                    withdrawal_id=request.id,
                    provider_payout_id="payout-mock-failed",
                    state="FAILED",
                    error_code="BANK_REJECTED",
                )
                replay = await service.record_payout_state(
                    withdrawal_id=request.id,
                    provider_payout_id="payout-mock-failed",
                    state="FAILED",
                    error_code="BANK_REJECTED",
                )
                assert first is not None and first.status == "FAILED"
                assert replay is not None and replay.status == "FAILED"
                async with session.begin():
                    ledger = FinanceLedger(session)
                    available, reserved = await ledger.user_accounts(owner.user_id)
                    assert await ledger.balance(available.id) == 800_000
                    assert await ledger.balance(reserved.id) == 0
        finally:
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_two_person_threshold_requires_distinct_approvers() -> None:
    async def exercise() -> None:
        (
            payment_service,
            sessions,
            engine,
            owner,
            cipher,
            bank_id,
        ) = await _prepared_withdrawal(threshold_minor=200_000)
        second_admin_id = uuid4()
        try:
            async with sessions() as session, session.begin():
                session.add(
                    User(
                        id=second_admin_id,
                        email=f"{second_admin_id}@example.test",
                        password_hash=None,
                        status="ACTIVE",
                    )
                )
            async with sessions() as session:
                service = WalletWithdrawalService(
                    session=session,
                    cipher=cipher,
                    withdrawal_feature_enabled=True,
                )
                await service.verify_bank_account(
                    bank_account_id=bank_id,
                    actor_user_id=ADMIN_ID,
                    evidence_reference="manual-check-large",
                )
                request = await service.request_withdrawal(
                    user_id=owner.user_id,
                    bank_account_id=bank_id,
                    amount_minor=200_000,
                    idempotency_key="two-person",
                )
                withdrawal_id = request.id
                first = await service.approve_withdrawal(
                    withdrawal_id=withdrawal_id,
                    actor_user_id=ADMIN_ID,
                )
                assert first.status == "PENDING_REVIEW"
                second = await service.approve_withdrawal(
                    withdrawal_id=withdrawal_id,
                    actor_user_id=second_admin_id,
                )
                assert second.status == "APPROVED"
                replay = await service.approve_withdrawal(
                    withdrawal_id=withdrawal_id,
                    actor_user_id=ADMIN_ID,
                )
                assert replay.status == "APPROVED"
            async with sessions() as session, session.begin():
                approvals = list(
                    await session.scalars(
                        select(WithdrawalApproval).where(
                            WithdrawalApproval.withdrawal_id == withdrawal_id
                        )
                    )
                )
                assert len(approvals) == 2
                assert await session.scalar(select(PayoutAttempt.id)) is None
        finally:
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_fee_is_calculated_in_integer_vnd_and_daily_limits_apply() -> None:
    async def exercise() -> None:
        (
            payment_service,
            sessions,
            engine,
            owner,
            cipher,
            bank_id,
        ) = await _prepared_withdrawal()
        try:
            async with sessions() as session, session.begin():
                settings = await session.get(FinanceSettings, 1)
                assert settings is not None
                settings.fee_mode = "BPS"
                settings.fee_value = 250
                bank = await session.get(BankAccount, bank_id)
                assert bank is not None
                bank.verification_status = "VERIFIED"
            async with sessions() as session:
                service = WalletWithdrawalService(
                    session=session,
                    cipher=cipher,
                    withdrawal_feature_enabled=True,
                )
                request = await service.request_withdrawal(
                    user_id=owner.user_id,
                    bank_account_id=bank_id,
                    amount_minor=500_000,
                    idempotency_key="fee-and-limit",
                )
                assert request.fee_minor == 12_500
                assert request.net_amount_minor == 487_500
                with pytest.raises(DomainError) as over_daily:
                    await service.request_withdrawal(
                        user_id=owner.user_id,
                        bank_account_id=bank_id,
                        amount_minor=500_001,
                        idempotency_key="over-daily-limit",
                    )
                assert over_daily.value.code == "WITHDRAWAL_LIMIT_EXCEEDED"
        finally:
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())
