from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.certificates.errors import CertificateConflictError
from app.modules.dossiers.models import Category


async def require_active_category(session: AsyncSession, name: str) -> Category:
    category = await session.scalar(
        select(Category)
        .where(Category.name == name, Category.is_active.is_(True))
        .limit(1)
    )
    if category is None:
        raise CertificateConflictError(
            "Certificate category must match an active system category."
        )
    return category
