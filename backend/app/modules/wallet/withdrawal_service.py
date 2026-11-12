from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import TypedDict
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserPermission,
    UserRole,
    UserStatus,
)
from app.modules.notifications.models import Notification
from app.modules.users.security import SensitiveFieldCipher
from app.modules.wallet.models import (
    BankAccount,
    FinanceAccount,
    FinanceEntry,
    FinanceJournal,
    FinanceSettings,
    FinancialIdentityVerification,
    PayoutAttempt,
    SupportedBank,
    WithdrawalApproval,
    WithdrawalEvent,
    WithdrawalRequest,
)
from app.modules.wallet.service import FinanceLedger, valid_key


@dataclass(frozen=True, slots=True)
class BankAccountView:
    id: UUID
    bank_bin: str
    bank_name: str
    account_number_masked: str
    account_name: str
    verification_status: str
    is_default: bool
    is_active: bool


class AdminWithdrawalDetail(TypedDict):
    request: WithdrawalRequest
    account_number: str
    account_name: str
    approvals: tuple[WithdrawalApproval, ...]
    events: tuple[WithdrawalEvent, ...]
    payout_attempts: tuple[PayoutAttempt, ...]


class PayoutSubmission(TypedDict):
    attempt_id: UUID
    reference_id: str
    idempotency_key: str
    amount_minor: int
    bank_bin: str
    account_number: str


class WalletWithdrawalService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        cipher: SensitiveFieldCipher,
        withdrawal_feature_enabled: bool,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.cipher = cipher
        self.withdrawal_feature_enabled = withdrawal_feature_enabled
        self.clock = clock or (lambda: datetime.now(UTC))

    async def list_supported_banks(self) -> tuple[SupportedBank, ...]:
        async with self.session.begin():
            return tuple(
                await self.session.scalars(
                    select(SupportedBank)
                    .where(SupportedBank.is_enabled.is_(True))
                    .order_by(SupportedBank.bank_name)
                )
            )

    async def add_bank_account(
        self,
        *,
        user_id: UUID,
        bank_bin: str,
        account_number: str,
        account_name: str,
        is_default: bool = False,
    ) -> BankAccount:
        bank_bin = bank_bin.strip()
        account_number = account_number.strip()
        account_name = " ".join(account_name.split())
        if not bank_bin.isdigit() or not 5 <= len(bank_bin) <= 12:
            raise DomainError(
                code="BANK_IDENTIFIER_INVALID",
                message="Ngân hàng đã chọn không hợp lệ.",
                status_code=422,
            )
        if not account_number.isdigit() or not 6 <= len(account_number) <= 32:
            raise DomainError(
                code="BANK_ACCOUNT_INVALID",
                message="Số tài khoản ngân hàng không hợp lệ.",
                status_code=422,
            )
        if (
            len(account_name) < 2
            or len(account_name) > 120
            or any(ord(character) < 32 for character in account_name)
        ):
            raise DomainError(
                code="BANK_ACCOUNT_NAME_INVALID",
                message="Tên chủ tài khoản không hợp lệ.",
                status_code=422,
            )

        async with self.session.begin():
            bank = await self.session.scalar(
                select(SupportedBank).where(
                    SupportedBank.bank_bin == bank_bin,
                    SupportedBank.is_enabled.is_(True),
                )
            )
            if bank is None:
                raise DomainError(
                    code="BANK_NOT_SUPPORTED",
                    message="Ngân hàng này chưa nằm trong danh sách được hỗ trợ.",
                    status_code=422,
                )
            existing_default = await self.session.scalar(
                select(BankAccount.id).where(
                    BankAccount.user_id == user_id,
                    BankAccount.is_active.is_(True),
                    BankAccount.is_default.is_(True),
                )
            )
            make_default = is_default or existing_default is None
            if make_default:
                await self.session.execute(
                    update(BankAccount)
                    .where(
                        BankAccount.user_id == user_id,
                        BankAccount.is_active.is_(True),
                    )
                    .values(is_default=False)
                )
            account = BankAccount(
                user_id=user_id,
                bank_bin=bank.bank_bin,
                bank_name_snapshot=bank.bank_name,
                account_number_ciphertext=self.cipher.encrypt(account_number),
                account_name_ciphertext=self.cipher.encrypt(account_name),
                account_number_last4=account_number[-4:],
                verification_status="UNVERIFIED",
                is_default=make_default,
                is_active=True,
            )
            self.session.add(account)
            await self.session.flush()
            self._audit(
                actor_user_id=user_id,
                action="wallet.bank_account.created",
                resource_type="wallet_bank_account",
                resource_id=str(account.id),
                after={
                    "bank_bin": bank.bank_bin,
                    "account_number_last4": account.account_number_last4,
                    "verification_status": account.verification_status,
                    "is_default": account.is_default,
                },
            )
            self._notify(
                user_id=user_id,
                event_id=account.id,
                event_type="WALLET_BANK_ACCOUNT_ADDED",
                title="Đã thêm tài khoản ngân hàng",
                body="Tài khoản ngân hàng mới đã được lưu an toàn.",
                data={"actionPath": "/wallet"},
            )
            return account

    async def bank_accounts(self, user_id: UUID) -> tuple[BankAccountView, ...]:
        async with self.session.begin():
            rows = tuple(
                await self.session.scalars(
                    select(BankAccount)
                    .where(BankAccount.user_id == user_id)
                    .order_by(
                        BankAccount.is_active.desc(), BankAccount.is_default.desc()
                    )
                )
            )
            return tuple(self._bank_view(row) for row in rows)

    def _bank_view(self, account: BankAccount) -> BankAccountView:
        return BankAccountView(
            id=account.id,
            bank_bin=account.bank_bin,
            bank_name=account.bank_name_snapshot,
            account_number_masked=f"•••• {account.account_number_last4}",
            account_name=self.cipher.decrypt(account.account_name_ciphertext),
            verification_status=account.verification_status,
            is_default=account.is_default,
            is_active=account.is_active,
        )

    async def set_default_bank_account(
        self, *, user_id: UUID, bank_account_id: UUID
    ) -> BankAccount:
        async with self.session.begin():
            account = await self.session.scalar(
                select(BankAccount)
                .where(
                    BankAccount.id == bank_account_id,
                    BankAccount.user_id == user_id,
                    BankAccount.is_active.is_(True),
                )
                .with_for_update()
            )
            if account is None:
                raise self._not_found("BANK_ACCOUNT_NOT_FOUND")
            await self.session.execute(
                update(BankAccount)
                .where(
                    BankAccount.user_id == user_id,
                    BankAccount.is_active.is_(True),
                )
                .values(is_default=False)
            )
            account.is_default = True
            self._audit(
                actor_user_id=user_id,
                action="wallet.bank_account.default_changed",
                resource_type="wallet_bank_account",
                resource_id=str(account.id),
                after={"is_default": True},
            )
            return account

    async def disable_bank_account(
        self, *, user_id: UUID, bank_account_id: UUID
    ) -> BankAccount:
        async with self.session.begin():
            account = await self.session.scalar(
                select(BankAccount)
                .where(
                    BankAccount.id == bank_account_id,
                    BankAccount.user_id == user_id,
                    BankAccount.is_active.is_(True),
                )
                .with_for_update()
            )
            if account is None:
                raise self._not_found("BANK_ACCOUNT_NOT_FOUND")
            account.is_active = False
            account.is_default = False
            next_default = await self.session.scalar(
                select(BankAccount)
                .where(
                    BankAccount.user_id == user_id,
                    BankAccount.is_active.is_(True),
                )
                .order_by(BankAccount.created_at, BankAccount.id)
                .with_for_update()
            )
            if next_default is not None:
                next_default.is_default = True
            self._audit(
                actor_user_id=user_id,
                action="wallet.bank_account.disabled",
                resource_type="wallet_bank_account",
                resource_id=str(account.id),
                after={
                    "is_active": False,
                    "new_default_id": str(next_default.id) if next_default else None,
                },
            )
            return account

    async def verify_bank_account(
        self,
        *,
        bank_account_id: UUID,
        actor_user_id: UUID,
        evidence_reference: str,
    ) -> BankAccount:
        evidence_reference = evidence_reference.strip()
        if not 5 <= len(evidence_reference) <= 128:
            raise DomainError(
                code="BANK_VERIFICATION_EVIDENCE_REQUIRED",
                message="Cần mã tham chiếu kiểm tra tài khoản ngân hàng.",
                status_code=422,
            )
        async with self.session.begin():
            account = await self.session.scalar(
                select(BankAccount)
                .where(BankAccount.id == bank_account_id)
                .with_for_update()
            )
            if account is None:
                raise self._not_found("BANK_ACCOUNT_NOT_FOUND")
            if account.verification_status == "VERIFIED":
                return account
            account.verification_status = "VERIFIED"
            self._audit(
                actor_user_id=actor_user_id,
                action="wallet.bank_account.verified",
                resource_type="wallet_bank_account",
                resource_id=str(account.id),
                after={
                    "verification_status": "VERIFIED",
                    "evidence_reference": evidence_reference,
                },
            )
            return account

    async def set_identity_verification(
        self,
        *,
        user_id: UUID,
        actor_user_id: UUID,
        status: str,
        evidence_reference: str,
        reason: str,
        method: str = "MANUAL",
    ) -> FinancialIdentityVerification:
        evidence_reference = evidence_reference.strip()
        reason = reason.strip()
        if status not in {"VERIFIED", "REJECTED"}:
            raise DomainError(
                code="IDENTITY_STATUS_INVALID",
                message="Trạng thái xác minh danh tính không hợp lệ.",
                status_code=422,
            )
        if not 5 <= len(evidence_reference) <= 128 or not 10 <= len(reason) <= 1_000:
            raise DomainError(
                code="IDENTITY_REVIEW_DETAILS_REQUIRED",
                message="Cần mã chứng từ và lý do kiểm tra hợp lệ.",
                status_code=422,
            )
        async with self.session.begin():
            user = await self.session.get(User, user_id)
            if user is None:
                raise self._not_found("USER_NOT_FOUND")
            row = await self.session.scalar(
                select(FinancialIdentityVerification)
                .where(FinancialIdentityVerification.user_id == user_id)
                .with_for_update()
            )
            before_status = row.status if row else None
            if row is None:
                row = FinancialIdentityVerification(user_id=user_id, status=status)
                self.session.add(row)
            row.status = status
            row.verification_method = method[:32]
            row.evidence_reference = evidence_reference
            row.checked_by_user_id = actor_user_id
            row.checked_at = self.clock()
            row.reason = reason
            self._audit(
                actor_user_id=actor_user_id,
                action="wallet.identity_verification.reviewed",
                resource_type="financial_identity_verification",
                resource_id=str(user_id),
                before={"status": before_status},
                after={"status": status, "evidence_reference": evidence_reference},
            )
            await self.session.flush()
            return row

    async def request_withdrawal(
        self,
        *,
        user_id: UUID,
        bank_account_id: UUID,
        amount_minor: int,
        idempotency_key: str,
    ) -> WithdrawalRequest:
        if type(amount_minor) is not int or amount_minor <= 0:
            raise DomainError(
                code="WITHDRAWAL_AMOUNT_INVALID",
                message="Số tiền rút không hợp lệ.",
                status_code=422,
            )
        idempotency_key = valid_key(idempotency_key)
        async with self.session.begin():
            existing = await self.session.scalar(
                select(WithdrawalRequest).where(
                    WithdrawalRequest.user_id == user_id,
                    WithdrawalRequest.idempotency_key == idempotency_key,
                )
            )
            if isinstance(existing, WithdrawalRequest):
                if (
                    existing.amount_minor != amount_minor
                    or existing.bank_account_id != bank_account_id
                ):
                    raise DomainError(
                        code="WITHDRAWAL_IDEMPOTENCY_CONFLICT",
                        message=(
                            "Khóa yêu cầu đã được sử dụng cho một yêu cầu rút khác."
                        ),
                        status_code=409,
                    )
                return existing

            settings = await self._finance_settings(lock=True)
            if not self.withdrawal_feature_enabled or not settings.withdrawal_enabled:
                raise self._unavailable()
            if settings.daily_limit_minor <= 0 or settings.daily_count_limit <= 0:
                raise self._unavailable()
            user = await self.session.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
            if (
                user is None
                or user.status is not UserStatus.ACTIVE
                or user.email_verified_at is None
                or user.is_test_account
            ):
                raise DomainError(
                    code="WITHDRAWAL_ACCOUNT_INELIGIBLE",
                    message="Tài khoản chưa đủ điều kiện tạo yêu cầu rút.",
                    status_code=403,
                )
            # Recheck after the per-user lock so concurrent retries cannot race
            # past the first lookup and collide with the unique idempotency key.
            existing = await self.session.scalar(
                select(WithdrawalRequest).where(
                    WithdrawalRequest.user_id == user_id,
                    WithdrawalRequest.idempotency_key == idempotency_key,
                )
            )
            if isinstance(existing, WithdrawalRequest):
                if (
                    existing.amount_minor != amount_minor
                    or existing.bank_account_id != bank_account_id
                ):
                    raise DomainError(
                        code="WITHDRAWAL_IDEMPOTENCY_CONFLICT",
                        message=(
                            "Khóa yêu cầu đã được sử dụng cho một yêu cầu rút khác."
                        ),
                        status_code=409,
                    )
                return existing
            identity = await self.session.scalar(
                select(FinancialIdentityVerification).where(
                    FinancialIdentityVerification.user_id == user_id,
                    FinancialIdentityVerification.status == "VERIFIED",
                )
            )
            if identity is None:
                raise DomainError(
                    code="WITHDRAWAL_IDENTITY_REQUIRED",
                    message="Cần hoàn tất xác minh danh tính trước khi rút tiền.",
                    status_code=403,
                )
            account = await self.session.scalar(
                select(BankAccount)
                .where(
                    BankAccount.id == bank_account_id,
                    BankAccount.user_id == user_id,
                    BankAccount.is_active.is_(True),
                )
                .with_for_update()
            )
            if account is None:
                raise self._not_found("BANK_ACCOUNT_NOT_FOUND")
            bank = await self.session.scalar(
                select(SupportedBank).where(
                    SupportedBank.bank_bin == account.bank_bin,
                    SupportedBank.is_enabled.is_(True),
                )
            )
            if bank is None:
                raise DomainError(
                    code="BANK_NOT_SUPPORTED",
                    message="Ngân hàng nhận tiền hiện không được hỗ trợ.",
                    status_code=409,
                )
            if not (
                settings.minimum_amount_minor
                <= amount_minor
                <= settings.maximum_amount_minor
            ):
                raise DomainError(
                    code="WITHDRAWAL_AMOUNT_OUT_OF_RANGE",
                    message="Số tiền nằm ngoài hạn mức rút hiện tại.",
                    status_code=422,
                )

            now = self.clock()
            day_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
            daily_count = await self.session.scalar(
                select(func.count(WithdrawalRequest.id)).where(
                    WithdrawalRequest.user_id == user_id,
                    WithdrawalRequest.created_at >= day_start,
                )
            )
            daily_total = await self.session.scalar(
                select(
                    func.coalesce(func.sum(WithdrawalRequest.amount_minor), 0)
                ).where(
                    WithdrawalRequest.user_id == user_id,
                    WithdrawalRequest.created_at >= day_start,
                )
            )
            if (
                int(daily_count or 0) >= settings.daily_count_limit
                or int(daily_total or 0) + amount_minor > settings.daily_limit_minor
            ):
                raise DomainError(
                    code="WITHDRAWAL_LIMIT_EXCEEDED",
                    message="Yêu cầu vượt giới hạn rút trong ngày.",
                    status_code=409,
                )

            fee_minor = self._fee(settings, amount_minor)
            net_amount_minor = amount_minor - fee_minor
            if net_amount_minor <= 0:
                raise DomainError(
                    code="WITHDRAWAL_FEE_INVALID",
                    message="Phí rút hiện tại vượt số tiền yêu cầu.",
                    status_code=422,
                )
            ledger = FinanceLedger(self.session)
            available, reserved = await ledger.user_accounts(user_id)
            if await ledger.balance(available.id) < amount_minor:
                raise DomainError(
                    code="WALLET_INSUFFICIENT_FUNDS",
                    message="Số dư hoa hồng khả dụng không đủ.",
                    status_code=409,
                )

            withdrawal_id = uuid4()
            request = WithdrawalRequest(
                id=withdrawal_id,
                user_id=user_id,
                bank_account_id=account.id,
                bank_bin_snapshot=account.bank_bin,
                bank_name_snapshot=account.bank_name_snapshot,
                account_number_ciphertext=account.account_number_ciphertext,
                account_name_ciphertext=account.account_name_ciphertext,
                account_number_last4=account.account_number_last4,
                amount_minor=amount_minor,
                fee_minor=fee_minor,
                net_amount_minor=net_amount_minor,
                status="PENDING_REVIEW",
                idempotency_key=idempotency_key,
                provider_reference=f"THV-WDR-{withdrawal_id.hex.upper()}",
            )
            self.session.add(request)
            await self.session.flush()
            await ledger.transfer(
                source_account_id=available.id,
                target_account_id=reserved.id,
                amount_minor=amount_minor,
                transaction_type="WITHDRAWAL_RESERVE",
                idempotency_key=f"withdrawal:{withdrawal_id}:reserve",
                source_reference=f"withdrawal:{withdrawal_id}:reserve",
                description="Reserve approved affiliate commission for review",
                actor_user_id=user_id,
            )
            event = self._event(
                withdrawal_id=withdrawal_id,
                event_type="REQUESTED",
                from_status=None,
                to_status="PENDING_REVIEW",
                actor_user_id=user_id,
                details={"amount_minor": amount_minor, "fee_minor": fee_minor},
            )
            self._audit(
                actor_user_id=user_id,
                action="wallet.withdrawal.created",
                resource_type="withdrawal_request",
                resource_id=str(withdrawal_id),
                after={
                    "amount_minor": amount_minor,
                    "fee_minor": fee_minor,
                    "net_amount_minor": net_amount_minor,
                    "status": request.status,
                    "bank_bin": account.bank_bin,
                    "account_number_last4": account.account_number_last4,
                },
            )
            self._notify(
                user_id=user_id,
                event_id=event.id,
                event_type="WITHDRAWAL_REQUESTED",
                title="Đã nhận yêu cầu rút hoa hồng",
                body="Yêu cầu đang chờ bộ phận tài chính kiểm tra.",
                data={"actionPath": "/wallet", "withdrawalId": str(withdrawal_id)},
            )
            await self._notify_finance_admins(event, request)
            await self.session.flush()
            return request

    async def approve_withdrawal(
        self, *, withdrawal_id: UUID, actor_user_id: UUID
    ) -> WithdrawalRequest:
        async with self.session.begin():
            request = await self._withdrawal_for_update(withdrawal_id)
            if request.status == "APPROVED":
                return request
            if request.status != "PENDING_REVIEW":
                raise self._state_conflict()
            if request.user_id == actor_user_id:
                raise DomainError(
                    code="WITHDRAWAL_SELF_APPROVAL_FORBIDDEN",
                    message="Người tạo yêu cầu không thể phê duyệt yêu cầu đó.",
                    status_code=403,
                )
            identity = await self.session.scalar(
                select(FinancialIdentityVerification).where(
                    FinancialIdentityVerification.user_id == request.user_id,
                    FinancialIdentityVerification.status == "VERIFIED",
                )
            )
            account = await self.session.scalar(
                select(BankAccount)
                .where(BankAccount.id == request.bank_account_id)
                .with_for_update()
            )
            if identity is None:
                raise DomainError(
                    code="WITHDRAWAL_IDENTITY_REQUIRED",
                    message="Yêu cầu cần xác minh danh tính trước khi duyệt.",
                    status_code=409,
                )
            if (
                account is None
                or not account.is_active
                or account.verification_status != "VERIFIED"
            ):
                raise DomainError(
                    code="BANK_ACCOUNT_UNVERIFIED",
                    message="Tài khoản ngân hàng cần được kiểm tra trước khi duyệt.",
                    status_code=409,
                )
            previous = await self.session.scalar(
                select(WithdrawalApproval).where(
                    WithdrawalApproval.withdrawal_id == withdrawal_id,
                    WithdrawalApproval.approver_user_id == actor_user_id,
                )
            )
            if previous is not None:
                if previous.decision == "APPROVE":
                    return request
                raise self._state_conflict()
            approval = WithdrawalApproval(
                withdrawal_id=withdrawal_id,
                approver_user_id=actor_user_id,
                decision="APPROVE",
            )
            self.session.add(approval)
            await self.session.flush()
            settings = await self._finance_settings(lock=True)
            required_count = (
                2
                if settings.two_person_threshold_minor is not None
                and request.amount_minor >= settings.two_person_threshold_minor
                else 1
            )
            approvals = int(
                await self.session.scalar(
                    select(func.count(WithdrawalApproval.id)).where(
                        WithdrawalApproval.withdrawal_id == withdrawal_id,
                        WithdrawalApproval.decision == "APPROVE",
                    )
                )
                or 0
            )
            if approvals < required_count:
                self._event(
                    withdrawal_id=withdrawal_id,
                    event_type="APPROVAL_RECORDED",
                    from_status=request.status,
                    to_status=request.status,
                    actor_user_id=actor_user_id,
                    details={
                        "approval_count": approvals,
                        "required_count": required_count,
                    },
                )
                self._audit(
                    actor_user_id=actor_user_id,
                    action="wallet.withdrawal.approval_recorded",
                    resource_type="withdrawal_request",
                    resource_id=str(withdrawal_id),
                    after={
                        "approval_count": approvals,
                        "required_count": required_count,
                    },
                )
                return request

            request.status = "APPROVED"
            request.approved_at = self.clock()
            request.approved_by_user_id = actor_user_id
            event = self._event(
                withdrawal_id=withdrawal_id,
                event_type="APPROVED",
                from_status="PENDING_REVIEW",
                to_status="APPROVED",
                actor_user_id=actor_user_id,
                details={"approval_count": approvals},
            )
            self._audit(
                actor_user_id=actor_user_id,
                action="wallet.withdrawal.approved",
                resource_type="withdrawal_request",
                resource_id=str(withdrawal_id),
                before={"status": "PENDING_REVIEW"},
                after={"status": "APPROVED", "approval_count": approvals},
            )
            self._notify(
                user_id=request.user_id,
                event_id=event.id,
                event_type="WITHDRAWAL_APPROVED",
                title="Yêu cầu rút đã được phê duyệt",
                body="Yêu cầu đang chờ bước xử lý chi trả theo quy trình tài chính.",
                data={"actionPath": "/wallet", "withdrawalId": str(withdrawal_id)},
            )
            return request

    async def reject_withdrawal(
        self, *, withdrawal_id: UUID, actor_user_id: UUID, reason: str
    ) -> WithdrawalRequest:
        reason = reason.strip()
        if not 10 <= len(reason) <= 1_000:
            raise DomainError(
                code="WITHDRAWAL_REJECTION_REASON_REQUIRED",
                message="Cần nhập lý do từ chối hợp lệ.",
                status_code=422,
            )
        async with self.session.begin():
            request = await self._withdrawal_for_update(withdrawal_id)
            if request.status != "PENDING_REVIEW":
                raise self._state_conflict()
            if request.user_id == actor_user_id:
                raise DomainError(
                    code="WITHDRAWAL_SELF_APPROVAL_FORBIDDEN",
                    message="Người tạo yêu cầu không thể xử lý quyết định tài chính.",
                    status_code=403,
                )
            previous = await self.session.scalar(
                select(WithdrawalApproval).where(
                    WithdrawalApproval.withdrawal_id == withdrawal_id,
                    WithdrawalApproval.approver_user_id == actor_user_id,
                )
            )
            if previous is not None:
                raise self._state_conflict()
            self.session.add(
                WithdrawalApproval(
                    withdrawal_id=withdrawal_id,
                    approver_user_id=actor_user_id,
                    decision="REJECT",
                    reason=reason,
                )
            )
            await self._release_reservation(request, actor_user_id)
            request.status = "REJECTED"
            request.rejected_at = self.clock()
            request.rejected_by_user_id = actor_user_id
            request.rejection_reason = reason
            event = self._event(
                withdrawal_id=withdrawal_id,
                event_type="REJECTED",
                from_status="PENDING_REVIEW",
                to_status="REJECTED",
                actor_user_id=actor_user_id,
                details={"reason": reason},
            )
            self._audit(
                actor_user_id=actor_user_id,
                action="wallet.withdrawal.rejected",
                resource_type="withdrawal_request",
                resource_id=str(withdrawal_id),
                before={"status": "PENDING_REVIEW"},
                after={"status": "REJECTED", "reason": reason},
            )
            self._notify(
                user_id=request.user_id,
                event_id=event.id,
                event_type="WITHDRAWAL_REJECTED",
                title="Yêu cầu rút chưa được chấp thuận",
                body=reason[:500],
                data={"actionPath": "/wallet", "withdrawalId": str(withdrawal_id)},
            )
            await self.session.flush()
            return request

    async def cancel_withdrawal(
        self, *, withdrawal_id: UUID, user_id: UUID
    ) -> WithdrawalRequest:
        async with self.session.begin():
            request = await self.session.scalar(
                select(WithdrawalRequest)
                .where(
                    WithdrawalRequest.id == withdrawal_id,
                    WithdrawalRequest.user_id == user_id,
                )
                .with_for_update()
            )
            if request is None:
                raise self._not_found("WITHDRAWAL_NOT_FOUND")
            if request.status != "PENDING_REVIEW":
                raise self._state_conflict()
            await self._release_reservation(request, user_id)
            request.status = "CANCELLED"
            event = self._event(
                withdrawal_id=withdrawal_id,
                event_type="CANCELLED",
                from_status="PENDING_REVIEW",
                to_status="CANCELLED",
                actor_user_id=user_id,
                details={},
            )
            self._audit(
                actor_user_id=user_id,
                action="wallet.withdrawal.cancelled",
                resource_type="withdrawal_request",
                resource_id=str(withdrawal_id),
                before={"status": "PENDING_REVIEW"},
                after={"status": "CANCELLED"},
            )
            self._notify(
                user_id=user_id,
                event_id=event.id,
                event_type="WITHDRAWAL_CANCELLED",
                title="Đã hủy yêu cầu rút",
                body="Số dư hoa hồng được hoàn lại vào khả dụng.",
                data={"actionPath": "/wallet", "withdrawalId": str(withdrawal_id)},
            )
            await self.session.flush()
            return request

    async def owned_withdrawal(
        self, *, withdrawal_id: UUID, user_id: UUID
    ) -> WithdrawalRequest:
        async with self.session.begin():
            request = await self.session.scalar(
                select(WithdrawalRequest).where(
                    WithdrawalRequest.id == withdrawal_id,
                    WithdrawalRequest.user_id == user_id,
                )
            )
            if request is None:
                raise self._not_found("WITHDRAWAL_NOT_FOUND")
            return request

    async def list_owned_withdrawals(
        self, *, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> tuple[WithdrawalRequest, ...]:
        async with self.session.begin():
            return tuple(
                await self.session.scalars(
                    select(WithdrawalRequest)
                    .where(WithdrawalRequest.user_id == user_id)
                    .order_by(
                        WithdrawalRequest.created_at.desc(), WithdrawalRequest.id.desc()
                    )
                    .limit(min(max(limit, 1), 100))
                    .offset(max(offset, 0))
                )
            )

    async def list_admin_withdrawals(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[WithdrawalRequest, ...]:
        async with self.session.begin():
            statement = select(WithdrawalRequest)
            if status is not None:
                if status not in {
                    "PENDING_REVIEW",
                    "APPROVED",
                    "REJECTED",
                    "QUEUED",
                    "PROCESSING",
                    "SUCCEEDED",
                    "FAILED",
                    "CANCELLED",
                    "RECONCILIATION_REQUIRED",
                }:
                    raise DomainError(
                        code="WITHDRAWAL_STATUS_FILTER_INVALID",
                        message="Bộ lọc trạng thái không hợp lệ.",
                        status_code=422,
                    )
                statement = statement.where(WithdrawalRequest.status == status)
            return tuple(
                await self.session.scalars(
                    statement.order_by(
                        WithdrawalRequest.created_at.desc(), WithdrawalRequest.id.desc()
                    )
                    .limit(min(max(limit, 1), 100))
                    .offset(max(offset, 0))
                )
            )

    async def admin_withdrawal_detail(
        self, withdrawal_id: UUID
    ) -> AdminWithdrawalDetail:
        async with self.session.begin():
            request = await self.session.get(WithdrawalRequest, withdrawal_id)
            if request is None:
                raise self._not_found("WITHDRAWAL_NOT_FOUND")
            approvals = tuple(
                await self.session.scalars(
                    select(WithdrawalApproval)
                    .where(WithdrawalApproval.withdrawal_id == withdrawal_id)
                    .order_by(WithdrawalApproval.created_at, WithdrawalApproval.id)
                )
            )
            events = tuple(
                await self.session.scalars(
                    select(WithdrawalEvent)
                    .where(WithdrawalEvent.withdrawal_id == withdrawal_id)
                    .order_by(WithdrawalEvent.created_at, WithdrawalEvent.id)
                )
            )
            payout_attempts = tuple(
                await self.session.scalars(
                    select(PayoutAttempt)
                    .where(PayoutAttempt.withdrawal_id == withdrawal_id)
                    .order_by(PayoutAttempt.created_at, PayoutAttempt.id)
                )
            )
            return {
                "request": request,
                "account_number": self.cipher.decrypt(
                    request.account_number_ciphertext
                ),
                "account_name": self.cipher.decrypt(request.account_name_ciphertext),
                "approvals": approvals,
                "events": events,
                "payout_attempts": payout_attempts,
            }

    async def finance_settings(self) -> FinanceSettings:
        async with self.session.begin():
            return await self._finance_settings(lock=False)

    async def queue_payout(
        self,
        *,
        withdrawal_id: UUID,
        actor_user_id: UUID,
        environment_live_enabled: bool,
        provider_enabled: bool,
        credentials_configured: bool,
    ) -> tuple[WithdrawalRequest, PayoutAttempt]:
        if not (
            environment_live_enabled and provider_enabled and credentials_configured
        ):
            raise DomainError(
                code="PAYOUT_PROVIDER_NOT_READY",
                message="Live payout gates or provider credentials are not ready.",
                status_code=503,
            )
        async with self.session.begin():
            request = await self._withdrawal_for_update(withdrawal_id)
            settings = await self._finance_settings(lock=True)
            if not settings.payout_live_enabled:
                raise DomainError(
                    code="PAYOUT_LIVE_DISABLED",
                    message="Live payouts are disabled in finance settings.",
                    status_code=409,
                )
            if request.status not in {"APPROVED", "QUEUED"}:
                raise self._state_conflict()
            attempt = await self.session.scalar(
                select(PayoutAttempt)
                .where(PayoutAttempt.withdrawal_id == withdrawal_id)
                .with_for_update()
            )
            if attempt is not None:
                if request.status == "QUEUED":
                    return request, attempt
                raise self._state_conflict()
            if request.approved_at is None:
                raise self._state_conflict()
            attempt = PayoutAttempt(
                withdrawal_id=withdrawal_id,
                reference_id=request.provider_reference,
                idempotency_key=f"withdrawal:{withdrawal_id}:payos-payout",
                status="CREATED",
                response_redacted={},
            )
            self.session.add(attempt)
            request.status = "QUEUED"
            self._event(
                withdrawal_id=withdrawal_id,
                event_type="PAYOUT_QUEUED",
                from_status="APPROVED",
                to_status="QUEUED",
                actor_user_id=actor_user_id,
                details={"reference_id": request.provider_reference},
            )
            self._audit(
                actor_user_id=actor_user_id,
                action="wallet.withdrawal.payout_queued",
                resource_type="withdrawal_request",
                resource_id=str(withdrawal_id),
                before={"status": "APPROVED"},
                after={"status": "QUEUED"},
            )
            await self.session.flush()
            return request, attempt

    async def begin_payout_submission(
        self, withdrawal_id: UUID
    ) -> PayoutSubmission | None:
        async with self.session.begin():
            request = await self._withdrawal_for_update(withdrawal_id)
            settings = await self._finance_settings(lock=True)
            attempt = await self.session.scalar(
                select(PayoutAttempt)
                .where(PayoutAttempt.withdrawal_id == withdrawal_id)
                .with_for_update()
            )
            if attempt is None or attempt.status != "CREATED":
                return None
            if request.status != "QUEUED" or request.approved_at is None:
                return None
            if not settings.payout_live_enabled:
                return None
            account = await self.session.scalar(
                select(BankAccount).where(
                    BankAccount.id == request.bank_account_id,
                    BankAccount.user_id == request.user_id,
                    BankAccount.is_active.is_(True),
                    BankAccount.verification_status == "VERIFIED",
                )
            )
            identity = await self.session.scalar(
                select(FinancialIdentityVerification).where(
                    FinancialIdentityVerification.user_id == request.user_id,
                    FinancialIdentityVerification.status == "VERIFIED",
                )
            )
            if account is None or identity is None:
                attempt.status = "UNKNOWN"
                request.status = "RECONCILIATION_REQUIRED"
                attempt.response_redacted = {"reason": "verification_changed"}
                self._event(
                    withdrawal_id=withdrawal_id,
                    event_type="PAYOUT_RECONCILIATION_REQUIRED",
                    from_status="QUEUED",
                    to_status="RECONCILIATION_REQUIRED",
                    actor_user_id=None,
                    details={"reason": "verification_changed"},
                )
                return None
            attempt.status = "SENDING"
            attempt.attempt_count += 1
            attempt.updated_at = self.clock()
            request.status = "PROCESSING"
            self._event(
                withdrawal_id=withdrawal_id,
                event_type="PAYOUT_SUBMISSION_STARTED",
                from_status="QUEUED",
                to_status="PROCESSING",
                actor_user_id=None,
                details={"attempt_id": str(attempt.id)},
            )
            await self.session.flush()
            return {
                "attempt_id": attempt.id,
                "reference_id": attempt.reference_id,
                "idempotency_key": attempt.idempotency_key,
                "amount_minor": request.net_amount_minor,
                "bank_bin": request.bank_bin_snapshot,
                "account_number": self.cipher.decrypt(
                    request.account_number_ciphertext
                ),
            }

    async def record_payout_state(
        self,
        *,
        withdrawal_id: UUID,
        provider_payout_id: str | None,
        state: str,
        error_code: str | None = None,
    ) -> WithdrawalRequest | None:
        normalized = state.upper()
        if normalized in {"SUCCEEDED", "COMPLETED"}:
            status = "SUCCEEDED"
        elif normalized in {"FAILED", "CANCELLED", "REJECTED"}:
            status = "FAILED"
        elif normalized in {"PROCESSING", "PENDING", "CREATED"}:
            status = "PROCESSING"
        else:
            status = "UNKNOWN"
        async with self.session.begin():
            request = await self._withdrawal_for_update(withdrawal_id)
            attempt = await self.session.scalar(
                select(PayoutAttempt)
                .where(PayoutAttempt.withdrawal_id == withdrawal_id)
                .with_for_update()
            )
            if attempt is None:
                raise self._not_found("PAYOUT_ATTEMPT_NOT_FOUND")
            if attempt.status in {"SUCCEEDED", "FAILED"}:
                return request
            if provider_payout_id is not None:
                if (
                    attempt.provider_payout_id is not None
                    and attempt.provider_payout_id != provider_payout_id
                ):
                    status = "UNKNOWN"
                else:
                    attempt.provider_payout_id = provider_payout_id
            attempt.status = status
            attempt.provider_error_code = error_code[:64] if error_code else None
            attempt.response_redacted = {
                "provider_state": normalized[:32],
                "provider_error_code": attempt.provider_error_code,
            }
            attempt.updated_at = self.clock()
            previous_status = request.status
            if status == "SUCCEEDED":
                ledger = FinanceLedger(self.session)
                _, reserved = await ledger.user_accounts(request.user_id)
                payout_account = await ledger.platform_account("PAYOUT_SETTLEMENT")
                await ledger.transfer(
                    source_account_id=reserved.id,
                    target_account_id=payout_account.id,
                    amount_minor=request.net_amount_minor,
                    transaction_type="PAYOUT_SETTLEMENT",
                    idempotency_key=f"withdrawal:{withdrawal_id}:payout-settlement",
                    source_reference=f"withdrawal:{withdrawal_id}:payout-settlement",
                    description="Settle successful approved payout",
                )
                if request.fee_minor:
                    fee_account = await ledger.platform_account(
                        "WITHDRAWAL_FEE_REVENUE"
                    )
                    await ledger.transfer(
                        source_account_id=reserved.id,
                        target_account_id=fee_account.id,
                        amount_minor=request.fee_minor,
                        transaction_type="WITHDRAWAL_FEE",
                        idempotency_key=f"withdrawal:{withdrawal_id}:fee",
                        source_reference=f"withdrawal:{withdrawal_id}:fee",
                        description="Settle successful withdrawal fee",
                    )
                request.status = "SUCCEEDED"
                request.succeeded_at = self.clock()
            elif status == "FAILED":
                await self._release_reservation(request, actor_user_id=None)
                request.status = "FAILED"
            elif status == "PROCESSING":
                request.status = "PROCESSING"
            else:
                request.status = "RECONCILIATION_REQUIRED"
            event = self._event(
                withdrawal_id=withdrawal_id,
                event_type=f"PAYOUT_{status}",
                from_status=previous_status,
                to_status=request.status,
                actor_user_id=None,
                details={
                    "provider_payout_id": provider_payout_id,
                    "provider_state": normalized[:32],
                },
            )
            if status == "SUCCEEDED":
                self._notify(
                    user_id=request.user_id,
                    event_id=event.id,
                    event_type="WITHDRAWAL_SUCCEEDED",
                    title="Khoản rút hoa hồng đã hoàn tất",
                    body="Yêu cầu rút đã được xác nhận hoàn tất.",
                    data={"actionPath": "/wallet", "withdrawalId": str(withdrawal_id)},
                )
            elif status == "FAILED":
                self._notify(
                    user_id=request.user_id,
                    event_id=event.id,
                    event_type="WITHDRAWAL_FAILED",
                    title="Khoản rút hoa hồng chưa hoàn tất",
                    body="Số dư đã được trả lại vào số dư hoa hồng khả dụng.",
                    data={"actionPath": "/wallet", "withdrawalId": str(withdrawal_id)},
                )
            elif status == "UNKNOWN":
                await self._notify_finance_admins(event, request)
            self._audit(
                actor_user_id=None,
                action=f"wallet.withdrawal.payout_{status.lower()}",
                resource_type="withdrawal_request",
                resource_id=str(withdrawal_id),
                before={"status": previous_status},
                after={"status": request.status},
            )
            return request

    async def update_finance_settings(
        self,
        *,
        actor_user_id: UUID,
        withdrawal_enabled: bool,
        minimum_amount_minor: int,
        maximum_amount_minor: int,
        daily_limit_minor: int,
        daily_count_limit: int,
        fee_mode: str,
        fee_value: int,
        two_person_threshold_minor: int | None,
        payout_live_enabled: bool | None = None,
    ) -> FinanceSettings:
        values = (
            minimum_amount_minor,
            maximum_amount_minor,
            daily_limit_minor,
            daily_count_limit,
            fee_value,
        )
        if any(type(value) is not int for value in values):
            raise DomainError(
                code="FINANCE_SETTINGS_INVALID",
                message="Cấu hình tài chính phải dùng số nguyên hợp lệ.",
                status_code=422,
            )
        if (
            minimum_amount_minor <= 0
            or maximum_amount_minor < minimum_amount_minor
            or daily_limit_minor < 0
            or daily_count_limit < 0
            or fee_mode not in {"NONE", "FIXED", "BPS"}
            or fee_value < 0
            or (fee_mode == "BPS" and fee_value > 10_000)
            or (
                two_person_threshold_minor is not None
                and two_person_threshold_minor <= 0
            )
            or (
                withdrawal_enabled
                and (daily_limit_minor <= 0 or daily_count_limit <= 0)
            )
        ):
            raise DomainError(
                code="FINANCE_SETTINGS_INVALID",
                message="Cấu hình rút tiền không hợp lệ hoặc chưa đủ hạn mức.",
                status_code=422,
            )
        async with self.session.begin():
            settings = await self._finance_settings(lock=True)
            before = {
                "withdrawal_enabled": settings.withdrawal_enabled,
                "payout_live_enabled": settings.payout_live_enabled,
                "minimum_amount_minor": settings.minimum_amount_minor,
                "maximum_amount_minor": settings.maximum_amount_minor,
                "daily_limit_minor": settings.daily_limit_minor,
                "daily_count_limit": settings.daily_count_limit,
                "fee_mode": settings.fee_mode,
                "fee_value": settings.fee_value,
                "two_person_threshold_minor": settings.two_person_threshold_minor,
            }
            settings.withdrawal_enabled = withdrawal_enabled
            if payout_live_enabled is not None:
                settings.payout_live_enabled = payout_live_enabled
            settings.minimum_amount_minor = minimum_amount_minor
            settings.maximum_amount_minor = maximum_amount_minor
            settings.daily_limit_minor = daily_limit_minor
            settings.daily_count_limit = daily_count_limit
            settings.fee_mode = fee_mode
            settings.fee_value = fee_value
            settings.two_person_threshold_minor = two_person_threshold_minor
            settings.approval_required = True
            settings.updated_by_user_id = actor_user_id
            settings.updated_at = self.clock()
            self._audit(
                actor_user_id=actor_user_id,
                action="finance.settings.updated",
                resource_type="finance_settings",
                resource_id="1",
                before=before,
                after={
                    "withdrawal_enabled": withdrawal_enabled,
                    "payout_live_enabled": settings.payout_live_enabled,
                    "minimum_amount_minor": minimum_amount_minor,
                    "maximum_amount_minor": maximum_amount_minor,
                    "daily_limit_minor": daily_limit_minor,
                    "daily_count_limit": daily_count_limit,
                    "fee_mode": fee_mode,
                    "fee_value": fee_value,
                    "two_person_threshold_minor": two_person_threshold_minor,
                    "approval_required": True,
                },
            )
            return settings

    async def save_supported_bank(
        self,
        *,
        actor_user_id: UUID,
        bank_bin: str,
        bank_name: str,
        source_reference: str,
        is_enabled: bool,
    ) -> SupportedBank:
        bank_bin = bank_bin.strip()
        bank_name = " ".join(bank_name.split())
        source_reference = source_reference.strip()
        if (
            not bank_bin.isdigit()
            or not 5 <= len(bank_bin) <= 12
            or not 2 <= len(bank_name) <= 128
            or not source_reference.startswith("https://")
            or len(source_reference) > 512
        ):
            raise DomainError(
                code="BANK_CATALOG_ENTRY_INVALID",
                message="Mã BIN, tên ngân hàng hoặc nguồn xác minh không hợp lệ.",
                status_code=422,
            )
        async with self.session.begin():
            row = await self.session.scalar(
                select(SupportedBank)
                .where(SupportedBank.bank_bin == bank_bin)
                .with_for_update()
            )
            before = (
                {"bank_name": row.bank_name, "is_enabled": row.is_enabled}
                if row is not None
                else None
            )
            if row is None:
                row = SupportedBank(bank_bin=bank_bin, bank_name=bank_name)
                self.session.add(row)
            row.bank_name = bank_name
            row.source_reference = source_reference
            row.is_enabled = is_enabled
            row.updated_by_user_id = actor_user_id
            row.updated_at = self.clock()
            self._audit(
                actor_user_id=actor_user_id,
                action="finance.bank_catalog.updated",
                resource_type="supported_bank",
                resource_id=bank_bin,
                before=before,
                after={
                    "bank_name": bank_name,
                    "is_enabled": is_enabled,
                    "source_reference": source_reference,
                },
            )
            await self.session.flush()
            return row

    async def reconciliation_summary(self) -> dict[str, object]:
        async with self.session.begin():
            issue_rows = list(
                (
                    await self.session.execute(
                        select(FinanceJournal.id)
                        .outerjoin(
                            FinanceEntry,
                            FinanceEntry.journal_id == FinanceJournal.id,
                        )
                        .group_by(FinanceJournal.id)
                        .having(
                            (func.count(FinanceEntry.id) != 2)
                            | (
                                func.coalesce(func.sum(FinanceEntry.amount_minor), 0)
                                != 0
                            )
                        )
                    )
                ).all()
            )
            checked_journals = int(
                await self.session.scalar(select(func.count(FinanceJournal.id))) or 0
            )
            actual_reserved_rows = await self.session.execute(
                select(
                    FinanceAccount.owner_user_id,
                    func.coalesce(func.sum(FinanceEntry.amount_minor), 0),
                )
                .outerjoin(FinanceEntry, FinanceEntry.account_id == FinanceAccount.id)
                .where(
                    FinanceAccount.account_type == "COMMISSION_RESERVED",
                    FinanceAccount.owner_user_id.is_not(None),
                )
                .group_by(FinanceAccount.owner_user_id)
            )
            actual_reserved = {
                user_id: int(balance)
                for user_id, balance in actual_reserved_rows.all()
                if user_id is not None
            }
            expected_reserved_rows = await self.session.execute(
                select(
                    WithdrawalRequest.user_id,
                    func.sum(WithdrawalRequest.amount_minor),
                )
                .where(
                    WithdrawalRequest.status.in_(
                        (
                            "PENDING_REVIEW",
                            "APPROVED",
                            "QUEUED",
                            "PROCESSING",
                            "RECONCILIATION_REQUIRED",
                        )
                    )
                )
                .group_by(WithdrawalRequest.user_id)
            )
            expected_reserved = {
                user_id: int(balance)
                for user_id, balance in expected_reserved_rows.all()
            }
            payout_exceptions = list(
                (
                    await self.session.execute(
                        select(
                            PayoutAttempt.withdrawal_id,
                            PayoutAttempt.reference_id,
                            PayoutAttempt.status,
                            PayoutAttempt.provider_payout_id,
                            PayoutAttempt.provider_error_code,
                            PayoutAttempt.updated_at,
                        )
                        .where(
                            PayoutAttempt.status.in_(
                                ("SENDING", "PROCESSING", "UNKNOWN")
                            )
                        )
                        .order_by(PayoutAttempt.updated_at)
                        .limit(100)
                    )
                ).all()
            )
            mismatches = [
                {
                    "user_id": str(user_id),
                    "ledger_reserved_minor": actual_reserved.get(user_id, 0),
                    "withdrawals_reserved_minor": expected_reserved.get(user_id, 0),
                }
                for user_id in sorted(
                    actual_reserved.keys() | expected_reserved.keys(), key=str
                )
                if actual_reserved.get(user_id, 0) != expected_reserved.get(user_id, 0)
            ]
            return {
                "checked_journals": checked_journals,
                "unbalanced_journals": len(issue_rows),
                "unbalanced_journal_ids": [str(row[0]) for row in issue_rows[:100]],
                "checked_reserved_accounts": len(
                    actual_reserved.keys() | expected_reserved.keys()
                ),
                "reserved_balance_mismatches": mismatches[:100],
                "payout_exceptions": [
                    {
                        "withdrawal_id": str(row.withdrawal_id),
                        "reference_id": row.reference_id,
                        "status": row.status,
                        "provider_payout_id": row.provider_payout_id,
                        "provider_error_code": row.provider_error_code,
                        "updated_at": row.updated_at,
                    }
                    for row in payout_exceptions
                ],
            }

    async def _release_reservation(
        self, request: WithdrawalRequest, actor_user_id: UUID | None
    ) -> None:
        ledger = FinanceLedger(self.session)
        available, reserved = await ledger.user_accounts(request.user_id)
        await ledger.transfer(
            source_account_id=reserved.id,
            target_account_id=available.id,
            amount_minor=request.amount_minor,
            transaction_type="WITHDRAWAL_RELEASE",
            idempotency_key=f"withdrawal:{request.id}:release",
            source_reference=f"withdrawal:{request.id}:release",
            description="Release rejected or cancelled withdrawal reservation",
            actor_user_id=actor_user_id,
        )

    async def _finance_settings(self, *, lock: bool) -> FinanceSettings:
        statement = select(FinanceSettings).where(FinanceSettings.id == 1)
        if lock:
            statement = statement.with_for_update()
        row = await self.session.scalar(statement)
        if row is None:
            row = FinanceSettings(id=1)
            self.session.add(row)
            await self.session.flush()
        return row

    async def _withdrawal_for_update(self, withdrawal_id: UUID) -> WithdrawalRequest:
        request = await self.session.scalar(
            select(WithdrawalRequest)
            .where(WithdrawalRequest.id == withdrawal_id)
            .with_for_update()
        )
        if request is None:
            raise self._not_found("WITHDRAWAL_NOT_FOUND")
        return request

    async def _notify_finance_admins(
        self, event: WithdrawalEvent, request: WithdrawalRequest
    ) -> None:
        now = self.clock()
        privileged = (
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.code == "SUPER_ADMIN")
        )
        role_permission = (
            select(UserRole.user_id)
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(Permission.code == "finance.withdrawals.approve")
        )
        user_permission = (
            select(UserPermission.user_id)
            .join(Permission, Permission.id == UserPermission.permission_id)
            .where(
                Permission.code == "finance.withdrawals.approve",
                or_(
                    UserPermission.expires_at.is_(None), UserPermission.expires_at > now
                ),
            )
        )
        recipient_ids = set(
            await self.session.scalars(
                select(User.id).where(
                    User.status == UserStatus.ACTIVE,
                    User.id.in_(privileged.union(role_permission, user_permission)),
                )
            )
        )
        for recipient_id in recipient_ids:
            if recipient_id == request.user_id:
                continue
            self._notify(
                user_id=recipient_id,
                event_id=event.id,
                event_type="WITHDRAWAL_REVIEW_REQUIRED",
                title="Có yêu cầu rút cần kiểm tra",
                body=(
                    f"Yêu cầu {request.provider_reference} cần được xem xét. "
                    f"Số tiền: {request.amount_minor:,} VNĐ."
                ),
                data={
                    "actionPath": "/admin/withdrawals",
                    "withdrawalId": str(request.id),
                },
            )

    def _event(
        self,
        *,
        withdrawal_id: UUID,
        event_type: str,
        from_status: str | None,
        to_status: str | None,
        actor_user_id: UUID | None,
        details: dict[str, object],
    ) -> WithdrawalEvent:
        event = WithdrawalEvent(
            id=uuid4(),
            withdrawal_id=withdrawal_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor_user_id,
            details_json=details,
            created_at=self.clock(),
        )
        self.session.add(event)
        return event

    def _notify(
        self,
        *,
        user_id: UUID,
        event_id: UUID,
        event_type: str,
        title: str,
        body: str,
        data: dict[str, object],
    ) -> None:
        self.session.add(
            Notification(
                user_id=user_id,
                source_event_id=event_id,
                type=event_type,
                title=title,
                body=body,
                data_json=data,
                created_at=self.clock(),
            )
        )

    def _audit(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
    ) -> None:
        AuditService(self.session).record(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before=before,
            after=after,
        )

    @staticmethod
    def _fee(settings: FinanceSettings, amount_minor: int) -> int:
        if settings.fee_mode == "NONE":
            return 0
        if settings.fee_mode == "FIXED":
            return settings.fee_value
        if settings.fee_mode == "BPS":
            return (amount_minor * settings.fee_value) // 10_000
        raise DomainError(
            code="WITHDRAWAL_FEE_INVALID",
            message="Cấu hình phí rút hiện không hợp lệ.",
            status_code=503,
        )

    @staticmethod
    def _not_found(code: str) -> DomainError:
        return DomainError(
            code=code,
            message="Không tìm thấy dữ liệu yêu cầu.",
            status_code=404,
        )

    @staticmethod
    def _state_conflict() -> DomainError:
        return DomainError(
            code="WITHDRAWAL_STATE_CONFLICT",
            message="Yêu cầu rút không còn ở trạng thái xử lý này.",
            status_code=409,
        )

    @staticmethod
    def _unavailable() -> DomainError:
        return DomainError(
            code="WITHDRAWAL_UNAVAILABLE",
            message="Chức năng rút tiền hiện chưa được kích hoạt.",
            status_code=503,
        )
