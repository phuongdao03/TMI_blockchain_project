from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
)


class BlockchainTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, transaction: BlockchainTransaction) -> None:
        self._session.add(transaction)

    async def get(
        self,
        transaction_id: UUID,
        *,
        for_update: bool = False,
    ) -> BlockchainTransaction | None:
        statement = select(BlockchainTransaction).where(
            BlockchainTransaction.id == transaction_id
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(
            BlockchainTransaction | None,
            await self._session.scalar(statement),
        )

    async def find_idempotent(
        self,
        *,
        dossier_version_id: UUID,
        network: str,
        contract_address: str,
        method: str,
        payload_hash: str,
    ) -> BlockchainTransaction | None:
        return cast(
            BlockchainTransaction | None,
            await self._session.scalar(
                select(BlockchainTransaction).where(
                    BlockchainTransaction.dossier_version_id
                    == dossier_version_id,
                    BlockchainTransaction.network == network,
                    BlockchainTransaction.contract_address
                    == contract_address,
                    BlockchainTransaction.method == method,
                    BlockchainTransaction.payload_hash == payload_hash,
                )
            ),
        )

    async def list(
        self,
        *,
        status: BlockchainTransactionStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[BlockchainTransaction, ...], int]:
        condition = (
            BlockchainTransaction.status == status if status is not None else None
        )
        query = select(BlockchainTransaction)
        count_query = select(func.count()).select_from(BlockchainTransaction)
        if condition is not None:
            query = query.where(condition)
            count_query = count_query.where(condition)
        rows = await self._session.scalars(
            query.order_by(BlockchainTransaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return tuple(rows.all()), int(await self._session.scalar(count_query) or 0)

    async def list_broadcast(self, *, limit: int) -> tuple[BlockchainTransaction, ...]:
        rows = await self._session.scalars(
            select(BlockchainTransaction)
            .where(
                BlockchainTransaction.status
                == BlockchainTransactionStatus.BROADCAST
            )
            .order_by(BlockchainTransaction.broadcast_at)
            .limit(limit)
        )
        return tuple(rows.all())
