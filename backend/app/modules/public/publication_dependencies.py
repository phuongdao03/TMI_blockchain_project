from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.engagement.qr_service import QrShareLinkService
from app.modules.engagement.redis import RedisQrScanDeduplicator
from app.modules.engagement.visitor import EngagementVisitorContext
from app.modules.public.catalog_cache import RedisPublicCatalogCache
from app.modules.public.catalog_query_service import PublicCatalogQueryService
from app.modules.public.detail_service import PublicWorkDetailService
from app.modules.public.editor_service import PublicWorkEditorService
from app.modules.public.media_dispatcher import CeleryPublicMediaDispatcher
from app.modules.public.media_service import PublicMediaService
from app.modules.public.publication_service import PublicationService
from app.modules.public.report_service import ContentReportService
from app.modules.public.seo_cache import RedisPublicSitemapCache
from app.modules.public.seo_service import PublicSeoService
from app.modules.public.share_service import PublicQrCodeService
from app.modules.public.taxonomy_service import TaxonomyService
from app.modules.users.security import SensitiveFieldCipher


async def get_publication_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicationService]:
    secret = settings.auth_outbox_encryption_key
    yield PublicationService(
        session=session,
        audit=AuditService(session),
        payload_cipher=OutboxPayloadCipher.from_base64(
            encoded_key=secret.get_secret_value() if secret is not None else "",
            key_id=settings.auth_outbox_key_id,
        ),
    )


PublicationServiceDependency = Annotated[
    PublicationService,
    Depends(get_publication_service),
]


async def get_taxonomy_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[TaxonomyService]:
    secret = settings.auth_outbox_encryption_key
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield TaxonomyService(
            session=session,
            audit=AuditService(session),
            payload_cipher=OutboxPayloadCipher.from_base64(
                encoded_key=secret.get_secret_value() if secret is not None else "",
                key_id=settings.auth_outbox_key_id,
            ),
            cache=RedisPublicCatalogCache(
                redis_client,
                ttl_seconds=settings.public_catalog_cache_ttl_seconds,
            ),
        )
    finally:
        await redis_client.aclose()


TaxonomyServiceDependency = Annotated[TaxonomyService, Depends(get_taxonomy_service)]


async def get_public_media_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicMediaService]:
    secret = settings.auth_outbox_encryption_key
    yield PublicMediaService(
        session=session,
        audit=AuditService(session),
        dispatcher=CeleryPublicMediaDispatcher(),
        payload_cipher=OutboxPayloadCipher.from_base64(
            encoded_key=secret.get_secret_value() if secret is not None else "",
            key_id=settings.auth_outbox_key_id,
        ),
    )


PublicMediaServiceDependency = Annotated[
    PublicMediaService,
    Depends(get_public_media_service),
]


async def get_public_work_editor_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicWorkEditorService]:
    secret = settings.auth_outbox_encryption_key
    yield PublicWorkEditorService(
        session=session,
        audit=AuditService(session),
        payload_cipher=OutboxPayloadCipher.from_base64(
            encoded_key=secret.get_secret_value() if secret is not None else "",
            key_id=settings.auth_outbox_key_id,
        ),
    )


PublicWorkEditorServiceDependency = Annotated[
    PublicWorkEditorService,
    Depends(get_public_work_editor_service),
]


async def get_public_catalog_query_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicCatalogQueryService]:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield PublicCatalogQueryService(
            session,
            cache=RedisPublicCatalogCache(
                redis_client,
                ttl_seconds=settings.public_catalog_cache_ttl_seconds,
            ),
        )
    finally:
        await redis_client.aclose()


PublicCatalogQueryDependency = Annotated[
    PublicCatalogQueryService,
    Depends(get_public_catalog_query_service),
]


async def get_public_work_detail_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicWorkDetailService]:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield PublicWorkDetailService(
            session,
            cache=RedisPublicCatalogCache(
                redis_client,
                ttl_seconds=settings.public_catalog_cache_ttl_seconds,
            ),
        )
    finally:
        await redis_client.aclose()


PublicWorkDetailDependency = Annotated[
    PublicWorkDetailService,
    Depends(get_public_work_detail_service),
]


async def get_public_seo_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicSeoService]:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield PublicSeoService(
            session,
            cache=RedisPublicSitemapCache(
                redis_client,
                ttl_seconds=settings.public_sitemap_cache_ttl_seconds,
            ),
            page_size=settings.public_sitemap_page_size,
        )
    finally:
        await redis_client.aclose()


PublicSeoServiceDependency = Annotated[
    PublicSeoService,
    Depends(get_public_seo_service),
]


async def get_public_qr_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicQrCodeService]:
    secret = settings.engagement_visitor_hmac_secret
    if secret is None:
        from app.modules.engagement.errors import EngagementUnavailableError

        raise EngagementUnavailableError()
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield PublicQrCodeService(
            session,
            public_base_url=settings.app_base_url,
            allow_local_http=settings.app_env == "local",
            share_links=QrShareLinkService(
                session,
                scans=RedisQrScanDeduplicator(
                    redis_client,
                    visitor_context=EngagementVisitorContext(
                        secret=secret.get_secret_value(),
                    ),
                    ttl_seconds=settings.engagement_view_dedupe_ttl_seconds,
                ),
                token_secret=secret.get_secret_value(),
            ),
        )
    finally:
        await redis_client.aclose()


PublicQrCodeServiceDependency = Annotated[
    PublicQrCodeService,
    Depends(get_public_qr_service),
]


async def get_content_report_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[ContentReportService]:
    pii_secret = settings.pii_encryption_key
    outbox_secret = settings.auth_outbox_encryption_key
    yield ContentReportService(
        session,
        audit=AuditService(session),
        pii_cipher=SensitiveFieldCipher.from_base64(
            pii_secret.get_secret_value() if pii_secret is not None else ""
        ),
        outbox_cipher=OutboxPayloadCipher.from_base64(
            encoded_key=(
                outbox_secret.get_secret_value() if outbox_secret is not None else ""
            ),
            key_id=settings.auth_outbox_key_id,
        ),
    )


ContentReportServiceDependency = Annotated[
    ContentReportService,
    Depends(get_content_report_service),
]
