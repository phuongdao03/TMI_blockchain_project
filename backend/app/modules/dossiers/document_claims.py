import re
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dossiers.errors import (
    DossierDuplicateDocumentError,
    DossierValidationError,
)
from app.modules.dossiers.models import (
    DocumentClaimantScope,
    DocumentHashAdjudication,
    DocumentHashAdjudicationAction,
    DocumentHashAnchor,
    DocumentHashClaim,
    Dossier,
    DossierVersion,
)
from app.modules.media.models import MediaAsset

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DocumentHashClaimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_anchor(self, sha256: str) -> DocumentHashAnchor:
        anchor_id = uuid4()
        values = {"id": anchor_id, "sha256": sha256}
        bind = self._session.bind
        dialect = bind.dialect.name if bind is not None else ""
        if dialect == "postgresql":
            postgres_statement = postgres_insert(DocumentHashAnchor).values(values)
            await self._session.execute(
                postgres_statement.on_conflict_do_nothing(
                    index_elements=[DocumentHashAnchor.sha256]
                )
            )
        elif dialect == "sqlite":
            sqlite_statement = sqlite_insert(DocumentHashAnchor).values(values)
            await self._session.execute(
                sqlite_statement.on_conflict_do_nothing(
                    index_elements=[DocumentHashAnchor.sha256]
                )
            )
        else:
            self._session.add(DocumentHashAnchor(**values))
            await self._session.flush()
        anchor = await self._session.scalar(
            select(DocumentHashAnchor)
            .where(DocumentHashAnchor.sha256 == sha256)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if anchor is None:
            raise RuntimeError("Document hash anchor was not persisted.")
        return anchor

    async def get_anchor(
        self,
        sha256: str,
        *,
        for_update: bool = False,
    ) -> DocumentHashAnchor | None:
        statement = select(DocumentHashAnchor).where(
            DocumentHashAnchor.sha256 == sha256
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(
            DocumentHashAnchor | None,
            await self._session.scalar(statement),
        )

    async def get_claim_by_media(
        self,
        media_asset_id: UUID,
    ) -> DocumentHashClaim | None:
        return cast(
            DocumentHashClaim | None,
            await self._session.scalar(
                select(DocumentHashClaim).where(
                    DocumentHashClaim.media_asset_id == media_asset_id
                )
            ),
        )

    async def list_claims(self, anchor_id: UUID) -> tuple[DocumentHashClaim, ...]:
        rows = await self._session.scalars(
            select(DocumentHashClaim)
            .where(DocumentHashClaim.anchor_id == anchor_id)
            .order_by(DocumentHashClaim.claimed_at, DocumentHashClaim.id)
        )
        return tuple(rows.all())

    async def has_adjudication(
        self,
        *,
        anchor_id: UUID,
        media_asset_id: UUID,
        dossier_id: UUID,
        scope_type: DocumentClaimantScope,
        scope_id: UUID,
    ) -> bool:
        return (
            await self._session.scalar(
                select(DocumentHashAdjudication.id).where(
                    DocumentHashAdjudication.anchor_id == anchor_id,
                    DocumentHashAdjudication.media_asset_id == media_asset_id,
                    DocumentHashAdjudication.dossier_id == dossier_id,
                    DocumentHashAdjudication.claimant_scope_type == scope_type,
                    DocumentHashAdjudication.claimant_scope_id == scope_id,
                )
            )
            is not None
        )

    def add_claim(self, claim: DocumentHashClaim) -> None:
        self._session.add(claim)

    async def get_adjudication(
        self,
        *,
        anchor_id: UUID,
        media_asset_id: UUID,
        dossier_id: UUID,
    ) -> DocumentHashAdjudication | None:
        return cast(
            DocumentHashAdjudication | None,
            await self._session.scalar(
                select(DocumentHashAdjudication).where(
                    DocumentHashAdjudication.anchor_id == anchor_id,
                    DocumentHashAdjudication.media_asset_id == media_asset_id,
                    DocumentHashAdjudication.dossier_id == dossier_id,
                )
            ),
        )

    def add_adjudication(self, adjudication: DocumentHashAdjudication) -> None:
        self._session.add(adjudication)


class DocumentHashClaimService:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._repository = DocumentHashClaimRepository(session)

    async def claim_document(
        self,
        *,
        dossier: Dossier,
        version: DossierVersion,
        media: MediaAsset,
    ) -> DocumentHashClaim:
        sha256 = media.sha256
        if sha256 is None or SHA256_PATTERN.fullmatch(sha256) is None:
            raise DossierValidationError(
                "Document does not have a trusted SHA-256 digest."
            )
        existing = await self._repository.get_claim_by_media(media.id)
        if existing is not None:
            return existing

        anchor = await self._repository.get_or_create_anchor(sha256)
        scope_type, scope_id = self._claimant_scope(dossier)
        claims = await self._repository.list_claims(anchor.id)
        has_cross_scope_claim = any(
            claim.claimant_scope_type != scope_type
            or claim.claimant_scope_id != scope_id
            for claim in claims
        )
        if has_cross_scope_claim and not await self._repository.has_adjudication(
            anchor_id=anchor.id,
            media_asset_id=media.id,
            dossier_id=dossier.id,
            scope_type=scope_type,
            scope_id=scope_id,
        ):
            raise DossierDuplicateDocumentError()

        claim = DocumentHashClaim(
            id=uuid4(),
            anchor_id=anchor.id,
            media_asset_id=media.id,
            dossier_id=dossier.id,
            dossier_version_id=version.id,
            claimant_scope_type=scope_type,
            claimant_scope_id=scope_id,
        )
        self._repository.add_claim(claim)
        await self._session.flush()
        return claim

    async def grant_adjudication(
        self,
        *,
        dossier: Dossier,
        media: MediaAsset,
        actor_user_id: UUID,
        reason: str,
    ) -> tuple[DocumentHashAdjudication, bool]:
        sha256 = media.sha256
        if sha256 is None or SHA256_PATTERN.fullmatch(sha256) is None:
            raise DossierValidationError(
                "Document does not have a trusted SHA-256 digest."
            )
        anchor = await self._repository.get_anchor(sha256, for_update=True)
        if anchor is None:
            raise DossierValidationError(
                "Document conflict is not eligible for adjudication."
            )
        existing = await self._repository.get_adjudication(
            anchor_id=anchor.id,
            media_asset_id=media.id,
            dossier_id=dossier.id,
        )
        if existing is not None:
            return existing, False
        scope_type, scope_id = self._claimant_scope(dossier)
        claims = await self._repository.list_claims(anchor.id)
        has_cross_scope_claim = any(
            claim.claimant_scope_type != scope_type
            or claim.claimant_scope_id != scope_id
            for claim in claims
        )
        if not has_cross_scope_claim:
            raise DossierValidationError(
                "Document conflict is not eligible for adjudication."
            )
        adjudication = DocumentHashAdjudication(
            id=uuid4(),
            anchor_id=anchor.id,
            media_asset_id=media.id,
            dossier_id=dossier.id,
            claimant_scope_type=scope_type,
            claimant_scope_id=scope_id,
            action=DocumentHashAdjudicationAction.ALLOW_REANCHOR,
            reason=reason,
            actor_user_id=actor_user_id,
        )
        self._repository.add_adjudication(adjudication)
        await self._session.flush()
        return adjudication, True

    @staticmethod
    def _claimant_scope(dossier: Dossier) -> tuple[DocumentClaimantScope, UUID]:
        if dossier.organization_id is not None:
            return DocumentClaimantScope.ORGANIZATION, dossier.organization_id
        return DocumentClaimantScope.USER, dossier.owner_user_id
