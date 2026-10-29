"""Pure, integer-only promotion arithmetic shared by quotes and reservations."""

from collections.abc import Mapping
from typing import NoReturn

from app.core.errors import DomainError

SERVICES = {"DOSSIER_SUBMISSION", "DOSSIER_APPROVAL", "MEMBERSHIP", "ADVERTISING"}


def reject(code: str, message: str) -> NoReturn:
    raise DomainError(code=code, message=message, status_code=409)


def discount_for(
    nominal_vnd: int,
    policy: Mapping[str, object],
    *,
    original_vnd: int,
    service_code: str,
    product_id: str | None = None,
    membership_discount_vnd: int = 0,
) -> tuple[int, int]:
    if type(original_vnd) is not int or original_vnd < 0:
        reject("VOUCHER_PRICE_INVALID", "Giá dịch vụ không hợp lệ.")
    services = policy.get("service_codes", ["DOSSIER_SUBMISSION"])
    if (
        not isinstance(services, list)
        or service_code not in SERVICES
        or service_code not in services
    ):
        reject("VOUCHER_SERVICE_INVALID", "Voucher không áp dụng cho dịch vụ này.")
    products = policy.get("product_ids", [])
    if not isinstance(products, list):
        reject("VOUCHER_POLICY_INVALID", "Danh sách gói không hợp lệ.")
    if products and product_id not in products:
        reject("VOUCHER_PRODUCT_INVALID", "Voucher không áp dụng cho gói này.")
    minimum = policy.get("minimum_order_vnd", 0)
    maximum = policy.get("maximum_order_vnd")
    if isinstance(minimum, int) and original_vnd < minimum:
        reject("VOUCHER_MINIMUM_ORDER", "Đơn hàng chưa đạt giá trị tối thiểu.")
    if isinstance(maximum, int) and original_vnd > maximum:
        reject("VOUCHER_MAXIMUM_ORDER", "Đơn hàng vượt giá trị áp dụng voucher.")
    discount = nominal_vnd
    if policy.get("discount_type") == "PERCENT":
        rate = policy.get("percentage_bps", 0)
        if type(rate) is not int or not 0 < rate <= 10_000:
            reject("VOUCHER_POLICY_INVALID", "Tỷ lệ giảm không hợp lệ.")
        discount = original_vnd * rate // 10_000
    cap = policy.get("discount_cap_vnd")
    if isinstance(cap, int):
        discount = min(discount, cap)
    discount = min(discount, original_vnd)
    if membership_discount_vnd:
        if policy.get("stacking_policy", "NONE") == "MEMBERSHIP_FIRST":
            reject(
                "VOUCHER_MEMBERSHIP_PRIORITY", "Đơn hàng ưu tiên quyền lợi hội viên."
            )
        if discount <= membership_discount_vnd:
            reject("VOUCHER_MEMBERSHIP_BETTER", "Ưu đãi hội viên hiện tại có lợi hơn.")
    if discount <= 0:
        reject("VOUCHER_NO_DISCOUNT", "Voucher không tạo ra khoản giảm hợp lệ.")
    return discount, original_vnd - discount
