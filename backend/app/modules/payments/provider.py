from app.core.config import Settings
from app.modules.payments.errors import PaymentProviderError
from app.modules.payments.gateway import MockPaymentGateway, PaymentGateway
from app.modules.payments.payos_gateway import PayOSGateway


def build_payment_gateway(settings: Settings) -> PaymentGateway:
    provider_name = settings.payment_provider.strip().lower()
    if provider_name == "mock":
        secret = settings.payment_webhook_secret
        return MockPaymentGateway(
            webhook_secret=(secret.get_secret_value() if secret is not None else ""),
            checkout_base_url=settings.payment_checkout_base_url,
            webhook_tolerance_seconds=settings.payment_webhook_tolerance_seconds,
        )
    if provider_name == "payos":
        credentials = (
            settings.payos_client_id,
            settings.payos_api_key,
            settings.payos_checksum_key,
        )
        if any(value is None for value in credentials):
            raise PaymentProviderError("payOS credentials are not configured.")
        client_id, api_key, checksum_key = credentials
        assert client_id is not None
        assert api_key is not None
        assert checksum_key is not None
        return PayOSGateway(
            client_id=client_id.get_secret_value(),
            api_key=api_key.get_secret_value(),
            checksum_key=checksum_key.get_secret_value(),
            return_url=settings.payos_return_url,
            cancel_url=settings.payos_cancel_url,
            base_url=settings.payos_base_url,
            timeout_seconds=settings.payos_timeout_seconds,
        )
    raise PaymentProviderError("Payment provider is not supported.")
