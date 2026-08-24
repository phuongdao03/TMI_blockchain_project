"""Read-only public dossier verification projection.

This module deliberately builds an allowlisted view from the frozen dossier
version referenced by the active certificate.  It never returns raw media
locations, submitted form data, ownership information, or reviewer material.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    BlockchainTransaction,
    Certificate,
    CertificateStatus,
    CertificateVersion,
)
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierStatus,
    DossierVersion,
    DossierVisibility,
    EvidenceVisibility,
)

PublicDocumentAccessScope = Literal["PUBLIC", "PUBLIC_PREVIEW"]
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class PublicDossierDocumentView:
    title: str
    evidence_type: str
    access_scope: PublicDocumentAccessScope
    mime_type: str
    bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class PublicDossierFieldView:
    key: str
    label: str
    value: str | int | float | bool | tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PublicDossierCertificateView:
    certificate_number: str
    status: CertificateStatus
    issued_at: datetime
    expires_at: datetime | None
    version: int
    network: str | None
    transaction_hash: str | None
    confirmations: int
    confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class PublicDossierVerificationView:
    code: str
    title: str
    summary: str | None
    category_name: str
    published_at: datetime | None
    certificate: PublicDossierCertificateView | None
    public_fields: tuple[PublicDossierFieldView, ...]
    documents: tuple[PublicDossierDocumentView, ...]


class PublicDossierVerificationService:
    """Projects only an already-published public dossier and safe evidence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, code: str) -> PublicDossierVerificationView | None:
        normalized_code = code.strip().upper()
        dossier_row = (
            await self._session.execute(
                select(Dossier, Category)
                .join(Category, Category.id == Dossier.category_id)
                .where(
                    func.upper(Dossier.code) == normalized_code,
                    Dossier.status == DossierStatus.PUBLISHED,
                    Dossier.visibility == DossierVisibility.PUBLIC,
                    Dossier.deleted_at.is_(None),
                )
            )
        ).one_or_none()
        if dossier_row is None:
            return None
        dossier, category = dossier_row

        certificate_row = (
            await self._session.execute(
                select(Certificate, CertificateVersion, BlockchainTransaction)
                .join(
                    CertificateVersion,
                    (CertificateVersion.certificate_id == Certificate.id)
                    & (
                        CertificateVersion.version_no
                        == Certificate.current_version_no
                    ),
                )
                .outerjoin(
                    BlockchainTransaction,
                    BlockchainTransaction.id
                    == CertificateVersion.blockchain_transaction_id,
                )
                .where(Certificate.dossier_id == dossier.id)
                .order_by(Certificate.issued_at.desc(), Certificate.id.desc())
                .limit(1)
            )
        ).one_or_none()
        if certificate_row is None:
            return PublicDossierVerificationView(
                code=dossier.code,
                title=dossier.title,
                summary=dossier.summary,
                category_name=category.name,
                published_at=dossier.published_at,
                certificate=None,
                public_fields=(),
                documents=(),
            )
        certificate, certificate_version, transaction = certificate_row
        dossier_version = await self._session.get(
            DossierVersion,
            certificate_version.dossier_version_id,
        )
        # A certificate without its frozen dossier version is not a valid public
        # verification source.  Fail closed rather than read mutable dossier data.
        snapshot = (
            dossier_version.snapshot_json if dossier_version is not None else {}
        )
        return PublicDossierVerificationView(
            code=dossier.code,
            title=dossier.title,
            summary=dossier.summary,
            category_name=category.name,
            published_at=dossier.published_at,
            certificate=PublicDossierCertificateView(
                certificate_number=certificate.certificate_number,
                status=certificate.status,
                issued_at=certificate.issued_at,
                expires_at=certificate.expires_at,
                version=certificate_version.version_no,
                network=transaction.network if transaction is not None else None,
                transaction_hash=(
                    transaction.tx_hash if transaction is not None else None
                ),
                confirmations=(
                    transaction.confirmations if transaction is not None else 0
                ),
                confirmed_at=(
                    transaction.confirmed_at if transaction is not None else None
                ),
            ),
            public_fields=self._public_fields(snapshot),
            documents=self._documents(snapshot),
        )

    @staticmethod
    def _documents(
        snapshot: object,
    ) -> tuple[PublicDossierDocumentView, ...]:
        snapshot_map = snapshot if isinstance(snapshot, dict) else {}
        evidences = snapshot_map.get("evidences")
        if not isinstance(evidences, list):
            return ()
        documents: list[PublicDossierDocumentView] = []
        for evidence in evidences:
            if not isinstance(evidence, dict):
                continue
            access_scope = evidence.get("accessScope")
            media = evidence.get("media")
            if not isinstance(media, dict):
                continue
            digest_value = media.get("sha256")
            digest = digest_value.lower() if isinstance(digest_value, str) else ""
            if _SHA256_PATTERN.fullmatch(digest) is None:
                continue
            if access_scope == EvidenceVisibility.PUBLIC.value:
                scope: PublicDocumentAccessScope = "PUBLIC"
            elif access_scope == EvidenceVisibility.PUBLIC_PREVIEW.value:
                scope = "PUBLIC_PREVIEW"
            else:
                continue
            title = evidence.get("title")
            evidence_type = evidence.get("evidenceType")
            mime_type = media.get("mimeType")
            byte_size = media.get("bytes")
            if (
                not isinstance(title, str)
                or not isinstance(evidence_type, str)
                or not isinstance(mime_type, str)
                or isinstance(byte_size, bool)
                or not isinstance(byte_size, int)
                or byte_size < 0
            ):
                continue
            documents.append(
                PublicDossierDocumentView(
                    title=title,
                    evidence_type=evidence_type,
                    access_scope=scope,
                    mime_type=mime_type,
                    bytes=byte_size,
                    sha256=digest,
                )
            )
        return tuple(documents)

    @staticmethod
    def _public_fields(snapshot: object) -> tuple[PublicDossierFieldView, ...]:
        snapshot_map = snapshot if isinstance(snapshot, dict) else {}
        dossier = snapshot_map.get("dossier")
        if not isinstance(dossier, dict):
            return ()
        dossier_type = dossier.get("dossierType")
        if not isinstance(dossier_type, dict):
            return ()
        fields = dossier_type.get("publicFields")
        if not isinstance(fields, list):
            return ()
        projected: list[PublicDossierFieldView] = []
        for field in fields:
            if not isinstance(field, dict):
                continue
            key = field.get("key")
            label = field.get("label")
            value = field.get("value")
            if (
                not isinstance(key, str)
                or not 1 <= len(key) <= 120
                or not isinstance(label, str)
                or not 1 <= len(label.strip()) <= 255
            ):
                continue
            if isinstance(value, str):
                if len(value) > 5_000:
                    continue
                safe_value: str | int | float | bool | tuple[str, ...] = value
            elif isinstance(value, bool):
                safe_value = value
            elif isinstance(value, (int, float)):
                safe_value = value
            elif (
                isinstance(value, list)
                and len(value) <= 100
                and all(isinstance(item, str) and len(item) <= 500 for item in value)
            ):
                safe_value = tuple(value)
            else:
                continue
            projected.append(
                PublicDossierFieldView(
                    key=key,
                    label=label.strip(),
                    value=safe_value,
                )
            )
        return tuple(projected)
