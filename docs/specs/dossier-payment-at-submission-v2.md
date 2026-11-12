# Dossier Submission Fees and TEST Isolation

**Status:** Implemented and committed to `main`. Production migrations, payments, and deployment have not been run.

## Implementation decisions

- Admin invites a new TEST applicant through the existing invitation flow. The account has the existing USER role and INDIVIDUAL_APPLICANT type; the server stores is_test_account.
- One authorized Admin can grant a full submission-fee waiver directly. The action records the actor, time, reason, and gross fee. Existing two-person waiver requests remain available for historical records.
- 5,000,000 VND is only the amount prefilled in the policy form. A policy takes effect only after Admin approval and at its explicitly configured start time.
- An unpaid submission stays PAYMENT_PENDING and has no official submission timestamp or review event. Payment, an approved waiver, or TEST skip finalizes the submission.
- TEST applicants can skip the fee or simulate success/failure. TEST transactions cannot debit or top up a real wallet, earn affiliate commission, withdraw funds, issue certificates, publish publicly, or create blockchain anchors. Admin payment reports default to REAL and offer explicit TEST/ALL filters.
- Migrations 0161–0163 preserve existing payment history and refuse unsafe downgrades. Verify migrations only against isolated databases.

## Mục tiêu

Chỉ tiếp nhận hồ sơ vào thẩm định sau khi nghĩa vụ thanh toán đã hoàn tất, được miễn chính thức, hoặc được bỏ qua hợp lệ cho TEST. Dùng một chính sách phí chung theo thời gian; giữ nguyên các obligation và giao dịch lịch sử. Tài khoản kiểm thử hiện có phải đi qua cùng luồng hồ sơ nhưng không tạo tiền thật hay tác động ra ngoài.

## Audit mã nguồn

- `DossierService._submit` trong `backend/app/modules/dossiers/service.py` tạo version, `submitted_at`, lịch sử `SUBMITTED` và outbox event, rồi mới đặt `PAYMENT_PENDING` trong cùng transaction. Hàng đợi review chỉ lấy `SUBMITTED`/`PRECHECK`/`UNDER_REVIEW`, không lấy `PAYMENT_PENDING`; vì vậy review hiện bị chặn đúng, nhưng thời điểm ghi nhận nộp và event vẫn sớm hơn thanh toán.
- `SubmissionFeeService` trong `backend/app/modules/billing/submission_policy.py` lấy chính sách theo `dossier_type_id`, khóa giá theo version, fail closed khi thiếu policy, và tạo order `wallet` tại xác nhận nộp. `PaymentService` trừ ví trong transaction có idempotency; xác nhận ví, webhook và reconcile dùng chung trạng thái thanh toán. Luồng legacy/admin vẫn có thể tạo order theo provider cấu hình cho dossier `APPROVED`; PayOS cũng được dùng ở luồng nạp ví.
- `fee_policies.dossier_type_id` đang NOT NULL; uniqueness và advisory lock đều theo loại hồ sơ. Migration gần nhất là `0160_dynamic_dossier_fees`. Các obligation giữ policy/version và giá đã chốt.
- Miễn phí hiện có hai cơ chế: `FeeWaiver` yêu cầu người khác phê duyệt trước khi áp dụng lúc submit; endpoint thanh toán legacy chỉ miễn cho hồ sơ `APPROVED`. UI quản trị có tab waiver.
- Không tìm thấy role TEST, capability kiểm thử, `is_test` marker hoặc luồng payment giả lập gắn với tài khoản trong backend. `AuthPrincipal` có roles/permissions động, nhưng `SYSTEM_ROLE_CODES` chỉ khai báo `VIEWER`, `USER`, `MODERATOR`, `SUPER_ADMIN`.
- Dossier/payment chưa có cờ cách ly TEST. Báo cáo lịch sử thanh toán tổng hợp mọi order; publication, certificate, blockchain, advertising và withdrawal cũng chưa có quy tắc dựa trên marker TEST.
- `CONTEXT.md` mô tả một phí nộp hồ sơ cho mọi loại; đặc tả và code hiện hành lại cho phép mức phí theo loại. Handoff hiện tại nêu không seed mức phí và không đặt giá hiện hành khi chưa có bằng chứng vận hành.

## Hành vi đề xuất

1. Bản nháp không tạo nghĩa vụ phí. Khi người nộp xác nhận, server kiểm tra hồ sơ, policy chung có hiệu lực, voucher và miễn phí hợp lệ; không dùng giá do client gửi.
2. Với khoản cần trả, hồ sơ ở `PAYMENT_PENDING` nhưng chưa được ghi nhận chính thức, chưa phát event tiếp nhận và chưa vào review queue. Chỉ sau khi ví xác nhận thanh toán mới tạo version chính thức, ghi `submitted_at` và chuyển `SUBMITTED`. Replay, webhook và reconcile phải hội tụ về cùng kết quả.
3. Miễn phí thật có quyết định riêng, người cấp, thời điểm, lý do và mức phí gốc. Bỏ qua TEST và thanh toán mô phỏng có nguồn gốc riêng, không tạo bút toán ví/doanh thu và không dùng chung trạng thái miễn phí thật.
4. Admin tạo tài khoản TEST riêng theo luồng tài khoản hiện có. Tài khoản giữ role `USER` và loại tài khoản người nộp hồ sơ; server gắn marker TEST lúc tạo/nhận lời mời. Hồ sơ và giao dịch kế thừa marker. Client không thể bật/tắt marker. TEST có thể bỏ qua hoặc mô phỏng, nhưng không gọi PayOS thật, trừ ví thật, nhận affiliate thật, kích hoạt quảng cáo thật, rút tiền thật, phát hành chứng nhận thật, ghi blockchain production hoặc xuất hiện công khai.
5. Tất cả thống kê tài chính và luồng nền phải loại TEST bằng marker dữ liệu bền vững, không bằng role hiện tại của chủ hồ sơ. Giữ giao dịch cũ, không tự gán lại lịch sử thành TEST.
6. Policy mới có scope toàn hệ thống. Giữ policy theo loại và snapshot cũ để tra cứu; không đổi giá obligation cũ. Form tạo policy có thể điền sẵn 5.000.000 VNĐ, nhưng policy chỉ có hiệu lực theo ngày giờ và quy trình phê duyệt đã cấu hình.

## Kế hoạch triển khai theo lát cắt

### Cổng 0: Chọn tài khoản TEST riêng

- **Chấp nhận:** Admin tạo applicant riêng với role hiện hữu `USER`; tài khoản được đánh dấu TEST phía server, không có role TEST mới và không có công tắc TEST trong form nộp hồ sơ.
- **Căn cứ:** luồng mời nhân sự hiện chỉ cấp `MODERATOR`; hồ sơ yêu cầu role `USER` cùng loại tài khoản applicant. Vì vậy không dùng tài khoản Admin/Moderator để nộp.
- **Phụ thuộc:** đã được người dùng duyệt trong cuộc hội thoại.

### Lát cắt 1: Policy chung và migration giữ lịch sử

- **Chấp nhận:** policy submission mới dùng scope chung; policy theo loại và obligation cũ vẫn đọc được, không đổi amount/version.
- **Files:** `billing/models.py`, migration `0161_*`, `test_dynamic_fee_migration.py`.
- **Verify:** upgrade/downgrade DB SQLite cô lập; downgrade từ chối nếu có dữ liệu global không thể bảo toàn.
- **Phụ thuộc:** cổng 0 không cần để làm schema.

### Lát cắt 2: Resolver/API policy phí chung

- **Chấp nhận:** quote và submit resolve cùng policy chung theo UTC/effective interval; fee API không tạo policy theo loại cho submission; overlap bị chặn.
- **Files:** `billing/fees.py`, `billing/schemas.py`, `api/v1/billing.py`, `test_billing_fee_policies.py`.
- **Verify:** half-open interval, overlap, authorization, snapshot giá; form có default 5.000.000 nhưng không tự kích hoạt policy.
- **Phụ thuộc:** lát cắt 1.

### Lát cắt 3: Submit chờ phí không được tiếp nhận chính thức

- **Chấp nhận:** xác nhận hồ sơ có khoản phí chỉ tạo pending obligation/order; không ghi version/event/`submitted_at` chính thức trước khi nghĩa vụ hoàn tất.
- **Files:** `dossiers/service.py`, `dossiers/workflow.py`, `billing/submission_policy.py`, `test_dynamic_submission_fee.py`.
- **Verify:** thiếu policy, stale quote, refresh, retry, resubmit và hồ sơ cũ.
- **Phụ thuộc:** lát cắt 2.

### Lát cắt 4: Thanh toán thành công tiếp nhận hồ sơ một lần

- **Chấp nhận:** wallet, webhook và reconcile hoàn tất cùng obligation; row lock/idempotency ngăn debit hoặc version trùng; thiếu ví không tự debit sau top-up.
- **Files:** `payments/service.py`, `payments/repository.py`, `test_payment_service.py`, `test_dossier_submission.py`.
- **Verify:** duplicate key/webhook, late callback, lỗi cập nhật trạng thái và retry sau nạp.
- **Phụ thuộc:** lát cắt 3.

### Lát cắt 5: Miễn phí chính thức có lịch sử riêng

- **Chấp nhận:** admin có capability phù hợp cấp waiver trước submit; bắt buộc lý do, actor, thời gian, phí gốc và audit; giao dịch đã trả không thể waive.
- **Files:** `billing/fees.py`, `api/v1/billing.py`, `test_dynamic_submission_fee.py`, `test_billing_authorization.py`.
- **Verify:** cấp/thiếu quyền, submit sau waive, replay, lịch sử và trường hợp đã paid.
- **Phụ thuộc:** cổng 0 và lát cắt 2.

### Lát cắt 6: Marker TEST và lưu trữ trạng thái

- **Chấp nhận:** tài khoản applicant TEST do Admin provision có marker server-side; dossier/payment/obligation mới kế thừa marker; API không cho client đổi; dữ liệu cũ giữ nguyên.
- **Files:** auth user/invitation model/service/API, `dossiers/models.py`, `payments/models.py`, `billing/models.py`, migration/test (chia lát cắt nếu quá 5 file).
- **Verify:** migration cô lập, tài khoản thường mặc định không TEST, invite TEST chỉ tạo USER applicant, marker chỉ được set bởi Admin.
- **Phụ thuộc:** cổng 0.

### Lát cắt 7: Skip và mô phỏng thanh toán cho TEST

- **Chấp nhận:** skip mặc định không tạo order/debit/revenue; mock có kết quả success/failure riêng; USER thường không thể giả mạo bằng payload; webhook thật không settle mock.
- **Files:** `dossiers/service.py`, `payments/service.py`, `api/v1/dossiers.py`, `api/v1/payments.py`, focused API/payment tests.
- **Verify:** skip, success/failure, hết hạn, hủy, retry, callback trùng, lỗi mất kết nối và test không dùng gateway thật.
- **Phụ thuộc:** cổng 0, lát cắt 4 và 6.

### Lát cắt 8: Cách ly báo cáo tài chính

- **Chấp nhận:** payment summary/history và affiliate revenue không tính TEST; admin có thể lọc TEST riêng.
- **Files:** `payments/repository.py`, `payments/service.py`, `test_payment_service.py`.
- **Verify:** cùng bộ dữ liệu test/real trả tổng tiền thật không đổi khi thêm transaction TEST.
- **Phụ thuộc:** lát cắt 6.

### Lát cắt 9: Chặn public hồ sơ TEST

- **Chấp nhận:** TEST vẫn vào review nội bộ nhưng không xuất hiện trong catalog hoặc xác minh public.
- **Files:** `public/catalog_repository.py`, `public/dossier_verification.py`, `test_public_catalog.py`, `test_public_dossier_verification.py`.
- **Verify:** public list/detail/verification không trả dossier TEST; hồ sơ thật giữ kết quả cũ.
- **Phụ thuộc:** lát cắt 6.

### Lát cắt 10: Chặn certificate và blockchain production

- **Chấp nhận:** TEST không phát hành chứng nhận thật hoặc ghi blockchain production; worker recovery cũng bỏ qua dossier TEST.
- **Files:** `certificates/service.py`, `blockchain/service.py`, `blockchain/proof_registry_service.py`, `workers/certificate_tasks.py`, `test_certificate_recovery_worker.py`.
- **Verify:** endpoint và worker từ chối test dossier; không tạo certificate/anchor job.
- **Phụ thuộc:** lát cắt 6.

### Lát cắt 11: Chặn doanh thu affiliate và quảng cáo thật

- **Chấp nhận:** mô phỏng TEST không settle doanh thu/commission hoặc kích hoạt promotion checkout thật.
- **Files:** `payments/service.py`, `affiliate/service.py`, `promotions/checkout.py`, `test_affiliate_service.py`, `test_promotion_checkout.py`.
- **Verify:** payment TEST không sinh revenue/commission hoặc checkout promotion; thanh toán thật giữ nguyên.
- **Phụ thuộc:** lát cắt 6–8.

### Lát cắt 12: Chặn quảng cáo thật cho dossier TEST

- **Chấp nhận:** TEST không tạo/serve advertising campaign và không tính doanh thu quảng cáo từ dossier TEST.
- **Files:** `advertising/inventory.py`, `advertising/delivery.py`, `advertising/admin.py`, `test_advertising_inventory.py`.
- **Verify:** campaign API/worker/dashboard bỏ qua TEST; campaign thật giữ nguyên.
- **Phụ thuộc:** lát cắt 6.

### Lát cắt 13: Chặn rút tiền thật từ tài khoản TEST

- **Chấp nhận:** principal TEST bị từ chối trước khi tạo payout/withdrawal; USER thường giữ nguyên quyền hiện tại.
- **Files:** `wallet/withdrawal_service.py`, `test_wallet_withdrawal_service.py`.
- **Verify:** không tạo payout attempt hoặc ledger hold khi TEST gọi rút tiền.
- **Phụ thuộc:** cổng 0 và lát cắt 6.

### Lát cắt 14: Applicant checkout mobile-first

- **Chấp nhận:** người thật chỉ thấy phí/voucher/số dư/thanh toán; TEST thấy khu vực nhỏ skip/mock; cùng wizard, cùng API và microcopy tiếng Việt.
- **Files:** `dossier-workspace.tsx`, `dossier-payment-action.tsx`, central API client/types và colocated tests.
- **Verify:** frontend unit tests, keyboard, 320/768/1024/1440px, loading/error/insufficient balance.
- **Phụ thuộc:** API ở lát cắt 3–7.

### Lát cắt 15: Admin workspace

- **Chấp nhận:** policy chung, transactions, hồ sơ miễn phí và filter TEST theo quyền; không có tab/flow TEST riêng.
- **Files:** `fee-management-workspace.tsx`, billing API types/client và `fee-management-workspace.test.tsx`.
- **Verify:** capability visibility, policy lịch sử, waiver audit, filter TEST.
- **Phụ thuộc:** lát cắt 2, 5, 6 và 8.

### Checkpoints

- Sau lát cắt 1–5: focused backend tests và migration test cô lập đạt; rà soát trạng thái, duplicate payment và dữ liệu lịch sử.
- Sau lát cắt 6–10: kiểm tra mọi boundary có thể tạo tiền hoặc public side effect; TEST không thể thành giao dịch thật qua worker/webhook.
- Sau lát cắt 14–15: frontend tests, lint, typecheck, build và browser flow trên mobile/desktop.

## Ranh giới và migration

- Không thêm role. Không gọi PayOS thật, chuyển tiền, chạy migration production, thay đổi payout ngoài điều kiện chặn tài khoản TEST, deploy, push hoặc commit.
- Luồng mới giữ phí hồ sơ qua ví nội bộ; PayOS tiếp tục phục vụ nạp ví. Không tạo payment trực tiếp mới sau phê duyệt; order legacy đang tồn tại vẫn phải đối soát/thanh toán theo snapshot cũ.
- Giữ policy, obligation, payment và hồ sơ lịch sử. Policy cũ không bị xóa; khoản đã trả không tính lại theo giá mới.
- Cột mới mặc định giữ hành vi hiện tại cho hồ sơ cũ. Downgrade không được xóa marker hoặc policy chung đã sử dụng; nếu không thể rollback an toàn thì migration sẽ từ chối downgrade có dữ liệu.
- Các API cũ chỉ đổi khi cần; giữ luồng thanh toán legacy cho dossier lịch sử trong khi áp dụng thứ tự mới cho submission fee.

## Kiểm thử và xác nhận

- Backend seam: API/service xác nhận submit, thanh toán ví, webhook/reconcile, waiver admin, payment summary, public listing và worker side effects.
- Frontend seam: applicant workspace/payment action, fee admin workspace. Các case bắt buộc lấy từ mục IX của yêu cầu người dùng: retry/duplicate, thiếu ví, payment failure, policy đổi, TEST skip/mock, role thường giả mạo TEST, waiver authorization, báo cáo/publication/webhook isolation.
- Mỗi lát cắt: test tập trung trước, sau đó format/lint/typecheck/build liên quan. Kết thúc: `npm run format:check`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run test:e2e` cho luồng browser nếu môi trường hỗ trợ; migration chỉ chạy trên DB cô lập.
- This feature was approved on 2026-11-12. Run verification only against isolated databases; do not apply these migrations in production.

## Giả định lấy từ yêu cầu của bạn

- Admin có quyền hiện hành được miễn trực tiếp hồ sơ chưa nộp; lưu lý do, người cấp, thời điểm, phí gốc và audit. Không tạo yêu cầu để người khác duyệt. Yêu cầu waiver cũ và lịch sử cũ được giữ lại.
- 5.000.000 VNĐ là giá ban đầu điền sẵn trong policy. Admin đặt ngày hiệu lực và phê duyệt khi lập policy; thay đổi code không tự áp dụng giá lên production.
- Không thêm role hoặc hệ thống TEST thứ hai.

## Quyết định TEST

Tạo tài khoản applicant TEST riêng theo luồng Admin đã được người dùng chấp thuận. Dùng role hiện có `USER`, gắn marker server-side và không dùng role Admin/Moderator. Không cần biết role code hoặc tài khoản TEST cũ.

## Điều kiện thành công

- Hồ sơ trả phí chưa vào review và chưa tạo bản nộp chính thức trước khi thanh toán.
- Chỉ có policy phí submission chung; mọi obligation mới giữ nguyên policy/version/gross/waiver/due đã chốt.
- TEST skip/mock không tạo tiền thật hoặc external side effect; dữ liệu TEST bị loại khỏi public và thống kê production.
- Miễn phí thật có quyết định và audit riêng; duplicate/replay không thu tiền hai lần.
- Hồ sơ và giao dịch lịch sử không bị mất hoặc thu phí lại; test/build/migration cô lập đạt theo kế hoạch.
