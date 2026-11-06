from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response
from pydantic import Field

from app.core.errors import DomainError, ServiceNotReadyError
from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
    SettingsDependency,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.payments.errors import PaymentForbiddenError
from app.modules.payments.schemas import PaymentSchema
from app.modules.users.security import SensitiveFieldCipher
from app.modules.wallet.models import FinanceSettings, WithdrawalRequest
from app.modules.wallet.withdrawal_service import (
    BankAccountView,
    WalletWithdrawalService,
)
from app.workers.celery_app import celery_app

router = APIRouter(prefix="/api/v1", tags=["wallet-withdrawals"])


class BankAccountCreateRequest(PaymentSchema):
    bank_bin: Annotated[str, Field(min_length=5, max_length=12)]
    account_number: Annotated[str, Field(min_length=6, max_length=32)]
    account_name: Annotated[str, Field(min_length=2, max_length=120)]
    is_default: bool = False


class BankAccountData(PaymentSchema):
    id: UUID
    bank_bin: str
    bank_name: str
    account_number_masked: str
    account_name: str
    verification_status: str
    is_default: bool
    is_active: bool


class BankData(PaymentSchema):
    bank_bin: str
    bank_name: str


class WithdrawalCreateRequest(PaymentSchema):
    bank_account_id: UUID
    amount_minor: Annotated[int, Field(strict=True, gt=0)]


class WithdrawalData(PaymentSchema):
    id: UUID
    provider_reference: str
    bank_name_snapshot: str
    account_number_masked: str
    amount_minor: int
    fee_minor: int
    net_amount_minor: int
    status: str
    created_at: datetime
    approved_at: datetime | None
    rejected_at: datetime | None
    succeeded_at: datetime | None
    rejection_reason: str | None


class WithdrawalApprovalData(PaymentSchema):
    id: UUID
    approver_user_id: UUID
    decision: str
    reason: str | None
    created_at: datetime


class WithdrawalEventData(PaymentSchema):
    id: UUID
    event_type: str
    from_status: str | None
    to_status: str | None
    actor_user_id: UUID | None
    details_json: dict[str, object]
    created_at: datetime


class PayoutAttemptData(PaymentSchema):
    id: UUID
    reference_id: str
    provider_payout_id: str | None
    status: str
    provider_error_code: str | None
    response_redacted: dict[str, object]
    attempt_count: int
    created_at: datetime
    updated_at: datetime


class AdminWithdrawalData(WithdrawalData):
    user_id: UUID
    bank_bin_snapshot: str
    account_number: str
    account_name: str
    approvals: list[WithdrawalApprovalData]
    events: list[WithdrawalEventData]
    payout_attempts: list[PayoutAttemptData]


class WithdrawalSettingsData(PaymentSchema):
    enabled: bool
    payout_live_enabled: bool
    minimum_amount_minor: int
    maximum_amount_minor: int
    daily_limit_minor: int
    daily_count_limit: int
    fee_mode: str
    fee_value: int
    manual_approval_required: bool
    two_person_threshold_minor: int | None


class WithdrawalRejectRequest(PaymentSchema):
    reason: Annotated[str, Field(min_length=10, max_length=1_000)]


class FinanceSettingsUpdateRequest(PaymentSchema):
    withdrawal_enabled: bool
    payout_live_enabled: bool | None = None
    minimum_amount_minor: Annotated[int, Field(strict=True, gt=0)]
    maximum_amount_minor: Annotated[int, Field(strict=True, gt=0)]
    daily_limit_minor: Annotated[int, Field(strict=True, ge=0)]
    daily_count_limit: Annotated[int, Field(strict=True, ge=0)]
    fee_mode: Annotated[str, Field(pattern="^(NONE|FIXED|BPS)$")]
    fee_value: Annotated[int, Field(strict=True, ge=0)]
    two_person_threshold_minor: Annotated[int | None, Field(strict=True, gt=0)] = None


class SupportedBankUpdateRequest(PaymentSchema):
    bank_bin: Annotated[str, Field(min_length=5, max_length=12)]
    bank_name: Annotated[str, Field(min_length=2, max_length=128)]
    source_reference: Annotated[str, Field(min_length=10, max_length=512)]
    is_enabled: bool = True


class IdentityReviewRequest(PaymentSchema):
    status: Annotated[str, Field(pattern="^(VERIFIED|REJECTED)$")]
    evidence_reference: Annotated[str, Field(min_length=5, max_length=128)]
    reason: Annotated[str, Field(min_length=10, max_length=1_000)]


class BankVerificationRequest(PaymentSchema):
    evidence_reference: Annotated[str, Field(min_length=5, max_length=128)]


class FinanceReconciliationData(PaymentSchema):
    checked_journals: int
    unbalanced_journals: int
    unbalanced_journal_ids: list[str]
    checked_reserved_accounts: int
    reserved_balance_mismatches: list[dict[str, object]]
    payout_exceptions: list[dict[str, object]]


def _service(
    session: SessionDependency, settings: SettingsDependency
) -> WalletWithdrawalService:
    secret = settings.pii_encryption_key
    if secret is None or not secret.get_secret_value():
        raise ServiceNotReadyError(details={"bank_data_encryption": "not_configured"})
    return WalletWithdrawalService(
        session=session,
        cipher=SensitiveFieldCipher.from_base64(secret.get_secret_value()),
        withdrawal_feature_enabled=settings.wallet_withdrawal_enabled,
    )


def _require(principal: AuthPrincipal, permission: str) -> None:
    AuthorizationPolicy.require_capability(
        principal,
        PolicyRequirement(permission=permission),
        PaymentForbiddenError,
    )


def _bank_data(view: BankAccountView) -> BankAccountData:
    return BankAccountData.model_validate(view)


def _withdrawal_data(request: WithdrawalRequest) -> WithdrawalData:
    return WithdrawalData.model_validate(
        {
            "id": request.id,
            "provider_reference": request.provider_reference,
            "bank_name_snapshot": request.bank_name_snapshot,
            "account_number_masked": f"•••• {request.account_number_last4}",
            "amount_minor": request.amount_minor,
            "fee_minor": request.fee_minor,
            "net_amount_minor": request.net_amount_minor,
            "status": request.status,
            "created_at": request.created_at,
            "approved_at": request.approved_at,
            "rejected_at": request.rejected_at,
            "succeeded_at": request.succeeded_at,
            "rejection_reason": request.rejection_reason,
        }
    )


def _settings_data(
    settings: FinanceSettings,
    *,
    environment_enabled: bool,
    payout_environment_enabled: bool,
) -> WithdrawalSettingsData:
    return WithdrawalSettingsData(
        enabled=environment_enabled and settings.withdrawal_enabled,
        payout_live_enabled=(
            payout_environment_enabled and settings.payout_live_enabled
        ),
        minimum_amount_minor=settings.minimum_amount_minor,
        maximum_amount_minor=settings.maximum_amount_minor,
        daily_limit_minor=settings.daily_limit_minor,
        daily_count_limit=settings.daily_count_limit,
        fee_mode=settings.fee_mode,
        fee_value=settings.fee_value,
        manual_approval_required=True,
        two_person_threshold_minor=settings.two_person_threshold_minor,
    )


@router.get("/wallet/banks", response_model=SuccessEnvelope[list[BankData]])
async def list_banks(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[list[BankData]]:
    rows = await _service(session, settings).list_supported_banks()
    return SuccessEnvelope(
        data=[BankData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/wallet/bank-accounts", response_model=SuccessEnvelope[list[BankAccountData]]
)
async def list_bank_accounts(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[list[BankAccountData]]:
    rows = await _service(session, settings).bank_accounts(principal.user_id)
    return SuccessEnvelope(
        data=[_bank_data(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("/wallet/bank-accounts", response_model=SuccessEnvelope[BankAccountData])
async def create_bank_account(
    payload: BankAccountCreateRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[BankAccountData]:
    result = await _service(session, settings).add_bank_account(
        user_id=principal.user_id,
        bank_bin=payload.bank_bin,
        account_number=payload.account_number,
        account_name=payload.account_name,
        is_default=payload.is_default,
    )
    view = await _service(session, settings).bank_accounts(principal.user_id)
    data = next(item for item in view if item.id == result.id)
    return SuccessEnvelope(
        data=_bank_data(data),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/wallet/bank-accounts/{bank_account_id}/default",
    response_model=SuccessEnvelope[BankAccountData],
)
async def set_default_bank_account(
    bank_account_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[BankAccountData]:
    service = _service(session, settings)
    result = await service.set_default_bank_account(
        user_id=principal.user_id, bank_account_id=bank_account_id
    )
    view = next(
        item
        for item in await service.bank_accounts(principal.user_id)
        if item.id == result.id
    )
    return SuccessEnvelope(
        data=_bank_data(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/wallet/bank-accounts/{bank_account_id}",
    response_model=SuccessEnvelope[BankAccountData],
)
async def disable_bank_account(
    bank_account_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[BankAccountData]:
    service = _service(session, settings)
    result = await service.disable_bank_account(
        user_id=principal.user_id, bank_account_id=bank_account_id
    )
    view = next(
        item
        for item in await service.bank_accounts(principal.user_id)
        if item.id == result.id
    )
    return SuccessEnvelope(
        data=_bank_data(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/wallet/withdrawal-settings",
    response_model=SuccessEnvelope[WithdrawalSettingsData],
)
async def get_withdrawal_settings(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[WithdrawalSettingsData]:
    finance = await _service(session, settings).finance_settings()
    return SuccessEnvelope(
        data=_settings_data(
            finance,
            environment_enabled=settings.wallet_withdrawal_enabled,
            payout_environment_enabled=settings.payout_live_enabled,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/wallet/withdrawals", response_model=SuccessEnvelope[list[WithdrawalData]])
async def list_withdrawals(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SuccessEnvelope[list[WithdrawalData]]:
    rows = await _service(session, settings).list_owned_withdrawals(
        user_id=principal.user_id, limit=limit, offset=offset
    )
    return SuccessEnvelope(
        data=[_withdrawal_data(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("/wallet/withdrawals", response_model=SuccessEnvelope[WithdrawalData])
async def create_withdrawal(
    payload: WithdrawalCreateRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
) -> SuccessEnvelope[WithdrawalData]:
    result = await _service(session, settings).request_withdrawal(
        user_id=principal.user_id,
        bank_account_id=payload.bank_account_id,
        amount_minor=payload.amount_minor,
        idempotency_key=idempotency_key,
    )
    return SuccessEnvelope(
        data=_withdrawal_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/wallet/withdrawals/{withdrawal_id}",
    response_model=SuccessEnvelope[WithdrawalData],
)
async def get_withdrawal(
    withdrawal_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[WithdrawalData]:
    result = await _service(session, settings).owned_withdrawal(
        withdrawal_id=withdrawal_id, user_id=principal.user_id
    )
    return SuccessEnvelope(
        data=_withdrawal_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/wallet/withdrawals/{withdrawal_id}/cancel",
    response_model=SuccessEnvelope[WithdrawalData],
)
async def cancel_withdrawal(
    withdrawal_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[WithdrawalData]:
    result = await _service(session, settings).cancel_withdrawal(
        withdrawal_id=withdrawal_id, user_id=principal.user_id
    )
    return SuccessEnvelope(
        data=_withdrawal_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/admin/withdrawals", response_model=SuccessEnvelope[list[WithdrawalData]])
async def list_admin_withdrawals(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SuccessEnvelope[list[WithdrawalData]]:
    _require(principal, "finance.read")
    rows = await _service(session, settings).list_admin_withdrawals(
        status=status, limit=limit, offset=offset
    )
    return SuccessEnvelope(
        data=[_withdrawal_data(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/withdrawals/{withdrawal_id}",
    response_model=SuccessEnvelope[AdminWithdrawalData],
)
async def get_admin_withdrawal(
    withdrawal_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[AdminWithdrawalData]:
    _require(principal, "finance.read")
    response.headers["Cache-Control"] = "no-store"
    result = await _service(session, settings).admin_withdrawal_detail(withdrawal_id)
    withdrawal = result["request"]
    assert isinstance(withdrawal, WithdrawalRequest)
    data = _withdrawal_data(withdrawal).model_dump()
    data.update(
        {
            "user_id": withdrawal.user_id,
            "bank_bin_snapshot": withdrawal.bank_bin_snapshot,
            "account_number": result["account_number"],
            "account_name": result["account_name"],
            "approvals": [
                WithdrawalApprovalData.model_validate(item)
                for item in result["approvals"]  # type: ignore[union-attr]
            ],
            "events": [
                WithdrawalEventData.model_validate(item)
                for item in result["events"]  # type: ignore[union-attr]
            ],
            "payout_attempts": [
                PayoutAttemptData.model_validate(item)
                for item in result["payout_attempts"]  # type: ignore[union-attr]
            ],
        }
    )
    return SuccessEnvelope(
        data=AdminWithdrawalData.model_validate(data),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/withdrawals/{withdrawal_id}/approve",
    response_model=SuccessEnvelope[WithdrawalData],
)
async def approve_withdrawal(
    withdrawal_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[WithdrawalData]:
    _require(principal, "finance.withdrawals.approve")
    result = await _service(session, settings).approve_withdrawal(
        withdrawal_id=withdrawal_id, actor_user_id=principal.user_id
    )
    return SuccessEnvelope(
        data=_withdrawal_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/withdrawals/{withdrawal_id}/payout",
    response_model=SuccessEnvelope[WithdrawalData],
)
async def queue_withdrawal_payout(
    withdrawal_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[WithdrawalData]:
    _require(principal, "finance.payouts.execute")
    credentials_configured = all(
        secret is not None and bool(secret.get_secret_value())
        for secret in (
            settings.payos_payout_client_id,
            settings.payos_payout_api_key,
            settings.payos_payout_checksum_key,
        )
    )
    result, _attempt = await _service(session, settings).queue_payout(
        withdrawal_id=withdrawal_id,
        actor_user_id=principal.user_id,
        environment_live_enabled=settings.payout_live_enabled,
        provider_enabled=settings.payos_payout_provider == "payos",
        credentials_configured=credentials_configured,
    )
    celery_app.send_task("app.workers.payout_tasks.process_queued_payouts")
    return SuccessEnvelope(
        data=_withdrawal_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/withdrawals/{withdrawal_id}/reject",
    response_model=SuccessEnvelope[WithdrawalData],
)
async def reject_withdrawal(
    withdrawal_id: UUID,
    payload: WithdrawalRejectRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[WithdrawalData]:
    _require(principal, "finance.withdrawals.approve")
    result = await _service(session, settings).reject_withdrawal(
        withdrawal_id=withdrawal_id,
        actor_user_id=principal.user_id,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=_withdrawal_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/withdrawals/{withdrawal_id}/verify-bank",
    response_model=SuccessEnvelope[BankAccountData],
)
async def verify_withdrawal_bank(
    withdrawal_id: UUID,
    payload: BankVerificationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[BankAccountData]:
    _require(principal, "finance.identity.verify")
    service = _service(session, settings)
    detail = await service.admin_withdrawal_detail(withdrawal_id)
    withdrawal = detail["request"]
    assert isinstance(withdrawal, WithdrawalRequest)
    account = await service.verify_bank_account(
        bank_account_id=withdrawal.bank_account_id,
        actor_user_id=principal.user_id,
        evidence_reference=payload.evidence_reference,
    )
    row = next(
        item
        for item in await service.bank_accounts(withdrawal.user_id)
        if item.id == account.id
    )
    return SuccessEnvelope(
        data=_bank_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/finance/users/{user_id}/identity-verification",
    response_model=SuccessEnvelope[dict[str, object]],
)
async def review_financial_identity(
    user_id: UUID,
    payload: IdentityReviewRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[dict[str, object]]:
    _require(principal, "finance.identity.verify")
    row = await _service(session, settings).set_identity_verification(
        user_id=user_id,
        actor_user_id=principal.user_id,
        status=payload.status,
        evidence_reference=payload.evidence_reference,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data={
            "user_id": row.user_id,
            "status": row.status,
            "checked_at": row.checked_at,
        },
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/finance/settings",
    response_model=SuccessEnvelope[WithdrawalSettingsData],
)
async def get_finance_settings(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[WithdrawalSettingsData]:
    _require(principal, "finance.settings.manage")
    finance = await _service(session, settings).finance_settings()
    return SuccessEnvelope(
        data=_settings_data(
            finance,
            environment_enabled=settings.wallet_withdrawal_enabled,
            payout_environment_enabled=settings.payout_live_enabled,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/admin/finance/settings",
    response_model=SuccessEnvelope[WithdrawalSettingsData],
)
async def update_finance_settings(
    payload: FinanceSettingsUpdateRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[WithdrawalSettingsData]:
    _require(principal, "finance.settings.manage")
    payout_credentials_configured = all(
        secret is not None and bool(secret.get_secret_value())
        for secret in (
            settings.payos_payout_client_id,
            settings.payos_payout_api_key,
            settings.payos_payout_checksum_key,
        )
    )
    if payload.payout_live_enabled is True and not (
        settings.payout_live_enabled
        and settings.payos_payout_provider == "payos"
        and payout_credentials_configured
    ):
        raise DomainError(
            code="PAYOUT_PROVIDER_NOT_READY",
            message="Live payout environment, provider, and credentials are required.",
            status_code=409,
        )
    finance = await _service(session, settings).update_finance_settings(
        actor_user_id=principal.user_id,
        withdrawal_enabled=payload.withdrawal_enabled,
        payout_live_enabled=payload.payout_live_enabled,
        minimum_amount_minor=payload.minimum_amount_minor,
        maximum_amount_minor=payload.maximum_amount_minor,
        daily_limit_minor=payload.daily_limit_minor,
        daily_count_limit=payload.daily_count_limit,
        fee_mode=payload.fee_mode,
        fee_value=payload.fee_value,
        two_person_threshold_minor=payload.two_person_threshold_minor,
    )
    return SuccessEnvelope(
        data=_settings_data(
            finance,
            environment_enabled=settings.wallet_withdrawal_enabled,
            payout_environment_enabled=settings.payout_live_enabled,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("/admin/finance/banks", response_model=SuccessEnvelope[BankData])
async def update_supported_bank(
    payload: SupportedBankUpdateRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[BankData]:
    _require(principal, "finance.banks.manage")
    bank = await _service(session, settings).save_supported_bank(
        actor_user_id=principal.user_id,
        bank_bin=payload.bank_bin,
        bank_name=payload.bank_name,
        source_reference=payload.source_reference,
        is_enabled=payload.is_enabled,
    )
    return SuccessEnvelope(
        data=BankData.model_validate(bank),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/payouts/reconciliation",
    response_model=SuccessEnvelope[FinanceReconciliationData],
)
async def get_finance_reconciliation(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[FinanceReconciliationData]:
    _require(principal, "finance.read")
    result = await _service(session, settings).reconciliation_summary()
    return SuccessEnvelope(
        data=FinanceReconciliationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
