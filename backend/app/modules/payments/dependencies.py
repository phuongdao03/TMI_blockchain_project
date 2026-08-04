from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.payments.gateway import MockPaymentGateway
from app.modules.payments.service import PaymentService
from app.workers.celery_app import celery_app


async def get_payment_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PaymentService]:
    secret = settings.payment_webhook_secret
    service = PaymentService(
        session=session,
        gateway=MockPaymentGateway(
            webhook_secret=(
                secret.get_secret_value() if secret is not None else ""
            ),
            checkout_base_url=settings.payment_checkout_base_url,
            webhook_tolerance_seconds=settings.payment_webhook_tolerance_seconds,
        ),
        provider_name=settings.payment_provider,
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
