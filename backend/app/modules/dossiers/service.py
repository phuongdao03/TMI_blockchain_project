import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.models import AccountType
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.canonical import (
    content_fingerprint,
    normalized_identity_text,
    snapshot_sha256,
)
from app.modules.dossiers.document_claims import DocumentHashClaimService
from app.modules.dossiers.document_rules import (
    DocumentRule,
    DocumentRuleError,
    document_rules_from_schema,
    validate_attachment_against_rules,
    validate_required_document_rules,
)
from app.modules.dossiers.dynamic_schema import (
    DynamicSchemaError,
    public_fields_from_schema,
    validate_and_normalize_form_data,
    validate_schema_definition,
)
from app.modules.dossiers.errors import (
    ApplicantProfileIncompleteError,
    DossierDuplicateContentError,
    DossierForbiddenError,
    DossierInvalidStateError,
    DossierNotFoundError,
    DossierValidationError,
)
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierContentClaim,
    DossierEvidence,
    DossierStatus,
    DossierStatusHistory,
    DossierType,
    DossierTypeVersion,
    DossierVersion,
    EvidenceVisibility,
)
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.types import (
    CreateDossier,
    CreateEvidence,
    DocumentHashAdjudicationView,
    DocumentRuleView,
    DossierChanges,
    DossierDetailView,
    DossierPage,
    DossierStatusHistoryView,
    DossierTypeVersionView,
    DossierTypeView,
    DossierVersionView,
    DossierView,
    EvidenceChanges,
    EvidenceView,
    SubmissionView,
)
from app.modules.dossiers.workflow import DossierWorkflowService
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.provenance import has_current_trusted_provenance
from app.modules.media.repository import MediaAssetRepository
from app.modules.organizations.models import (
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
)
from app.modules.organizations.repository import OrganizationRepository
from app.modules.users.repository import UserProfileRepository

EDITABLE_STATUSES = frozenset({DossierStatus.DRAFT, DossierStatus.NEEDS_SUPPLEMENT})
DOSSIER_MUTATION_ROLES = frozenset({"USER"})
APPLICANT_ACCOUNT_TYPES = frozenset(
    {AccountType.INDIVIDUAL_APPLICANT, AccountType.ORGANIZATION_APPLICANT}
)
PUBLIC_EVIDENCE_SCOPES = frozenset(
    {EvidenceVisibility.PUBLIC, EvidenceVisibility.PUBLIC_PREVIEW}
)
DOSSIER_SUBMITTED_EVENT = "dossier.submitted"


class DossierService:
    DOSSIER_TYPE_MANAGE = PolicyRequirement(
        permission="cms.manage",
        compatible_roles=frozenset({"SUPER_ADMIN"}),
    )
    DOCUMENT_CLAIM_OVERRIDE = PolicyRequirement(
        permission="document_claim.override",
        compatible_roles=frozenset({"SUPER_ADMIN"}),
    )

    def __init__(
        self,
        *,
        session: AsyncSession,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
        enqueue_similarity_detection: Callable[[UUID], None] | None = None,
        payload_cipher: OutboxPayloadCipher | None = None,
    ) -> None:
        self._session = session
        self._repository = DossierRepository(session)
        self._document_claims = DocumentHashClaimService(session=session)
        self._organizations = OrganizationRepository(session)
        self._profiles = UserProfileRepository(session)
        self._media = MediaAssetRepository(session)
        self._workflow = DossierWorkflowService(self._repository)
        self._audit_service = AuditService(session)
        self._outbox = OutboxRepository(session)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4
        self._enqueue_similarity_detection = enqueue_similarity_detection
        self._payload_cipher = payload_cipher

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
            dossier_type: DossierType | None = None
            type_version: DossierTypeVersion | None = None
            form_data: dict[str, Any] = {}
            if payload.dossier_type_version_id is not None:
                type_version = await self._repository.get_dossier_type_version(
                    payload.dossier_type_version_id
                )
                if type_version is None:
                    raise DossierValidationError(
                        "Selected dossier type is unavailable."
                    )
                dossier_type = await self._repository.get_dossier_type(
                    type_version.dossier_type_id
                )
                if (
                    dossier_type is None
                    or not dossier_type.is_active
                    or dossier_type.category_id != payload.category_id
                ):
                    raise DossierValidationError(
                        "Selected dossier type is unavailable."
                    )
                try:
                    form_data = validate_and_normalize_form_data(
                        type_version.schema_json, payload.form_data or {}
                    )
                except DynamicSchemaError as exc:
                    raise DossierValidationError(str(exc)) from exc
            elif payload.form_data:
                raise DossierValidationError(
                    "Form data requires a selected dossier type."
                )
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
                dossier_type_id=(dossier_type.id if dossier_type is not None else None),
                dossier_type_version_id=(
                    type_version.id if type_version is not None else None
                ),
                form_data_json=form_data,
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

    async def list_active_dossier_types(
        self,
        principal: AuthPrincipal,
    ) -> tuple[DossierTypeView, ...]:
        self._require_mutation_role(principal)
        async with self._session.begin():
            rows = await self._repository.list_active_dossier_types()
            return tuple(
                self._dossier_type_view(item, version) for item, version in rows
            )

    async def create_dossier_type(
        self,
        principal: AuthPrincipal,
        *,
        category_id: UUID,
        code: str,
        name: str,
        schema: Mapping[str, Any],
    ) -> DossierTypeView:
        AuthorizationPolicy.require_capability(
            principal, self.DOSSIER_TYPE_MANAGE, DossierForbiddenError
        )
        normalized_code = code.strip().upper()
        normalized_name = name.strip()
        if not normalized_code or not normalized_name:
            raise DossierValidationError("Dossier type code and name are required.")
        try:
            validated_schema = validate_schema_definition(schema)
        except DynamicSchemaError as exc:
            raise DossierValidationError(str(exc)) from exc
        async with self._session.begin():
            await self._require_category(category_id)
            dossier_type = DossierType(
                id=uuid4(),
                category_id=category_id,
                code=normalized_code,
                name=normalized_name,
            )
            version = DossierTypeVersion(
                dossier_type_id=dossier_type.id,
                version_no=1,
                schema_json=validated_schema,
            )
            self._repository.add_type(dossier_type)
            self._repository.add_type_version(version)
            await self._session.flush()
            self._audit("dossier.type.created", principal.user_id, dossier_type.id)
            return self._dossier_type_view(dossier_type, version)

    async def create_dossier_type_version(
        self,
        principal: AuthPrincipal,
        dossier_type_id: UUID,
        *,
        schema: Mapping[str, Any],
    ) -> DossierTypeVersionView:
        AuthorizationPolicy.require_capability(
            principal, self.DOSSIER_TYPE_MANAGE, DossierForbiddenError
        )
        try:
            validated_schema = validate_schema_definition(schema)
        except DynamicSchemaError as exc:
            raise DossierValidationError(str(exc)) from exc
        async with self._session.begin():
            dossier_type = await self._repository.get_dossier_type(dossier_type_id)
            if dossier_type is None:
                raise DossierNotFoundError("Dossier type was not found.")
            version = DossierTypeVersion(
                dossier_type_id=dossier_type.id,
                version_no=await self._repository.next_dossier_type_version_no(
                    dossier_type.id
                ),
                schema_json=validated_schema,
            )
            self._repository.add_type_version(version)
            await self._session.flush()
            self._audit(
                "dossier.type.version.created", principal.user_id, dossier_type.id
            )
            return self._dossier_type_version_view(version)

    async def grant_document_hash_override(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        media_asset_id: UUID,
        reason: str,
    ) -> DocumentHashAdjudicationView:
        AuthorizationPolicy.require_capability(
            principal,
            self.DOCUMENT_CLAIM_OVERRIDE,
            DossierForbiddenError,
        )
        normalized_reason = reason.strip()
        if not 10 <= len(normalized_reason) <= 1000:
            raise DossierValidationError(
                "Override reason must contain between 10 and 1000 characters."
            )
        async with self._session.begin():
            dossier = await self._repository.get_by_id(dossier_id, for_update=True)
            if dossier is None:
                raise DossierNotFoundError()
            if dossier.status not in EDITABLE_STATUSES:
                raise DossierInvalidStateError(
                    "Only an editable dossier can receive a document override."
                )
            evidence_rows = await self._repository.list_draft_evidences(dossier.id)
            media = next(
                (
                    item
                    for evidence, item in evidence_rows
                    if evidence.media_asset_id == media_asset_id
                ),
                None,
            )
            if media is None:
                raise DossierNotFoundError("Dossier document was not found.")
            if not has_current_trusted_provenance(media):
                raise DossierValidationError(
                    "Document does not have current trusted provenance."
                )
            adjudication, created = await self._document_claims.grant_adjudication(
                dossier=dossier,
                media=media,
                actor_user_id=principal.user_id,
                reason=normalized_reason,
            )
            if created:
                self._audit_service.record(
                    actor_user_id=principal.user_id,
                    action="DOCUMENT_HASH_OVERRIDE_GRANTED",
                    resource_type="DOCUMENT_HASH_ADJUDICATION",
                    resource_id=str(adjudication.id),
                    after={
                        "dossierId": str(dossier.id),
                        "mediaAssetId": str(media.id),
                        "action": adjudication.action.value,
                    },
                )
            return DocumentHashAdjudicationView(
                id=adjudication.id,
                dossier_id=adjudication.dossier_id,
                media_asset_id=adjudication.media_asset_id,
                action=adjudication.action,
                created_at=adjudication.created_at,
            )

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
            document_rules = await self._document_rules_for(dossier)
            return DossierDetailView(
                dossier=self._view(dossier, can_edit=can_edit),
                evidences=tuple(
                    self._evidence_view(evidence, media) for evidence, media in rows
                ),
                document_rules=tuple(
                    self._document_rule_view(rule) for rule in document_rules
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
            existing_rows = await self._repository.list_draft_evidences(dossier.id)
            evidence_type, evidence_role, access_scope = await self._attachment_policy(
                dossier,
                evidence_type=payload.evidence_type,
                evidence_role=payload.evidence_role,
                media=media,
                existing=tuple(item for item, _ in existing_rows),
            )
            evidence = DossierEvidence(
                id=self._uuid_factory(),
                dossier_id=dossier.id,
                media_asset_id=media.id,
                evidence_type=evidence_type,
                evidence_role=evidence_role,
                access_scope=access_scope,
                title=self._required_title(payload.title),
                description=self._optional_text(payload.description),
                issued_at=self._as_utc(payload.issued_at),
                display_order=self._display_order(payload.display_order),
                is_public=self._is_public_scope(access_scope),
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
            media = await self._require_media(principal, evidence.media_asset_id)
            rules = await self._document_rules_for(dossier)
            candidate_type = (
                changes.evidence_type
                if "evidence_type" in changes.provided_fields
                else evidence.evidence_type
            )
            candidate_role = (
                changes.evidence_role
                if "evidence_role" in changes.provided_fields
                else evidence.evidence_role
            )
            if rules:
                try:
                    rule = validate_attachment_against_rules(
                        rules,
                        evidence_type=candidate_type or "",
                        evidence_role=candidate_role,
                        mime_type=media.mime_type,
                        byte_size=media.bytes,
                        existing=tuple(
                            item
                            for item, _ in await self._repository.list_draft_evidences(
                                dossier.id
                            )
                            if item.id != evidence.id
                        ),
                    )
                except DocumentRuleError as exc:
                    raise DossierValidationError(str(exc)) from exc
                if rule is None:
                    raise RuntimeError(
                        "Configured dossier rules did not select a rule."
                    )
                evidence.evidence_type = rule.document_type
                evidence.evidence_role = rule.key
                evidence.access_scope = self._evidence_visibility(
                    rule.default_visibility
                )
                evidence.is_public = self._is_public_scope(evidence.access_scope)
            else:
                if "evidence_type" in changes.provided_fields:
                    evidence.evidence_type = self._evidence_type(candidate_type or "")
                if "evidence_role" in changes.provided_fields:
                    evidence.evidence_role = self._evidence_role(candidate_role)
                if {
                    "access_scope",
                    "is_public",
                }.intersection(changes.provided_fields):
                    # A legacy type has no server-owned public document rule;
                    # never let a browser promote its attachment to public.
                    evidence.access_scope = EvidenceVisibility.PRIVATE
                    evidence.is_public = False
            if "evidence_type" in changes.provided_fields:
                evidence.evidence_type = self._evidence_type(evidence.evidence_type)
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
        similarity_version_id: UUID | None = None
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
                dossier_type_schema = await self._dossier_type_schema_for(dossier)
                try:
                    document_rules = (
                        document_rules_from_schema(dossier_type_schema)
                        if dossier_type_schema is not None
                        else ()
                    )
                except DocumentRuleError as exc:
                    raise DossierValidationError(str(exc)) from exc
                self._validate_submission_evidence(
                    evidence_rows,
                    rules=document_rules,
                )
                submitted_at = self._clock()
                version_no = dossier.current_version_no + 1
                snapshot = self._snapshot(
                    dossier,
                    category,
                    evidence_rows,
                    version_no=version_no,
                    submitted_by=principal.user_id,
                    submitted_at=submitted_at,
                    dossier_type_schema=dossier_type_schema,
                )
                identity_fingerprint = self._content_fingerprint(
                    dossier,
                    category,
                    evidence_rows,
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
                claim = await self._repository.claim_content(
                    DossierContentClaim(
                        id=uuid4(),
                        content_fingerprint=identity_fingerprint,
                        dossier_id=dossier.id,
                        dossier_version_id=version.id,
                    )
                )
                if claim.dossier_id != dossier.id:
                    raise DossierDuplicateContentError()
                for _, media in evidence_rows:
                    await self._document_claims.claim_document(
                        dossier=dossier,
                        version=version,
                        media=media,
                    )
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
                similarity_version_id = version.id
                self._audit_submission(
                    reason_code.lower(),
                    principal.user_id,
                    dossier_id,
                    normalized_key,
                )
                self._add_submitted_event(dossier, version)
        if (
            similarity_version_id is not None
            and self._enqueue_similarity_detection is not None
        ):
            self._enqueue_similarity_detection(similarity_version_id)
        return result

    def _add_submitted_event(
        self,
        dossier: Dossier,
        version: DossierVersion,
    ) -> None:
        if self._payload_cipher is None:
            return
        encrypted = self._payload_cipher.encrypt(
            {
                "dossier_id": str(dossier.id),
                "dossier_version_id": str(version.id),
                "recipient_user_id": str(dossier.owner_user_id),
                "version": str(version.version_no),
            },
            event_type=DOSSIER_SUBMITTED_EVENT,
            aggregate_id=dossier.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=DOSSIER_SUBMITTED_EVENT,
                aggregate_type="dossier",
                aggregate_id=dossier.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=self._clock(),
            )
        )

    @staticmethod
    def _content_fingerprint(
        dossier: Dossier,
        category: Category,
        rows: tuple[tuple[DossierEvidence, MediaAsset], ...],
    ) -> str:
        evidence_identity = sorted(
            (
                {
                    "evidenceType": normalized_identity_text(evidence.evidence_type),
                    "title": normalized_identity_text(evidence.title),
                    "mimeType": normalized_identity_text(media.mime_type),
                    "bytes": media.bytes,
                    "sha256": media.sha256,
                }
                for evidence, media in rows
            ),
            key=lambda item: (
                str(item["sha256"]),
                str(item["evidenceType"]),
                str(item["title"]),
            ),
        )
        return content_fingerprint(
            {
                "schemaVersion": 1,
                "categoryCode": normalized_identity_text(category.code),
                "title": normalized_identity_text(dossier.title),
                "summary": normalized_identity_text(dossier.summary),
                "evidence": evidence_identity,
            }
        )

    @staticmethod
    def _validate_submission_evidence(
        rows: tuple[tuple[DossierEvidence, MediaAsset], ...],
        *,
        rules: tuple[DocumentRule, ...],
    ) -> None:
        if not rows:
            raise DossierValidationError(
                "At least one verified evidence file is required."
            )
        for _, media in rows:
            if not has_current_trusted_provenance(media):
                raise DossierValidationError(
                    "Every evidence file must have current trusted provenance."
                )
        try:
            validate_required_document_rules(
                rules,
                evidences=tuple(evidence for evidence, _ in rows),
            )
        except DocumentRuleError as exc:
            raise DossierValidationError(str(exc)) from exc

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
        dossier_type_schema: Mapping[str, Any] | None,
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
                    "evidenceRole": evidence.evidence_role,
                    "accessScope": evidence.access_scope.value,
                    "title": evidence.title,
                    "description": evidence.description,
                    "issuedAt": cls._iso_utc(evidence.issued_at),
                    "displayOrder": evidence.display_order,
                    "isPublic": cls._is_public_scope(evidence.access_scope),
                    "media": {
                        "mimeType": media.mime_type,
                        "bytes": media.bytes,
                        "sha256": media.sha256,
                        "hashAlgorithm": media.hash_algorithm,
                        "hashByteLength": media.hash_byte_length,
                        "inspectionPolicyVersion": media.inspection_policy_version,
                        "storageObjectVersion": media.hash_storage_version,
                        "hashComputedAt": cls._iso_utc(media.hash_computed_at),
                        **(
                            {"perceptualHash": media.perceptual_hash}
                            if media.perceptual_hash is not None
                            else {}
                        ),
                    },
                }
            )
        dossier_snapshot: dict[str, object] = {
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
        }
        if (
            dossier.dossier_type_id is not None
            and dossier.dossier_type_version_id is not None
        ):
            if dossier_type_schema is None:
                raise DossierValidationError("Selected dossier type is unavailable.")
            try:
                public_fields = public_fields_from_schema(
                    dossier_type_schema,
                    dossier.form_data_json,
                )
            except DynamicSchemaError as exc:
                raise DossierValidationError(str(exc)) from exc
            dossier_snapshot["dossierType"] = {
                "id": str(dossier.dossier_type_id),
                "versionId": str(dossier.dossier_type_version_id),
                "formData": dict(dossier.form_data_json),
                # Public consumers are allowed to use this frozen, explicit
                # projection only. Raw formData remains immutable evidence and
                # is never a public serializer source.
                "publicFields": public_fields,
            }
        return {
            "schemaVersion": 1,
            "dossier": dossier_snapshot,
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
        if not has_current_trusted_provenance(media):
            raise DossierValidationError(
                "Evidence media must have current trusted provenance."
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
        can_manage = AuthorizationPolicy.allows_capability(
            principal,
            PolicyRequirement(
                permission="dossier.manage",
                compatible_roles=DOSSIER_MUTATION_ROLES,
                allow_super_admin=False,
            ),
        )
        if not can_manage or dossier.status not in EDITABLE_STATUSES:
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
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="dossier.manage",
                compatible_roles=DOSSIER_MUTATION_ROLES,
                allow_super_admin=False,
            ),
            DossierForbiddenError,
        )

    async def _require_applicant_profile(self, principal: AuthPrincipal) -> None:
        if (
            "USER" not in principal.roles
            or principal.account_type not in APPLICANT_ACCOUNT_TYPES
        ):
            return
        profile = await self._profiles.get_profile(principal.user_id)
        if profile is None or not profile.full_name or not profile.full_name.strip():
            raise ApplicantProfileIncompleteError()

    async def _document_rules_for(
        self,
        dossier: Dossier,
    ) -> tuple[DocumentRule, ...]:
        schema = await self._dossier_type_schema_for(dossier)
        if schema is None:
            return ()
        try:
            return document_rules_from_schema(schema)
        except DocumentRuleError as exc:
            raise DossierValidationError(str(exc)) from exc

    async def _dossier_type_schema_for(
        self,
        dossier: Dossier,
    ) -> Mapping[str, Any] | None:
        if dossier.dossier_type_version_id is None:
            return None
        type_version = await self._repository.get_dossier_type_version(
            dossier.dossier_type_version_id
        )
        if type_version is None:
            raise DossierValidationError("Selected dossier type is unavailable.")
        return type_version.schema_json

    async def _attachment_policy(
        self,
        dossier: Dossier,
        *,
        evidence_type: str,
        evidence_role: str | None,
        media: MediaAsset,
        existing: tuple[DossierEvidence, ...],
    ) -> tuple[str, str, EvidenceVisibility]:
        normalized_type = self._evidence_type(evidence_type)
        normalized_role = self._evidence_role(evidence_role)
        rules = await self._document_rules_for(dossier)
        if not rules:
            # Types without explicit document policy default to private.  This
            # avoids silently publishing a legacy attachment just because a
            # client sent an old `isPublic` field.
            return (
                normalized_type,
                normalized_role or normalized_type,
                EvidenceVisibility.PRIVATE,
            )
        try:
            rule = validate_attachment_against_rules(
                rules,
                evidence_type=normalized_type,
                evidence_role=normalized_role,
                mime_type=media.mime_type,
                byte_size=media.bytes,
                existing=existing,
            )
        except DocumentRuleError as exc:
            raise DossierValidationError(str(exc)) from exc
        if rule is None:
            raise RuntimeError("Configured dossier rules did not select a rule.")
        return (
            rule.document_type,
            rule.key,
            self._evidence_visibility(rule.default_visibility),
        )

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

    @classmethod
    def _evidence_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return cls._evidence_type(value)

    @staticmethod
    def _evidence_visibility(value: str) -> EvidenceVisibility:
        try:
            return EvidenceVisibility(value)
        except ValueError as exc:
            raise DossierValidationError("Evidence visibility is invalid.") from exc

    @staticmethod
    def _is_public_scope(scope: EvidenceVisibility) -> bool:
        return scope in PUBLIC_EVIDENCE_SCOPES

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
            evidence_role=evidence.evidence_role,
            access_scope=evidence.access_scope,
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
            dossier_type_id=dossier.dossier_type_id,
            dossier_type_version_id=dossier.dossier_type_version_id,
            form_data=dict(dossier.form_data_json),
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
    def _dossier_type_version_view(
        version: DossierTypeVersion,
    ) -> DossierTypeVersionView:
        return DossierTypeVersionView(
            id=version.id,
            dossier_type_id=version.dossier_type_id,
            version_no=version.version_no,
            schema=dict(version.schema_json),
        )

    @staticmethod
    def _document_rule_view(rule: DocumentRule) -> DocumentRuleView:
        return DocumentRuleView(
            key=rule.key,
            label=rule.label,
            document_type=rule.document_type,
            required=rule.required,
            allowed_mime_types=tuple(sorted(rule.allowed_mime_types)),
            max_bytes=rule.max_bytes,
            max_count=rule.max_count,
            default_visibility=EvidenceVisibility(rule.default_visibility),
        )

    @classmethod
    def _dossier_type_view(
        cls, dossier_type: DossierType, version: DossierTypeVersion
    ) -> DossierTypeView:
        return DossierTypeView(
            id=dossier_type.id,
            category_id=dossier_type.category_id,
            code=dossier_type.code,
            name=dossier_type.name,
            is_active=dossier_type.is_active,
            current_version=cls._dossier_type_version_view(version),
        )

    def _audit(self, action: str, user_id: UUID, dossier_id: UUID) -> None:
        self._audit_service.record(
            actor_user_id=user_id,
            action=action,
            resource_type="dossier",
            resource_id=str(dossier_id),
        )

    def _audit_submission(
        self,
        action: str,
        user_id: UUID,
        dossier_id: UUID,
        idempotency_key: str,
    ) -> None:
        self._audit_service.record(
            actor_user_id=user_id,
            action=f"dossier.{action}",
            resource_type="dossier",
            resource_id=str(dossier_id),
            after={"idempotency_key_length": len(idempotency_key)},
        )

    async def close(self) -> None:
        await self._session.close()
