from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.payments.provider import build_payment_gateway
from app.modules.payments.service import PaymentService
from app.workers.celery_app import celery_app


async def get_payment_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PaymentService]:
    provider_name = settings.payment_provider.strip().lower()
    gateway = build_payment_gateway(settings)
    service = PaymentService(
        session=session,
        gateway=gateway,
        provider_name=provider_name,
        amount_minor=settings.payment_amount_minor,
        currency=settings.payment_currency,
        order_ttl_seconds=settings.payment_order_ttl_seconds,
        enqueue_certificate_issue=lambda dossier_id: celery_app.send_task(
            "app.workers.certificate_tasks.issue_certificate",
            args=[str(dossier_id)],
        ),
    )
    try:
        yield service
    finally:
        await service.close()


PaymentServiceDependency = Annotated[
    PaymentService,
    Depends(get_payment_service),
]
