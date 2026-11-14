# Structured dossier and review upgrade — 2026-10-30

This handoff tracks the supplied dossier/evidence/assessment master prompt.
`MASTER_PROMPT_ACCEPTANCE_2026.md` tracks the earlier UX brief and is not a full
acceptance declaration for this work. No production database, payment, chain
transaction, merge, push or deployment was performed.

## Implemented behavior and code evidence

| Area                   | Implementation                                                                                                                                                | Local acceptance                                                                                                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Catalog and narrative  | Migration 0151 copies the latest schemas for the 12 verified built-in codes, adding four distinct Vietnamese narrative fields per type with guidance/examples | Existing fields, requirements, custom types and historical schema bytes preserved; optional new fields avoid inventing mandatory business rules                                      |
| Applicant claims       | `dossiers/service.py:replace_claims`, `_validated_claims`; `dossier-claims-editor.tsx`                                                                        | Claims link a statement, pinned criterion and current dossier evidence; server validates scope and revision; unsaved changes are protected                                           |
| Submission version     | Existing `DossierVersion`, `DossierService._snapshot`                                                                                                         | Private claims join frozen form/rubric/evidence hashes; existing snapshots and explicit public projections are unchanged                                                             |
| Content verification   | `reviews/service.py:_validated_evidence_assessments`, `_attribute_verifications`; `review-evidence-assessments.tsx`                                           | Relevance remains distinct from content verification; method/source/scope/limitations and server attribution; incomplete drafts can be saved                                         |
| Criterion safety       | `_validate_verdict_decision`, `validate_approval_review`; `verdict-review-form.tsx`                                                                           | No default success; insufficient basis requires supplementation without manufacturing a citation; unsuitable/contradictory evidence cannot support approval under the new policy     |
| Independent approval   | `CouncilService._validate_policy_decision`, `CouncilRepository.submitted_review_reports`                                                                      | Current owner, submitted expert reviewer or conflicted actor cannot decide under the new frozen policy; configured minimum defaults to one; submitted reports are revalidated        |
| Structured supplements | `supplements/{models,repository,service,schemas}.py`, shared panel                                                                                            | Version/criterion/optional claim, reason, concrete request, priority and explicit optional deadline; append-only sequenced replies/resolutions/reopening, optimistic revision checks |
| Workflow guards        | Existing dossier resubmit and council decision paths                                                                                                          | Open requests block resubmission before snapshots/financial changes; unresolved requests block approval; dossier row locks serialize mutations                                       |
| Preparation recovery   | Authenticated pinned-version endpoint and create-form recovery                                                                                                | A catalog upgrade does not silently replace a restored preparation's schema or fields; loading/error/retry/inactive-template cases covered                                           |
| Regression boundaries  | Existing payment, wallet, fee, certificate and precheck paths                                                                                                 | Retain existing fees, policy snapshots, encrypted notification event, certificate and publication rules                                                                              |

Backend module paths are relative to `backend/app/modules/`; frontend components
are under `frontend/src/components/`. Detailed contracts and first audit are in
`docs/specs/structured-dossier-review-2026.md`, `dossier-applicant-claims.md`,
`council-evidence-policy-guards.md` and `structured-supplements.md`.

Verified built-in codes: CULTURAL_WORK, TRADEMARK, ARTWORK, DOCUMENT,
CERTIFICATE, PERSON, ORGANIZATION, PRODUCT, CULTURAL_HERITAGE, INITIATIVE,
INTELLECTUAL_ASSET, OTHER. No code or name is invented or renamed.

## Data and compatibility

`Dossier.claims_json` and `claims_revision` extend the existing dossier, rather
than adding a second application workflow. Claims contain stable IDs, criterion
keys, statements and evidence media IDs. Each submitted snapshot carries its
private claims. Existing versions remain the source for later expert decisions.

Verification extends the existing review JSON. Files are never verified by
upload, checksum, hash anchoring, membership or payment. Client attribution is
ignored; the authenticated reviewer and server clock are authoritative. Legacy
relevance- only saves cannot silently discard an existing verification, even
when a file or the entire assessment map is omitted. Changes generate existing
sealed audit events containing identifiers/outcomes, without free-text evidence
contents.

`evidencePolicyVersion: "2026.1"` freezes stricter criterion and independence
guards for new templates. Criteria may explicitly enable `allowNotApplicable` or
`verificationRequired`; no universal external certification is introduced.
`minimumIndependentReviews` is an optional integer from 1 to 10, default 1.
Publishing these new configuration flags requires the explicit policy version,
so configuration cannot silently promise an inactive verification guard. Exact
normalized boilerplate reused across approving criteria is rejected; each needs
its own rationale. The software does not infer the truth of a professional
opinion. Old rubric snapshots keep their established rules. Structured request
guards also protect legacy dossiers when staff explicitly create new requests
for them.

Supplement request rows reference the frozen dossier version and criterion
label. Optional claim references must exist in that version. Entries contain
RESPONSE, RESOLVE or REOPEN and increasing per-request sequence numbers.
Existing messages are never overwritten by an endpoint. Internal actor IDs
remain server-side in the persistence/audit records and are excluded from
applicant DTOs.

## APIs and permissions

| Route                                                  | Boundary                                                                                                                                                             |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/v1/dossier-type-versions/{versionId}`        | Authenticated form access; parent type must still be active                                                                                                          |
| `PUT /api/v1/dossiers/{id}/claims`                     | Existing mutation role/scope and editable state; expected claims revision; evidence must belong to current draft                                                     |
| Existing reviewer assignment draft/submit routes       | Assigned reviewer, cleared conflict, locked snapshot; existing CSRF and role checks                                                                                  |
| Existing admin council decision, vote and close routes | Existing authority plus frozen policy separation/completeness guards                                                                                                 |
| `GET /api/v1/dossiers/{id}/supplement-requests`        | Owner or eligible current assigned staff/admin; unreleased OPEN requests are hidden from owner outside NEEDS_SUPPLEMENT; answered/resolved history remains available |
| `POST` to that request collection                      | Eligible current staff/admin, active review, expected version ID, frozen criterion/claim validation                                                                  |
| `PUT .../{requestId}/response`                         | Owner only, NEEDS_SUPPLEMENT only, OPEN request and expected revision                                                                                                |
| `POST .../{requestId}/resolve`                         | Eligible staff/admin, active review and expected revision; explicit resolution or reopening reason                                                                   |

All writes retain existing CSRF protection. Assignment membership alone does not
grant reviewer access after role withdrawal or a conflict. Owning the dossier
does not grant staff authority to resolve one's own requests. Request lists are
bounded to 100 records per dossier, matching the explicit creation limit; this
is an operational limit, not a fee or certification rule.

## Applicant and reviewer operation

The seven business activities fit the existing preparation/completion stages:
choose a type; declare subject information; add its type-specific narrative;
state criterion claims; attach/link evidence; inspect the dossier; submit
through the existing fee policy. Preparation recovery/autosave and uploads are
reused. The claim editor provides explicit save/discard and concurrency errors.

Reviewers see frozen applicant claims beside each corresponding criterion,
without adopting self-declarations as conclusions. Relevance and content checks
are separate. Uncited relevant contradictions still prevent approval. Missing
sources can be recorded as insufficient basis with a concrete applicant request.

Staff save structured supplement items, then use the existing admin request-
supplement transition to release them and send the existing encrypted notice.
Saving an item alone does not send a notice or alter dossier/payment state.
Owners reply and add documents through existing editable dossier controls; every
open item must be answered or resolved before resubmission. Staff then verify
and resolve the items, preserving earlier entries and versions. No duplicate fee
is introduced by creating, responding to or resolving requests.

## State mapping

Existing dossier states remain DRAFT, SUBMITTED, PRECHECK, NEEDS_SUPPLEMENT,
UNDER_REVIEW, COUNCIL_REVIEW and existing decision/payment/anchor/certificate/
publication/revocation states. Payment, relevance, verification, assignment and
supplement statuses remain separate axes. No expanded catch-all enum is added.

Supplement states are OPEN -> ANSWERED -> RESOLVED; a documented staff REOPEN
returns to OPEN without deleting entries. Existing dossier transition services
remain authoritative. A request on an earlier version must still be resolved
before approval of the current dossier.

## Migrations and recovery

1. 0149 appends evidence-policy template versions for the 12 built-in types.
2. 0150 adds private claims JSON and optimistic revision to dossiers.
3. 0151 appends enriched narrative template versions, preserving other schema
   data.
4. 0152 adds structured supplement requests and sequenced response/decision
   rows.

All were exercised only in temporary SQLite databases. Template downgrades
refuse to remove versions referenced by dossiers or saved preparations,
including alternate UUID text forms. Claims downgrade refuses edited data.
Supplement downgrade refuses any request/response history. Recovery after use is
compatible roll-forward or an approved backup restore, never automatic deletion
of live data.

Before staging: capture database/object-store backups, apply reviewed revisions,
check old and new dossiers with real role accounts, exercise sandbox payments
and concurrency, and verify restore. Do not deploy old application code that can
ignore new history or policy guards while keeping new-policy dossiers active.

## Verification record

Final consolidated checks passed: 153 backend tests across the affected business
flows and four migration roundtrips; the full frontend suite passed 1,018 tests
across 239 files. Ruff lint and formatting passed across the backend. Targeted
mypy, frontend typecheck and the browser cases below also passed. The optimized
Next.js production build passed, including its TypeScript/static-page checks.
Full backend mypy passed across 485 source files. Frontend ESLint reported no
errors and four pre-existing unused-variable warnings in the untouched
membership chat administration component. Generated test-server configuration
was restored; build output and synthetic evidence remain outside the delivered
source diff.

Six Chrome cases passed for claims, verification and structured supplementation
across desktop/mobile. They include overflow checks and axe scans limited to the
changed panels. They use synthetic API fixtures and do not prove deployed
provider behavior. Evidence is in
`tmp/structured-dossier-final-browser-20261030/`. Ten additional desktop/mobile
Chrome regression cases passed for the critical applicant/payment/certificate
journey and reviewer submission/tablet/dark-mode paths, in
`tmp/structured-dossier-regression-browser-20261030/`.

## Remaining acceptance limits

- PostgreSQL locking/concurrency and deployed migration/restore are unverified.
- Real authentication/MFA, notification delivery, provider sandbox
  reconciliation, chain signing, physical Safari/Android and measured CWV
  require staging/devices.
- There is no separate adjudication entity for per-criterion expert
  disagreement; recovery uses existing assistance, supplement, version and
  independent review routes. Submitted opinions are not silently replaced.
- New narratives are optional until an authorized template version changes their
  required rules. There is no new graphical template governance console.
- Supplement items identify a criterion/optional claim, not arbitrary per-field
  unlock policies. Existing editable dossier controls remain the allowed
  surface.
- Migration 0152 must be applied before enabling this code against a deployed
  DB.

This is local implementation evidence, not a declaration that every item in the
master prompt or production rollout has been accepted.


## UI/UX hồ sơ, thẩm định và quản trị — 2026-11-14

### Audit đã xác minh

- Nghiệp vụ/backend: thu phí trước tiếp nhận đã có trong `dossiers/service.py` và `billing/submission_policy.py`; không cần viết lại giao dịch hay migration. Chế độ DYNAMIC, thời điểm nộp phí và thời điểm miễn phí trước đây chưa được cung cấp đủ cho mọi vai trò. Enum hồ sơ không phải enum nghĩa vụ phí.
- Dữ liệu/tiến độ: timeline cũ suy diễn hoàn tất theo vị trí, coi công bố đồng nghĩa toàn bộ các chặng đều hoàn tất; mặc định đặt phí sau thẩm định. Lịch sử cũ cần ưu tiên sự kiện thực tế, không sửa lịch sử để đồng nhất giao diện.
- Kiến trúc thông tin: trang khóa vẫn dựng wizard; bước xác nhận lặp danh sách tệp và phiên bản/lịch sử. Workspace thẩm định dùng liên kết cuộn, giữ tất cả khối biểu mẫu trên cùng trang. Master-detail tiêu chí đã tồn tại; thay đổi này giữ lại và bổ sung điều hướng tác vụ/mobile.
- Tương tác: form phân công luôn mở; form quyết định xuất hiện trước khi báo cáo hoàn tất. Tự lưu báo đã lưu trong khoảng debounce; lưu tay và tự lưu có thể chạy đồng thời; bản nháp chưa có cơ chế chống ghi đè từ phiên khác.
- UI/nội dung/responsive: metadata tệp dùng MIME kỹ thuật; nhiều cột lồng ở phần kiểm tra tài liệu; hướng dẫn sau phê duyệt vẫn yêu cầu lập phí đối với hồ sơ đã hoàn tất phí nộp. Uploader hiện có dropdown, hàng đợi, giới hạn, retry và chọn tệp mobile nên được giữ lại.

### Triển khai

- Người nộp: tách `SubmittedDossier` khỏi phần chuẩn bị, dùng Tổng quan/Tài liệu/Yêu cầu bổ sung/Lịch sử. Không dựng form chỉnh sửa sau khóa, không lặp banner thành công khi truy cập lại. Bước xác nhận chỉ giữ tóm tắt và nghĩa vụ phí; lịch sử chuyển ra ngoài wizard. Giữ quyền bổ sung do server quyết định và dịch vụ quảng bá tùy chọn.
- Tiến độ: `dossier-progress.ts` là bộ ánh xạ dùng chung; `DossierWorkflowTimeline` được dùng bởi người nộp, người thẩm định và Admin. Hoàn tất dựa trên sự kiện ra khỏi chặng hoặc chứng cứ thanh toán/miễn phí/phát hành; không dựa chỉ số. Sự kiện phí sau thẩm định được ưu tiên để giữ trình tự lịch sử. Mobile hiển thị chặng hiện tại, việc tiếp theo và timeline dọc có thể mở thêm. Nội dung chờ bổ sung phù hợp vai trò.
- Người thẩm định: tách tài liệu hồ sơ/phiếu/bổ sung-phối hợp; trong phiếu tách kiểm tra tệp/điều kiện/tiêu chí/báo cáo. Một tài liệu, một điều kiện và một tiêu chí chuyên biệt tại một thời điểm. Giữ state khi đổi mục, dropdown tiêu chí trên mobile, danh sách bên cạnh trên desktop; có tổng hợp kết luận và các mục thiếu. Luồng 5T lịch sử vẫn giữ nguyên thang điểm và quy tắc.
- Admin: mở bộ chọn người theo nhu cầu, danh sách phân công/báo cáo gọn với thời hạn và tiến độ; chi tiết báo cáo mở thêm. Chỉ hiển thị form quyết định ở UNDER_REVIEW khi có báo cáo đã gửi và mọi phân công kết thúc. Server tiếp tục kiểm tra tính độc lập, số báo cáo, yêu cầu bổ sung và tính toàn vẹn trước khi chấp nhận quyết định.
- Lưu nháp: cùng hàng đợi cho tự lưu/lưu tay/xác nhận gửi; báo chưa lưu/đang lưu/lỗi chính xác, bảo vệ rời trang. `draftToken` và `X-Review-Draft-Token` là cơ chế so khớp nội dung dưới khóa hiện hữu; lỗi 409 giữ nguyên bản nhập, không tự đổi token để ghi đè. Client cũ không gửi header vẫn tương thích; client cũ có thể chưa được bảo vệ đồng thời.

### Hợp đồng và bảo toàn dữ liệu

- Dossier responses bổ sung `submissionFeePolicyMode` và `submissionFeeTestExempted` chỉ đọc. Hai endpoint chi tiết thẩm định bổ sung `workflowProgress` có schema rõ ràng; không chuyển actor hoặc ghi chú lịch sử nội bộ cho người thẩm định. Chỉ cấp dữ liệu khi phân công được phép xem snapshot.
- Review responses bổ sung token nội dung; lưu nháp nhận header tùy chọn. Không thay URL, role, enum, rubric, schema database, tiền, lịch sử, điều kiện ký/phát hành/công bố hoặc môi trường production.
- Ngày phân công chưa có trong model ReviewAssignment hiện tại; không tự suy diễn từ thời hạn hay ngày gửi báo cáo. Không thêm migration chỉ để làm đầy giao diện.
- Quyền bổ sung hiện theo hồ sơ/tiêu chí, chưa có chính sách mở từng trường tùy ý; UI tuân theo `canEdit` và endpoint bổ sung hiện hữu, không tự cấp quyền mới.

### Kiểm chứng và giới hạn

Kết quả cuối, đường dẫn ảnh và danh sách tệp được cập nhật sau lượt kiểm tra cuối. E2E dùng Next.js chạy thật với API giả lập và dữ liệu tổng hợp; pytest kiểm tra nghiệp vụ/API với database cô lập. Chúng không chứng minh giao dịch nhà cung cấp, thông báo, chữ ký hoặc khóa PostgreSQL trên staging. Không dùng tiền thật, không migrate production, không push/merge/deploy.

### Kết quả bàn giao cuối

| Kiểm tra | Kết quả |
| --- | --- |
| Root repository tests | 10 đạt |
| Frontend đầy đủ | 248 files, 1.094 ca đạt; lượt ổn định giới hạn 4 workers |
| Backend đầy đủ | 1.370 đạt, 3 bỏ qua; 321 warnings phụ thuộc/cleanup thread, không có ca thất bại |
| Backend hồi quy sau thay đổi token/API | 32 đạt, gồm scoring/API, assignment, submission và dynamic fees |
| Component kiểm tra cuối | 31 đạt, gồm 5T, verdict, tài liệu, Admin và tiến độ |
| E2E liên quan | 32 đạt, 2 bỏ qua theo loại thiết bị; 7 files, desktop + mobile Chrome |
| Format, lint, typecheck | Đạt; mypy 504 source files, ruff format 1.042 files |
| Production build | Đạt |
| Git diff whitespace | Đạt |

Bộ đầy đủ được chạy trong quá trình triển khai; các thay đổi cuối được kiểm tra lại bằng các bộ hồi quy trọng tâm, format/lint/typecheck/build và lượt E2E cuối trên source đã ổn định. E2E cuối dùng hai project trong cùng lượt, Next trên cổng 3125 và mock API trên cổng 4025. Source không phụ thuộc các cổng kiểm thử này.

Ba ca backend bỏ qua: advertising concurrency và staff invitations cần PostgreSQL cô lập; blockchain gateway Anvil là kiểm thử opt-in. Hai ca E2E bỏ qua là bản kiểm tra mobile khi chạy desktop và bản kiểm tra tablet riêng khi chạy mobile. Các lần chạy dev server dùng lại từng có lỗi 500 liên kết tài liệu; lượt cô lập cuối không tái hiện và đã đạt đủ 32 ca. Các warnings pytest vẫn cần theo dõi riêng, không bị xóa hoặc che bằng việc sửa test.

### Component dùng lại

- `TaskNavigation`: điều hướng tác vụ người nộp, workspace và hai dạng phiếu; dùng button native có trạng thái được chọn, giữ nội dung mounted để không mất bản nhập.
- `DossierWorkflowTimeline` + `dossierProgress`: cùng bộ định nghĩa và bằng chứng tiến độ cho ba vai trò, không nhân bản mốc xử lý.
- `EvidenceItem`, `EvidenceViewer`, `PrivateDocumentVerification`, `FileUploader`: giữ truy cập ký tạm, xem trước, đối chiếu hash, giới hạn tệp và hàng đợi hiện hữu; phần kỹ thuật chỉ mở khi cần.
- `SupplementRequestsPanel`, `ConfirmationDialog`, `useReviewAutosave`: giữ nghiệp vụ bổ sung, xác nhận trước gửi và bản nháp; không viết một quy trình song song.

### Ảnh giao diện (chỉ lưu cục bộ, không đưa vào Git)

- [Hồ sơ sau nộp / tiến độ desktop](../../.tmp/uiux-evidence/test-account-submission-ex-13db7-n-submits-without-a-payment-desktop-chrome/submitted-progress-1440.png)
- [Tải tài liệu mobile](../../.tmp/uiux-evidence/test-account-submission-ex-13db7-n-submits-without-a-payment-mobile-chrome/dossier-upload-390.png)
- [Workspace người thẩm định / xem tài liệu](../../.tmp/uiux-evidence/reviewer-reviewer-reviews--b0afa--submits-a-criteria-verdict-desktop-chrome/review-form-before-submit.png)
- [Đánh giá tiêu chí desktop](../../.tmp/uiux-evidence/reviewer-reviewer-criteria-76834-get-viewport-in-both-themes-desktop-chrome/criteria-light-1440.png)
- [Đánh giá tiêu chí mobile / dark mode](../../.tmp/uiux-evidence/reviewer-reviewer-criteria-76834-get-viewport-in-both-themes-mobile-chrome/criteria-dark-390.png)
- [Admin phân công](../../.tmp/uiux-evidence/reviewer-admin-opens-assig-1a645-for-reports-before-deciding-desktop-chrome/admin-assignment-1440.png)
- [Admin báo cáo và quyết định](../../.tmp/uiux-evidence/reviewer-reviewer-reviews--b0afa--submits-a-criteria-verdict-desktop-chrome/admin-review-report.png)
- [Tiến độ mobile](../../.tmp/uiux-evidence/test-account-submission-ex-13db7-n-submits-without-a-payment-mobile-chrome/submitted-progress-390.png)

### Git và việc còn cần kiểm chứng

Branch `main`, HEAD nền `67313e07`; không tạo commit mới, chưa stage, push, merge hoặc deploy. Không có migration mới. Thay đổi `tsconfig.json` do Next tự thêm đường dẫn output đã được khôi phục; ảnh, logs và build output được Git bỏ qua.

Cần staging để xác minh PostgreSQL locking thực, đăng nhập/MFA thực, thông báo, nhà cung cấp thanh toán sandbox, ký/phát hành/công bố xuyên hệ thống và thiết bị Safari/Android thật. Chưa chạy toàn bộ các file E2E ngoài 7 file thuộc hành trình này. Chống ghi đè được bật cho UI mới gửi token; client cũ không gửi token vẫn giữ hành vi tương thích. Không tuyên bố nghiệm thu production từ fixture local.

### Danh sách tệp thay đổi

- [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py)
- [backend/app/modules/dossiers/schemas.py](../../backend/app/modules/dossiers/schemas.py)
- [backend/app/modules/dossiers/service.py](../../backend/app/modules/dossiers/service.py)
- [backend/app/modules/dossiers/types.py](../../backend/app/modules/dossiers/types.py)
- [backend/app/modules/reviews/schemas.py](../../backend/app/modules/reviews/schemas.py)
- [backend/app/modules/reviews/service.py](../../backend/app/modules/reviews/service.py)
- [backend/app/modules/reviews/types.py](../../backend/app/modules/reviews/types.py)
- [backend/app/tests/test_review_assignment.py](../../backend/app/tests/test_review_assignment.py)
- [backend/app/tests/test_review_scoring.py](../../backend/app/tests/test_review_scoring.py)
- [backend/app/tests/test_review_scoring_api.py](../../backend/app/tests/test_review_scoring_api.py)
- [docs/handoffs/structured-dossier-review-2026.md](../../docs/handoffs/structured-dossier-review-2026.md)
- [docs/specs/structured-dossier-review-2026.md](../../docs/specs/structured-dossier-review-2026.md)
- [frontend/e2e/dossier-review-ux.spec.ts](../../frontend/e2e/dossier-review-ux.spec.ts)
- [frontend/e2e/dossier-theme.spec.ts](../../frontend/e2e/dossier-theme.spec.ts)
- [frontend/e2e/review-evidence-policy.spec.ts](../../frontend/e2e/review-evidence-policy.spec.ts)
- [frontend/e2e/reviewer.spec.ts](../../frontend/e2e/reviewer.spec.ts)
- [frontend/e2e/submission-review-flow.spec.ts](../../frontend/e2e/submission-review-flow.spec.ts)
- [frontend/e2e/test-account-submission.spec.ts](../../frontend/e2e/test-account-submission.spec.ts)
- [frontend/src/components/admin/review-assignment-queue.test.tsx](../../frontend/src/components/admin/review-assignment-queue.test.tsx)
- [frontend/src/components/admin/review-lifecycle-panel.test.tsx](../../frontend/src/components/admin/review-lifecycle-panel.test.tsx)
- [frontend/src/components/admin/review-lifecycle-panel.tsx](../../frontend/src/components/admin/review-lifecycle-panel.tsx)
- [frontend/src/components/dossiers/dossier-list.tsx](../../frontend/src/components/dossiers/dossier-list.tsx)
- [frontend/src/components/dossiers/dossier-progress.ts](../../frontend/src/components/dossiers/dossier-progress.ts)
- [frontend/src/components/dossiers/dossier-status.tsx](../../frontend/src/components/dossiers/dossier-status.tsx)
- [frontend/src/components/dossiers/dossier-workflow-timeline.test.tsx](../../frontend/src/components/dossiers/dossier-workflow-timeline.test.tsx)
- [frontend/src/components/dossiers/dossier-workflow-timeline.tsx](../../frontend/src/components/dossiers/dossier-workflow-timeline.tsx)
- [frontend/src/components/dossiers/dossier-workspace.test.tsx](../../frontend/src/components/dossiers/dossier-workspace.test.tsx)
- [frontend/src/components/dossiers/dossier-workspace.tsx](../../frontend/src/components/dossiers/dossier-workspace.tsx)
- [frontend/src/components/reviews/evidence-viewer.tsx](../../frontend/src/components/reviews/evidence-viewer.tsx)
- [frontend/src/components/reviews/five-t-scorecard.test.tsx](../../frontend/src/components/reviews/five-t-scorecard.test.tsx)
- [frontend/src/components/reviews/five-t-scorecard.tsx](../../frontend/src/components/reviews/five-t-scorecard.tsx)
- [frontend/src/components/reviews/review-evidence-assessments.tsx](../../frontend/src/components/reviews/review-evidence-assessments.tsx)
- [frontend/src/components/reviews/review-workspace-flow.test.tsx](../../frontend/src/components/reviews/review-workspace-flow.test.tsx)
- [frontend/src/components/reviews/review-workspace.test.tsx](../../frontend/src/components/reviews/review-workspace.test.tsx)
- [frontend/src/components/reviews/review-workspace.tsx](../../frontend/src/components/reviews/review-workspace.tsx)
- [frontend/src/components/reviews/specialist-rubric-section.tsx](../../frontend/src/components/reviews/specialist-rubric-section.tsx)
- [frontend/src/components/reviews/use-review-autosave.test.tsx](../../frontend/src/components/reviews/use-review-autosave.test.tsx)
- [frontend/src/components/reviews/use-review-autosave.ts](../../frontend/src/components/reviews/use-review-autosave.ts)
- [frontend/src/components/reviews/verdict-review-form.test.tsx](../../frontend/src/components/reviews/verdict-review-form.test.tsx)
- [frontend/src/components/reviews/verdict-review-form.tsx](../../frontend/src/components/reviews/verdict-review-form.tsx)
- [frontend/src/components/ui/task-navigation.tsx](../../frontend/src/components/ui/task-navigation.tsx)
- [frontend/src/lib/api/client.ts](../../frontend/src/lib/api/client.ts)
- [frontend/src/lib/api/types.ts](../../frontend/src/lib/api/types.ts)
