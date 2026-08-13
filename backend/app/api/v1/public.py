from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse

from app.core.schemas import (
    ErrorEnvelope,
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.auth.dependencies import (
    OptionalCsrfPrincipalDependency,
    OptionalCurrentPrincipalDependency,
    SettingsDependency,
)
from app.modules.blockchain.schemas import DocumentVerificationData
from app.modules.blockchain.verification_dependencies import (
    DocumentVerificationServiceDependency,
)
from app.modules.engagement.errors import EngagementUnavailableError
from app.modules.engagement.schemas import (
    ShareActionAcceptedData,
    ShareActionRequest,
)
from app.modules.engagement.visitor import EngagementVisitorContext
from app.modules.public.catalog_query_service import PublicWorkSort
from app.modules.public.dependencies import (
    EngagementServiceDependency,
    PublicCatalogDependency,
    PublicVerificationDependency,
    enforce_public_engagement_rate_limit,
    enforce_public_rate_limit,
    enforce_public_report_rate_limit,
)
from app.modules.public.models import PublicWorkVisibility
from app.modules.public.publication_dependencies import (
    ContentReportServiceDependency,
    PublicCatalogQueryDependency,
    PublicQrCodeServiceDependency,
    PublicSeoServiceDependency,
    PublicWorkDetailDependency,
    TaxonomyServiceDependency,
)
from app.modules.public.report_service import ContentReportInput
from app.modules.public.schemas import (
    ContentReportAcceptedData,
    ContentReportRequest,
    PublicAssetData,
    PublicAssetDetailData,
    PublicCategoryData,
    PublicCertificateVersionData,
    PublicHomeData,
    PublicMapMarkerData,
    PublicSitemapEntryData,
    PublicSitemapManifestData,
    PublicWorkCardData,
    PublicWorkDetailProjectionData,
    TaxonomyTagData,
    VerificationData,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["public"],
    dependencies=[Depends(enforce_public_rate_limit)],
)

PUBLIC_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"description": "Public resource was not found.", "model": ErrorEnvelope},
    422: {"description": "Request validation failed.", "model": ErrorEnvelope},
}
PublicSlugPath = Annotated[str, Path(min_length=1, max_length=180)]
VerificationTokenPath = Annotated[
    str,
    Path(min_length=32, max_length=512, pattern=r"^[A-Za-z0-9_-]+$"),
]
CertificateNumberPath = Annotated[
    str,
    Path(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9-]+$"),
]
TransactionHashPath = Annotated[
    str,
    Path(pattern=r"^0x[0-9a-fA-F]{64}$"),
]
DocumentIndexPath = Annotated[int, Path(ge=0, le=100)]


def _engagement_visitor(request: Request, response: Response) -> str:
    settings = request.app.state.settings
    secret = settings.engagement_visitor_hmac_secret
    if secret is None:
        raise EngagementUnavailableError()
    visitor_context = EngagementVisitorContext(secret=secret.get_secret_value())
    cookie_visitor = request.cookies.get(settings.engagement_visitor_cookie_name)
    if visitor_context.is_valid(cookie_visitor):
        assert cookie_visitor is not None
        return cookie_visitor
    visitor = visitor_context.issue()
    response.set_cookie(
        key=settings.engagement_visitor_cookie_name,
        value=visitor,
        httponly=True,
        secure=settings.app_env != "local",
        samesite="lax",
        max_age=settings.engagement_view_dedupe_ttl_seconds,
        path="/",
    )
    return visitor


@router.post(
    "/public/works/{slug}/engagement/views",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        **PUBLIC_RESPONSES,
        429: {"description": "Engagement rate limited.", "model": ErrorEnvelope},
        503: {"description": "Engagement unavailable.", "model": ErrorEnvelope},
    },
    dependencies=[Depends(enforce_public_engagement_rate_limit)],
)
async def record_public_work_view(
    slug: PublicSlugPath,
    request: Request,
    response: Response,
    service: EngagementServiceDependency,
) -> Response:
    await service.record_view(
        slug=slug,
        visitor=_engagement_visitor(request, response),
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/public/works/{slug}/engagement/shares",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SuccessEnvelope[ShareActionAcceptedData],
    responses={
        **PUBLIC_RESPONSES,
        429: {"description": "Engagement rate limited.", "model": ErrorEnvelope},
        503: {"description": "Engagement unavailable.", "model": ErrorEnvelope},
    },
    dependencies=[Depends(enforce_public_engagement_rate_limit)],
)
async def record_public_work_share(
    slug: PublicSlugPath,
    payload: ShareActionRequest,
    request: Request,
    response: Response,
    service: EngagementServiceDependency,
    principal: OptionalCurrentPrincipalDependency,
) -> SuccessEnvelope[ShareActionAcceptedData]:
    accepted = await service.record_share(
        slug=slug,
        visitor=_engagement_visitor(request, response),
        channel=payload.channel.value,
        principal=principal,
    )
    return SuccessEnvelope(
        data=ShareActionAcceptedData(accepted=accepted),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/public/home", response_model=SuccessEnvelope[PublicHomeData])
async def public_home(
    request: Request,
    service: PublicCatalogDependency,
) -> SuccessEnvelope[PublicHomeData]:
    home = await service.home()
    return SuccessEnvelope(
        data=PublicHomeData(
            certificate_count=home.certificate_count,
            category_count=home.category_count,
            latest_assets=[
                PublicAssetData.model_validate(asset) for asset in home.latest_assets
            ],
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/public/categories",
    response_model=SuccessEnvelope[list[PublicCategoryData]],
)
async def public_categories(
    request: Request,
    service: PublicCatalogDependency,
) -> SuccessEnvelope[list[PublicCategoryData]]:
    categories = await service.categories()
    return SuccessEnvelope(
        data=[PublicCategoryData.model_validate(item) for item in categories],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/public/tags", response_model=SuccessEnvelope[list[TaxonomyTagData]])
async def public_tags(
    request: Request,
    service: TaxonomyServiceDependency,
) -> SuccessEnvelope[list[TaxonomyTagData]]:
    tags = await service.list_tags(public_only=True)
    return SuccessEnvelope(
        data=[TaxonomyTagData.model_validate(tag) for tag in tags],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/public/seo/sitemap",
    response_model=SuccessEnvelope[PublicSitemapManifestData],
)
async def public_sitemap_manifest(
    request: Request,
    service: PublicSeoServiceDependency,
) -> SuccessEnvelope[PublicSitemapManifestData]:
    manifest = await service.manifest()
    return SuccessEnvelope(
        data=PublicSitemapManifestData.model_validate(manifest),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/public/seo/sitemap/{page}",
    response_model=SuccessEnvelope[list[PublicSitemapEntryData]],
)
async def public_sitemap_page(
    page: Annotated[int, Path(ge=1)],
    request: Request,
    service: PublicSeoServiceDependency,
) -> SuccessEnvelope[list[PublicSitemapEntryData]]:
    entries = await service.page(page)
    return SuccessEnvelope(
        data=[PublicSitemapEntryData.model_validate(entry) for entry in entries],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/public/works",
    response_model=PaginatedSuccessEnvelope[list[PublicWorkCardData]],
    responses=PUBLIC_RESPONSES,
)
async def public_works(
    request: Request,
    service: PublicCatalogQueryDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    query: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=160)] = None,
    tag: Annotated[str | None, Query(max_length=160)] = None,
    organization_id: Annotated[UUID | None, Query(alias="organizationId")] = None,
    published_from: Annotated[datetime | None, Query(alias="publishedFrom")] = None,
    published_to: Annotated[datetime | None, Query(alias="publishedTo")] = None,
    sort: PublicWorkSort = PublicWorkSort.NEWEST,
) -> PaginatedSuccessEnvelope[list[PublicWorkCardData]]:
    works, total = await service.list_works(
        query=query,
        category_slug=category,
        tag_slug=tag,
        organization_id=organization_id,
        published_from=published_from,
        published_to=published_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[PublicWorkCardData.model_validate(work) for work in works],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/public/works/featured",
    response_model=SuccessEnvelope[list[PublicWorkCardData]],
    responses=PUBLIC_RESPONSES,
)
async def public_featured_works(
    request: Request,
    service: PublicCatalogQueryDependency,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
) -> SuccessEnvelope[list[PublicWorkCardData]]:
    works = await service.list_featured(limit=limit)
    return SuccessEnvelope(
        data=[PublicWorkCardData.model_validate(work) for work in works],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/public/works/{slug}/qr",
    response_class=Response,
    responses={
        200: {"content": {"image/png": {}}, "description": "Canonical work QR."},
        **PUBLIC_RESPONSES,
    },
)
async def public_work_qr(
    slug: PublicSlugPath,
    service: PublicQrCodeServiceDependency,
) -> Response:
    rendered = await service.render(slug)
    if rendered is None:
        raise HTTPException(status_code=404, detail="Public work was not found.")
    return Response(
        content=rendered.png,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'inline; filename="public-work-qr.png"',
            "Content-Location": rendered.payload,
            "X-Content-Type-Options": "nosniff",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@router.post(
    "/public/works/{work_id}/reports",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[ContentReportAcceptedData],
    dependencies=[Depends(enforce_public_report_rate_limit)],
)
async def create_public_content_report(
    work_id: UUID,
    payload: ContentReportRequest,
    request: Request,
    principal: OptionalCsrfPrincipalDependency,
    service: ContentReportServiceDependency,
) -> SuccessEnvelope[ContentReportAcceptedData]:
    row = await service.submit(
        work_id,
        ContentReportInput(
            reason=payload.reason,
            description=payload.description,
            reporter_email=(
                str(payload.reporter_email) if payload.reporter_email else None
            ),
            captcha_token=(
                payload.captcha_token.get_secret_value()
                if payload.captcha_token
                else None
            ),
        ),
        principal=principal,
        client_ip=request.client.host if request.client else "unknown",
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=ContentReportAcceptedData(id=row.id, status=row.status),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/public/works/{slug}",
    response_model=SuccessEnvelope[PublicWorkDetailProjectionData],
    responses=PUBLIC_RESPONSES,
)
async def public_work_detail(
    slug: PublicSlugPath,
    request: Request,
    response: Response,
    service: PublicWorkDetailDependency,
) -> SuccessEnvelope[PublicWorkDetailProjectionData] | RedirectResponse:
    detail = await service.get(slug)
    if detail is None:
        raise HTTPException(status_code=404, detail="Public work was not found.")
    if detail.redirected:
        return RedirectResponse(
            url=f"/api/v1/public/works/{detail.canonical_slug}",
            status_code=308,
        )
    if detail.visibility is PublicWorkVisibility.UNLISTED:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return SuccessEnvelope(
        data=PublicWorkDetailProjectionData.model_validate(detail),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/public/assets",
    response_model=PaginatedSuccessEnvelope[list[PublicAssetData]],
    responses=PUBLIC_RESPONSES,
)
async def public_assets(
    request: Request,
    service: PublicCatalogDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    query: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=64)] = None,
) -> PaginatedSuccessEnvelope[list[PublicAssetData]]:
    assets, total = await service.assets(
        query=query,
        category=category,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[PublicAssetData.model_validate(item) for item in assets],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/public/assets/{slug}",
    response_model=SuccessEnvelope[PublicAssetDetailData],
    responses=PUBLIC_RESPONSES,
)
async def public_asset(
    slug: PublicSlugPath,
    request: Request,
    service: PublicCatalogDependency,
) -> SuccessEnvelope[PublicAssetDetailData]:
    detail = await service.asset(slug)
    if detail is None:
        raise HTTPException(status_code=404, detail="Public asset was not found.")
    return SuccessEnvelope(
        data=PublicAssetDetailData(
            asset=PublicAssetData.model_validate(detail.asset),
            metadata=detail.metadata,
            network=detail.network,
            contract_address=detail.contract_address,
            confirmations=detail.confirmations,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/public/map",
    response_model=SuccessEnvelope[list[PublicMapMarkerData]],
)
async def public_map(
    request: Request,
    service: PublicCatalogDependency,
    category: Annotated[str | None, Query(max_length=64)] = None,
    min_latitude: Annotated[
        float | None,
        Query(alias="minLat", ge=-90, le=90),
    ] = None,
    max_latitude: Annotated[
        float | None,
        Query(alias="maxLat", ge=-90, le=90),
    ] = None,
    min_longitude: Annotated[
        float | None,
        Query(alias="minLng", ge=-180, le=180),
    ] = None,
    max_longitude: Annotated[
        float | None,
        Query(alias="maxLng", ge=-180, le=180),
    ] = None,
) -> SuccessEnvelope[list[PublicMapMarkerData]]:
    markers = await service.map_markers(
        category=category,
        min_latitude=min_latitude,
        max_latitude=max_latitude,
        min_longitude=min_longitude,
        max_longitude=max_longitude,
    )
    return SuccessEnvelope(
        data=[PublicMapMarkerData.model_validate(item) for item in markers],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


async def _verification_response(
    request: Request,
    result: object,
) -> SuccessEnvelope[VerificationData]:
    return SuccessEnvelope(
        data=VerificationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/public/certificates/{number}/documents/{document_index}/verifications",
    response_model=SuccessEnvelope[DocumentVerificationData],
    responses={
        415: {
            "description": "A binary document body is required.",
            "model": ErrorEnvelope,
        },
        413: {
            "description": "The verification document is too large.",
            "model": ErrorEnvelope,
        },
        **PUBLIC_RESPONSES,
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        }
    },
)
async def verify_public_document_candidate(
    number: CertificateNumberPath,
    document_index: DocumentIndexPath,
    request: Request,
    settings: SettingsDependency,
    certificate_service: PublicVerificationDependency,
    document_service: DocumentVerificationServiceDependency,
) -> SuccessEnvelope[DocumentVerificationData]:
    if request.headers.get("content-type") != "application/octet-stream":
        raise HTTPException(
            status_code=415,
            detail="A binary document body is required.",
        )
    content_length = request.headers.get("content-length")
    if (
        content_length is not None
        and content_length.isdecimal()
        and int(content_length) > settings.document_verification_max_bytes
    ):
        raise HTTPException(
            status_code=413,
            detail="The document exceeds the verification size limit.",
        )
    certificate = await certificate_service.verify_number(number)
    document = (
        certificate.documents[document_index]
        if document_index < len(certificate.documents)
        else None
    )
    result = await document_service.verify_public(
        expected_sha256=document.sha256 if document is not None else None,
        certificate_is_confirmed=certificate.status.value
        in {"VALID", "REVOKED", "EXPIRED"},
        chunks=request.stream(),
    )
    return SuccessEnvelope(
        data=DocumentVerificationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/verify/{token}", response_model=SuccessEnvelope[VerificationData])
async def verify_token(
    token: VerificationTokenPath,
    request: Request,
    service: PublicVerificationDependency,
) -> SuccessEnvelope[VerificationData]:
    return await _verification_response(request, await service.verify_token(token))


@router.get(
    "/verify/certificate/{number}",
    response_model=SuccessEnvelope[VerificationData],
)
async def verify_certificate(
    number: CertificateNumberPath,
    request: Request,
    service: PublicVerificationDependency,
) -> SuccessEnvelope[VerificationData]:
    return await _verification_response(
        request,
        await service.verify_number(number),
    )


@router.get(
    "/verify/certificate/{number}/versions",
    response_model=SuccessEnvelope[list[PublicCertificateVersionData]],
    responses=PUBLIC_RESPONSES,
)
async def public_certificate_versions(
    number: CertificateNumberPath,
    request: Request,
    service: PublicCatalogDependency,
) -> SuccessEnvelope[list[PublicCertificateVersionData]]:
    versions = await service.certificate_versions(number)
    if not versions:
        raise HTTPException(status_code=404, detail="Certificate was not found.")
    return SuccessEnvelope(
        data=[PublicCertificateVersionData.model_validate(item) for item in versions],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/verify/transaction/{tx_hash}",
    response_model=SuccessEnvelope[VerificationData],
)
async def verify_transaction(
    tx_hash: TransactionHashPath,
    request: Request,
    service: PublicVerificationDependency,
) -> SuccessEnvelope[VerificationData]:
    return await _verification_response(
        request,
        await service.verify_transaction(tx_hash),
    )
