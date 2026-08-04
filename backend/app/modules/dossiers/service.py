import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AccountType
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.canonical import snapshot_sha256
from app.modules.dossiers.errors import (
    ApplicantProfileIncompleteError,
    DossierForbiddenError,
    DossierInvalidStateError,
    DossierNotFoundError,
    DossierValidationError,
)
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierEvidence,
    DossierStatus,
    DossierStatusHistory,
    DossierVersion,
)
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.types import (
    CreateDossier,
    CreateEvidence,
    DossierChanges,
    DossierDetailView,
    DossierPage,
    DossierStatusHistoryView,
    DossierVersionView,
    DossierView,
    EvidenceChanges,
    EvidenceView,
    SubmissionView,
)
from app.modules.dossiers.workflow import DossierWorkflowService
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.repository import MediaAssetRepository
from app.modules.organizations.models import (
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
)
from app.modules.organizations.repository import OrganizationRepository
from app.modules.users.repository import UserProfileRepository

logger = logging.getLogger(__name__)

EDITABLE_STATUSES = frozenset({DossierStatus.DRAFT, DossierStatus.NEEDS_SUPPLEMENT})
DOSSIER_MUTATION_ROLES = frozenset({"APPLICANT", "ORG_MANAGER"})
APPLICANT_ACCOUNT_TYPES = frozenset(
    {AccountType.INDIVIDUAL_APPLICANT, AccountType.ORGANIZATION_APPLICANT}
)


class DossierService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._session = session
        self._repository = DossierRepository(session)
        self._organizations = OrganizationRepository(session)
        self._profiles = UserProfileRepository(session)
        self._media = MediaAssetRepository(session)
        self._workflow = DossierWorkflowService(self._repository)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    async def create_dossier(
        self,
        principal: AuthPrincipal,
        payload: CreateDossier,
    ) -> DossierView:
        self._require_mutation_role(principal)
        title = self._required_title(payload.title)
        async with self._session.begin():
            await self._require_applicant_profile(principal)
            await self._require_category(payload.category_id)
            if payload.organization_id is not None:
                await self._require_organization_manager(
                    principal,
                    payload.organization_id,
                )
            identifier = self._uuid_factory()
            dossier = Dossier(
                id=identifier,
                code=f"TMI-{self._clock().year}-{identifier.hex[:12].upper()}",
                owner_user_id=principal.user_id,
                organization_id=payload.organization_id,
                category_id=payload.category_id,
                title=title,
                slug=self._optional_text(payload.slug),
                summary=self._optional_text(payload.summary),
                visibility=payload.visibility,
            )
            self._repository.add(dossier)
            await self._session.flush()
            view = self._view(dossier, can_edit=True)
        self._audit("dossier.created", principal.user_id, dossier.id)
        return view

    async def list_dossiers(
        self,
        principal: AuthPrincipal,
        *,
        status: DossierStatus | None = None,
        category_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DossierPage:
        async with self._session.begin():
            dossiers, total = await self._repository.list_accessible(
                principal.user_id,
                status=status,
                category_id=category_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            views = tuple(
                [
                    self._view(
                        dossier,
                        can_edit=await self._can_mutate(principal, dossier),
                    )
                    for dossier in dossiers
                ]
            )
        return DossierPage(items=views, total=total)

    async def get_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> DossierView:
        async with self._session.begin():
            dossier = await self._owned_or_scoped(principal, dossier_id)
            return self._view(
                dossier,
                can_edit=await self._can_mutate(principal, dossier),
            )

    async def get_dossier_detail(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> DossierDetailView:
        async with self._session.begin():
            dossier = await self._owned_or_scoped(principal, dossier_id)
            can_edit = await self._can_mutate(principal, dossier)
            version_id: UUID | None = None
            if not can_edit and dossier.current_version_no > 0:
                version = await self._repository.get_version(
                    dossier.id,
                    dossier.current_version_no,
                )
                if version is not None:
                    version_id = version.id
            rows = await self._repository.list_evidences(
                dossier.id,
                version_id=version_id,
            )
            return DossierDetailView(
                dossier=self._view(dossier, can_edit=can_edit),
                evidences=tuple(
                    self._evidence_view(evidence, media) for evidence, media in rows
                ),
            )

    async def update_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        changes: DossierChanges,
    ) -> DossierView:
        self._require_mutation_role(principal)
        async with self._session.begin():
            dossier = await self._owned_or_scoped(
                principal,
                dossier_id,
                for_update=True,
            )
            await self._require_mutation_scope(principal, dossier)
            self._require_editable(dossier)
            if "category_id" in changes.provided_fields:
                if changes.category_id is None:
                    raise DossierValidationError("Category is required.")
                await self._require_category(changes.category_id)
                dossier.category_id = changes.category_id
            if "organization_id" in changes.provided_fields:
                if changes.organization_id is not None:
                    await self._require_organization_manager(
                        principal,
                        changes.organization_id,
                    )
                dossier.organization_id = changes.organization_id
            if "title" in changes.provided_fields:
                dossier.title = self._required_title(changes.title or "")
            if "slug" in changes.provided_fields:
                dossier.slug = self._optional_text(changes.slug)
            if "summary" in changes.provided_fields:
                dossier.summary = self._optional_text(changes.summary)
            if "visibility" in changes.provided_fields:
                if changes.visibility is None:
                    raise DossierValidationError("Visibility is required.")
                dossier.visibility = changes.visibility
            await self._session.flush()
            await self._session.refresh(dossier, attribute_names=["updated_at"])
            view = self._view(dossier, can_edit=True)
        self._audit("dossier.updated", principal.user_id, dossier_id)
        return view

    async def delete_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> None:
        self._require_mutation_role(principal)
        async with self._session.begin():
            dossier = await self._owned_or_scoped(
                principal,
                dossier_id,
                for_update=True,
            )
            await self._require_mutation_scope(principal, dossier)
            if dossier.status is not DossierStatus.DRAFT:
                raise DossierInvalidStateError("Only a draft dossier can be deleted.")
            dossier.deleted_at = self._clock()
        self._audit("dossier.deleted", principal.user_id, dossier_id)

    async def attach_evidence(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        payload: CreateEvidence,
    ) -> EvidenceView:
        self._require_mutation_role(principal)
        async with self._session.begin():
            dossier = await self._owned_or_scoped(
                principal,
                dossier_id,
                for_update=True,
            )
            await self._require_mutation_scope(principal, dossier)
            self._require_editable(dossier)
            media = await self._require_media(principal, payload.media_asset_id)
            evidence = DossierEvidence(
                id=self._uuid_factory(),
                dossier_id=dossier.id,
                media_asset_id=media.id,
                evidence_type=self._evidence_type(payload.evidence_type),
                title=self._required_title(payload.title),
                description=self._optional_text(payload.description),
                issued_at=self._as_utc(payload.issued_at),
                display_order=self._display_order(payload.display_order),
                is_public=payload.is_public,
            )
            self._repository.add_evidence(evidence)
            await self._session.flush()
            view = self._evidence_view(evidence, media)
        self._audit("dossier.evidence.attached", principal.user_id, dossier_id)
        return view

    async def update_evidence(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        evidence_id: UUID,
        changes: EvidenceChanges,
    ) -> EvidenceView:
        self._require_mutation_role(principal)
        async with self._session.begin():
            dossier = await self._owned_or_scoped(
                principal,
                dossier_id,
                for_update=True,
            )
            await self._require_mutation_scope(principal, dossier)
            self._require_editable(dossier)
            evidence = await self._require_editable_evidence(
                dossier_id,
                evidence_id,
            )
            if "evidence_type" in changes.provided_fields:
                evidence.evidence_type = self._evidence_type(
                    changes.evidence_type or ""
                )
            if "title" in changes.provided_fields:
                evidence.title = self._required_title(changes.title or "")
            if "description" in changes.provided_fields:
                evidence.description = self._optional_text(changes.description)
            if "issued_at" in changes.provided_fields:
                evidence.issued_at = self._as_utc(changes.issued_at)
            if "display_order" in changes.provided_fields:
                if changes.display_order is None:
                    raise DossierValidationError("Display order is required.")
                evidence.display_order = self._display_order(changes.display_order)
            if "is_public" in changes.provided_fields:
                if changes.is_public is None:
                    raise DossierValidationError("Public flag is required.")
                evidence.is_public = changes.is_public
            media = await self._require_media(principal, evidence.media_asset_id)
            await self._session.flush()
            view = self._evidence_view(evidence, media)
        self._audit("dossier.evidence.updated", principal.user_id, dossier_id)
        return view

    async def remove_evidence(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        evidence_id: UUID,
    ) -> None:
        self._require_mutation_role(principal)
        async with self._session.begin():
            dossier = await self._owned_or_scoped(
                principal,
                dossier_id,
                for_update=True,
            )
            await self._require_mutation_scope(principal, dossier)
            self._require_editable(dossier)
            evidence = await self._require_editable_evidence(
                dossier_id,
                evidence_id,
            )
            await self._repository.remove_evidence(evidence)
        self._audit("dossier.evidence.removed", principal.user_id, dossier_id)

    async def submit_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
    ) -> SubmissionView:
        return await self._submit(
            principal,
            dossier_id,
            idempotency_key=idempotency_key,
            expected_status=DossierStatus.DRAFT,
            reason_code="APPLICANT_SUBMIT",
        )

    async def resubmit_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
    ) -> SubmissionView:
        return await self._submit(
            principal,
            dossier_id,
            idempotency_key=idempotency_key,
            expected_status=DossierStatus.NEEDS_SUPPLEMENT,
            reason_code="APPLICANT_RESUBMIT",
        )

    async def list_versions(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> tuple[DossierVersionView, ...]:
        async with self._session.begin():
            await self._owned_or_scoped(principal, dossier_id)
            versions = await self._repository.list_versions(dossier_id)
            return tuple(self._version_view(version) for version in versions)

    async def get_timeline(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> tuple[DossierStatusHistoryView, ...]:
        async with self._session.begin():
            await self._owned_or_scoped(principal, dossier_id)
            history = await self._repository.list_status_history(dossier_id)
            return tuple(self._history_view(item) for item in history)

    async def _submit(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
        expected_status: DossierStatus,
        reason_code: str,
    ) -> SubmissionView:
        self._require_mutation_role(principal)
        normalized_key = self._idempotency_key(idempotency_key)
        async with self._session.begin():
            dossier = await self._owned_or_scoped(
                principal,
                dossier_id,
                for_update=True,
            )
            await self._require_mutation_scope(principal, dossier)
            if (
                dossier.status is DossierStatus.SUBMITTED
                and dossier.current_version_no > 0
            ):
                current = await self._repository.get_version(
                    dossier.id,
                    dossier.current_version_no,
                )
                if current is None:
                    raise RuntimeError("Submitted dossier has no current version.")
                result = SubmissionView(
                    dossier=self._view(dossier, can_edit=False),
                    version=self._version_view(current),
                )
            else:
                if dossier.status is not expected_status:
                    raise DossierInvalidStateError(
                        f"Dossier must be {expected_status.value} for this action."
                    )
                category = await self._repository.get_category(dossier.category_id)
                if category is None:
                    raise DossierValidationError("Dossier category is not active.")
                evidence_rows = await self._repository.list_draft_evidences(dossier.id)
                self._validate_submission_evidence(evidence_rows)
                submitted_at = self._clock()
                version_no = dossier.current_version_no + 1
                snapshot = self._snapshot(
                    dossier,
                    category,
                    evidence_rows,
                    version_no=version_no,
                    submitted_by=principal.user_id,
                    submitted_at=submitted_at,
                )
                version = DossierVersion(
                    dossier_id=dossier.id,
                    version_no=version_no,
                    snapshot_json=snapshot,
                    canonical_hash=snapshot_sha256(snapshot),
                    submitted_by=principal.user_id,
                    submitted_at=submitted_at,
                )
                self._repository.add_version(version)
                await self._session.flush()
                for evidence, _ in evidence_rows:
                    evidence.dossier_version_id = version.id
                self._workflow.transition(
                    dossier,
                    target=DossierStatus.SUBMITTED,
                    actor_user_id=principal.user_id,
                    allowed_sources=(expected_status,),
                    reason_code=reason_code,
                )
                dossier.current_version_no = version_no
                dossier.submitted_at = submitted_at
                await self._session.flush()
                await self._session.refresh(
                    dossier,
                    attribute_names=["updated_at"],
                )
                result = SubmissionView(
                    dossier=self._view(dossier, can_edit=False),
                    version=self._version_view(version),
                )
        self._audit_submission(
            reason_code.lower(),
            principal.user_id,
            dossier_id,
            normalized_key,
        )
        return result

    @staticmethod
    def _validate_submission_evidence(
        rows: tuple[tuple[DossierEvidence, MediaAsset], ...],
    ) -> None:
        if not rows:
            raise DossierValidationError(
                "At least one verified evidence file is required."
            )
        for _, media in rows:
            if (
                media.status is not MediaStatus.ACTIVE
                or media.deleted_at is not None
                or media.sha256 is None
                or re.fullmatch(r"[0-9a-f]{64}", media.sha256) is None
            ):
                raise DossierValidationError(
                    "Every evidence file must be active and checksum verified."
                )

    @classmethod
    def _snapshot(
        cls,
        dossier: Dossier,
        category: Category,
        rows: tuple[tuple[DossierEvidence, MediaAsset], ...],
        *,
        version_no: int,
        submitted_by: UUID,
        submitted_at: datetime,
    ) -> dict[str, object]:
        evidences: list[dict[str, object]] = []
        for evidence, media in rows:
            if media.sha256 is None:
                raise RuntimeError("Validated evidence media has no checksum.")
            evidences.append(
                {
                    "id": str(evidence.id),
                    "mediaAssetId": str(media.id),
                    "evidenceType": evidence.evidence_type,
                    "title": evidence.title,
                    "description": evidence.description,
                    "issuedAt": cls._iso_utc(evidence.issued_at),
                    "displayOrder": evidence.display_order,
                    "isPublic": evidence.is_public,
                    "media": {
                        "mimeType": media.mime_type,
                        "bytes": media.bytes,
                        "sha256": media.sha256,
                    },
                }
            )
        return {
            "schemaVersion": 1,
            "dossier": {
                "id": str(dossier.id),
                "code": dossier.code,
                "ownerUserId": str(dossier.owner_user_id),
                "organizationId": (
                    str(dossier.organization_id)
                    if dossier.organization_id is not None
                    else None
                ),
                "category": {
                    "id": str(category.id),
                    "code": category.code,
                    "name": category.name,
                },
                "title": dossier.title,
                "slug": dossier.slug,
                "summary": dossier.summary,
                "visibility": dossier.visibility.value,
            },
            "evidences": evidences,
            "submission": {
                "versionNo": version_no,
                "submittedBy": str(submitted_by),
                "submittedAt": cls._iso_utc(submitted_at),
            },
        }

    @staticmethod
    def _idempotency_key(value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 128:
            raise DossierValidationError("Idempotency key is invalid.")
        return normalized

    async def _require_editable_evidence(
        self,
        dossier_id: UUID,
        evidence_id: UUID,
    ) -> DossierEvidence:
        evidence = await self._repository.get_evidence(
            dossier_id,
            evidence_id,
            for_update=True,
        )
        if evidence is None:
            raise DossierNotFoundError("Dossier evidence was not found.")
        if evidence.dossier_version_id is not None:
            raise DossierInvalidStateError(
                "Evidence in a submitted version is immutable."
            )
        return evidence

    async def _require_media(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> MediaAsset:
        media = await self._media.get_by_id(media_id, for_update=True)
        if media is None:
            raise DossierNotFoundError("Evidence media was not found.")
        if media.owner_user_id != principal.user_id:
            raise DossierForbiddenError()
        if media.status is not MediaStatus.ACTIVE or media.deleted_at is not None:
            raise DossierInvalidStateError("Evidence media is not active.")
        if media.sha256 is None or re.fullmatch(r"[0-9a-f]{64}", media.sha256) is None:
            raise DossierValidationError(
                "Evidence media must have a verified SHA-256 checksum."
            )
        return media

    async def _owned_or_scoped(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        for_update: bool = False,
    ) -> Dossier:
        dossier = await self._repository.get_by_id(
            dossier_id,
            for_update=for_update,
        )
        if dossier is None:
            raise DossierNotFoundError()
        if dossier.owner_user_id == principal.user_id:
            return dossier
        if dossier.organization_id is None:
            raise DossierForbiddenError()
        membership = await self._organizations.get_membership(
            dossier.organization_id,
            principal.user_id,
            for_update=for_update,
        )
        if membership is None or membership.status is not MembershipStatus.ACTIVE:
            raise DossierForbiddenError()
        return dossier

    async def _can_mutate(
        self,
        principal: AuthPrincipal,
        dossier: Dossier,
    ) -> bool:
        if (
            not DOSSIER_MUTATION_ROLES.intersection(principal.roles)
            or dossier.status not in EDITABLE_STATUSES
        ):
            return False
        if dossier.owner_user_id == principal.user_id:
            return True
        if dossier.organization_id is None:
            return False
        membership = await self._organizations.get_membership(
            dossier.organization_id,
            principal.user_id,
        )
        return bool(
            membership is not None
            and membership.status is MembershipStatus.ACTIVE
            and membership.role_code
            in (MembershipRole.OWNER, MembershipRole.ORG_MANAGER)
        )

    async def _require_mutation_scope(
        self,
        principal: AuthPrincipal,
        dossier: Dossier,
    ) -> None:
        if dossier.owner_user_id == principal.user_id:
            return
        if dossier.organization_id is None:
            raise DossierForbiddenError()
        await self._require_organization_manager(
            principal,
            dossier.organization_id,
        )

    async def _require_organization_manager(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
    ) -> None:
        organization = await self._organizations.get_by_id(organization_id)
        membership = await self._organizations.get_membership(
            organization_id,
            principal.user_id,
        )
        if (
            organization is None
            or organization.status is not OrganizationStatus.ACTIVE
            or membership is None
            or membership.status is not MembershipStatus.ACTIVE
            or membership.role_code
            not in (MembershipRole.OWNER, MembershipRole.ORG_MANAGER)
        ):
            raise DossierForbiddenError()

    async def _require_category(self, category_id: UUID) -> None:
        if await self._repository.get_category(category_id) is None:
            raise DossierNotFoundError("Dossier category was not found.")

    @staticmethod
    def _require_mutation_role(principal: AuthPrincipal) -> None:
        if not DOSSIER_MUTATION_ROLES.intersection(principal.roles):
            raise DossierForbiddenError()

    async def _require_applicant_profile(self, principal: AuthPrincipal) -> None:
        if (
            "APPLICANT" not in principal.roles
            or principal.account_type not in APPLICANT_ACCOUNT_TYPES
        ):
            return
        profile = await self._profiles.get_profile(principal.user_id)
        if profile is None or not profile.full_name or not profile.full_name.strip():
            raise ApplicantProfileIncompleteError()

    @staticmethod
    def _require_editable(dossier: Dossier) -> None:
        if dossier.status not in EDITABLE_STATUSES:
            raise DossierInvalidStateError("Dossier is read-only in its current state.")

    @staticmethod
    def _required_title(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise DossierValidationError("Dossier title is required.")
        return normalized

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _evidence_type(value: str) -> str:
        normalized = value.strip().upper()
        if re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", normalized) is None:
            raise DossierValidationError("Evidence type is invalid.")
        return normalized

    @staticmethod
    def _display_order(value: int) -> int:
        if value < 0:
            raise DossierValidationError("Display order cannot be negative.")
        return value

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @classmethod
    def _iso_utc(cls, value: datetime | None) -> str | None:
        normalized = cls._as_utc(value)
        if normalized is None:
            return None
        return normalized.isoformat(timespec="microseconds").replace(
            "+00:00",
            "Z",
        )

    @staticmethod
    def _evidence_view(
        evidence: DossierEvidence,
        media: MediaAsset,
    ) -> EvidenceView:
        if media.sha256 is None:
            raise RuntimeError("Validated evidence media has no checksum.")
        return EvidenceView(
            id=evidence.id,
            dossier_id=evidence.dossier_id,
            dossier_version_id=evidence.dossier_version_id,
            media_asset_id=evidence.media_asset_id,
            evidence_type=evidence.evidence_type,
            title=evidence.title,
            description=evidence.description,
            issued_at=evidence.issued_at,
            display_order=evidence.display_order,
            is_public=evidence.is_public,
            mime_type=media.mime_type,
            bytes=media.bytes,
            sha256=media.sha256,
        )

    @staticmethod
    def _version_view(version: DossierVersion) -> DossierVersionView:
        return DossierVersionView(
            id=version.id,
            dossier_id=version.dossier_id,
            version_no=version.version_no,
            snapshot_json=version.snapshot_json,
            canonical_hash=version.canonical_hash,
            submitted_by=version.submitted_by,
            submitted_at=version.submitted_at,
        )

    @staticmethod
    def _history_view(
        history: DossierStatusHistory,
    ) -> DossierStatusHistoryView:
        return DossierStatusHistoryView(
            id=history.id,
            dossier_id=history.dossier_id,
            from_status=history.from_status,
            to_status=history.to_status,
            actor_user_id=history.actor_user_id,
            reason_code=history.reason_code,
            note=history.note,
            created_at=history.created_at,
        )

    @staticmethod
    def _view(dossier: Dossier, *, can_edit: bool) -> DossierView:
        return DossierView(
            id=dossier.id,
            code=dossier.code,
            owner_user_id=dossier.owner_user_id,
            organization_id=dossier.organization_id,
            category_id=dossier.category_id,
            title=dossier.title,
            slug=dossier.slug,
            summary=dossier.summary,
            status=dossier.status,
            visibility=dossier.visibility,
            current_version_no=dossier.current_version_no,
            submitted_at=dossier.submitted_at,
            created_at=dossier.created_at,
            updated_at=dossier.updated_at,
            can_edit=can_edit,
        )

    @staticmethod
    def _audit(action: str, user_id: UUID, dossier_id: UUID) -> None:
        logger.info(
            "security_audit",
            extra={
                "action": action,
                "user_id": str(user_id),
                "dossier_id": str(dossier_id),
            },
        )

    @staticmethod
    def _audit_submission(
        action: str,
        user_id: UUID,
        dossier_id: UUID,
        idempotency_key: str,
    ) -> None:
        logger.info(
            "security_audit",
            extra={
                "action": f"dossier.{action}",
                "user_id": str(user_id),
                "dossier_id": str(dossier_id),
                "idempotency_key_length": len(idempotency_key),
            },
        )

    async def close(self) -> None:
        await self._session.close()
