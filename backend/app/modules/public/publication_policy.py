from app.modules.blockchain.models import CertificateStatus
from app.modules.dossiers.models import DossierStatus
from app.modules.media.models import MediaStatus
from app.modules.public.catalog_repository import PublicWorkPublicationContext

PUBLISHABLE_DOSSIER_STATUSES = frozenset(
    {DossierStatus.CERTIFICATE_ISSUED, DossierStatus.PUBLISHED}
)
PUBLICATION_CHECK_CODES = (
    "dossier_not_publishable",
    "active_certificate_required",
    "title_required",
    "slug_required",
    "description_required",
    "category_inactive",
    "thumbnail_not_ready",
)


def publication_checklist(
    context: PublicWorkPublicationContext,
) -> tuple[str, ...]:
    work = context.work
    reasons: list[str] = []
    if context.dossier.status not in PUBLISHABLE_DOSSIER_STATUSES:
        reasons.append("dossier_not_publishable")
    if (
        context.certificate is None
        or context.certificate.status is not CertificateStatus.ACTIVE
        or context.certificate.dossier_id != work.dossier_id
    ):
        reasons.append("active_certificate_required")
    if not work.title.strip():
        reasons.append("title_required")
    if not work.slug.strip():
        reasons.append("slug_required")
    if not work.short_description.strip():
        reasons.append("description_required")
    if not context.category.is_active:
        reasons.append("category_inactive")
    if (
        context.thumbnail is None
        or context.thumbnail.status is not MediaStatus.ACTIVE
        or context.thumbnail.deleted_at is not None
        or not context.thumbnail.mime_type.startswith("image/")
    ):
        reasons.append("thumbnail_not_ready")
    return tuple(reasons)
