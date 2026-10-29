import pytest

from app.core.errors import DomainError
from app.modules.promotions.checkout_rules import discount_for


def test_integer_percentage_cap_and_no_negative_payable():
    policy = {
        "service_codes": ["MEMBERSHIP"],
        "discount_type": "PERCENT",
        "percentage_bps": 1250,
        "discount_cap_vnd": 30_000,
    }
    assert discount_for(1, policy, original_vnd=333_333, service_code="MEMBERSHIP") == (
        30_000,
        303_333,
    )
    policy["discount_cap_vnd"] = 1_000_000
    assert discount_for(1, policy, original_vnd=99, service_code="MEMBERSHIP") == (
        12,
        87,
    )
    assert discount_for(
        200_000,
        {"service_codes": ["MEMBERSHIP"]},
        original_vnd=100_000,
        service_code="MEMBERSHIP",
    ) == (100_000, 0)


@pytest.mark.parametrize(
    "service,extra,price,code",
    [
        ("WALLET_TOPUP", {}, 500_000, "VOUCHER_SERVICE_INVALID"),
        (
            "MEMBERSHIP",
            {"minimum_order_vnd": 600_000},
            500_000,
            "VOUCHER_MINIMUM_ORDER",
        ),
        ("MEMBERSHIP", {"product_ids": ["other"]}, 500_000, "VOUCHER_PRODUCT_INVALID"),
        (
            "MEMBERSHIP",
            {"maximum_order_vnd": 400_000},
            500_000,
            "VOUCHER_MAXIMUM_ORDER",
        ),
    ],
)
def test_rejects_ineligible_prices_services_and_products(service, extra, price, code):
    with pytest.raises(DomainError) as error:
        discount_for(
            200_000,
            {"service_codes": ["MEMBERSHIP"], **extra},
            original_vnd=price,
            service_code=service,
        )
    assert error.value.code == code


def test_never_sacrifices_better_membership_benefit():
    with pytest.raises(DomainError, match="có lợi hơn"):
        discount_for(
            100_000,
            {"service_codes": ["ADVERTISING"]},
            original_vnd=1_000_000,
            service_code="ADVERTISING",
            membership_discount_vnd=150_000,
        )
