import asyncio

import pytest
from sqlalchemy import select

from app.core.errors import DomainError
from app.modules.wallet.models import FinanceEntry, FinanceJournal
from app.modules.wallet.service import FinanceLedger
from app.tests.test_payment_service import _service


def test_finance_journal_is_balanced_and_idempotent() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner = await _service()
        try:
            async with sessions() as session, session.begin():
                ledger = FinanceLedger(session)
                available, _reserved = await ledger.user_accounts(owner.user_id)
                expense = await ledger.platform_account("COMMISSION_EXPENSE")
                first = await ledger.transfer(
                    source_account_id=expense.id,
                    target_account_id=available.id,
                    amount_minor=12_500,
                    transaction_type="COMMISSION_CREDIT",
                    idempotency_key="commission:one",
                    source_reference="commission:one",
                    description="Approved commission",
                )
                replay = await ledger.transfer(
                    source_account_id=expense.id,
                    target_account_id=available.id,
                    amount_minor=12_500,
                    transaction_type="COMMISSION_CREDIT",
                    idempotency_key="commission:one",
                    source_reference="commission:one",
                    description="Approved commission",
                )
                assert replay.id == first.id
                assert await ledger.balance(available.id) == 12_500
                assert await ledger.balance(expense.id) == -12_500
                entries = list(
                    await session.scalars(
                        select(FinanceEntry).where(FinanceEntry.journal_id == first.id)
                    )
                )
                assert len(entries) == 2
                assert sum(entry.amount_minor for entry in entries) == 0
                assert (
                    await session.scalar(
                        select(FinanceJournal.id).where(
                            FinanceJournal.idempotency_key == "commission:one"
                        )
                    )
                    == first.id
                )
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_finance_ledger_rejects_spending_more_than_user_liability_balance() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner = await _service()
        try:
            async with sessions() as session, session.begin():
                ledger = FinanceLedger(session)
                available, reserved = await ledger.user_accounts(owner.user_id)
                with pytest.raises(DomainError) as error:
                    await ledger.transfer(
                        source_account_id=available.id,
                        target_account_id=reserved.id,
                        amount_minor=1,
                        transaction_type="WITHDRAWAL_RESERVE",
                        idempotency_key="withdrawal:empty",
                        source_reference="withdrawal:empty",
                        description="Reserve withdrawal",
                    )
                assert error.value.code == "WALLET_INSUFFICIENT_FUNDS"
                assert await ledger.balance(available.id) == 0
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_finance_ledger_rejects_key_reuse_for_a_different_transfer() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner = await _service()
        try:
            async with sessions() as session, session.begin():
                ledger = FinanceLedger(session)
                available, reserved = await ledger.user_accounts(owner.user_id)
                expense = await ledger.platform_account("COMMISSION_EXPENSE")
                await ledger.transfer(
                    source_account_id=expense.id,
                    target_account_id=available.id,
                    amount_minor=12_500,
                    transaction_type="COMMISSION_CREDIT",
                    idempotency_key="shared-key",
                    source_reference="commission:owner",
                    description="Approved commission",
                )
                with pytest.raises(DomainError) as error:
                    await ledger.transfer(
                        source_account_id=available.id,
                        target_account_id=reserved.id,
                        amount_minor=12_500,
                        transaction_type="WITHDRAWAL_RESERVE",
                        idempotency_key="shared-key",
                        source_reference="withdrawal:other",
                        description="Reserve withdrawal",
                    )
                assert error.value.code == "PAYMENT_CONFLICT"
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())
