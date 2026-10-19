# Help Center source audit

> Lưu ý: đây là bản chụp trước các migration `0116`–`0120` và thay đổi lọc
> quyền đọc. Bản đồ và trạng thái mới nhất nằm tại
> [help-center-workflow-map.md](help-center-workflow-map.md) và
> [help-center-business-review-2026-10.md](help-center-business-review-2026-10.md).

Audit of the current Help Center, guide API, authorization model, and seeded guide content (2026-10-18). Source review and read-only production browser checks were completed; local role E2E could not start because Next.js was denied access to create its cache directory. Focused unit and backend guide tests passed.

## Product roles and effective permissions

The application declares four product roles: `VIEWER`, `USER`, `MODERATOR`, and `SUPER_ADMIN` ([role constants](../backend/app/modules/auth/roles.py#L1-L10)). Account type is separate: registration maps `PUBLIC_USER` to `VIEWER` and applicant account types to `USER` ([account types](../backend/app/modules/auth/models.py#L31-L34), [registration role assignment](../backend/app/modules/auth/services.py#L116-L126)). The staff account schema currently allows `MODERATOR` as its managed staff role ([staff role schema](../backend/app/modules/auth/schemas.py#L18-L22)).

Effective permissions are the union of role-permission grants and direct, non-expired user grants ([permission query](../backend/app/modules/auth/repositories.py#L189-L213)). Server policy checks allow the requested permission, a compatible role, or `SUPER_ADMIN` unless a policy opts out ([policy behavior](../backend/app/modules/auth/authorization.py#L18-L40)). The role-consolidation migration left `VIEWER` without role grants, transferred applicant-role grants to `USER`, restricted `MODERATOR` to review permissions, and assigned `SUPER_ADMIN` the catalog entries present at that migration ([migration mapping](../backend/alembic/versions/0058_four_product_roles.py#L23-L45), [role grants](../backend/alembic/versions/0058_four_product_roles.py#L299-L318), [moderator restriction](../backend/alembic/versions/0061_restrict_moderator_permissions.py#L20-L70)). The later admin catalog migration inserts codes without assigning role grants ([0063 catalog](../backend/alembic/versions/0063_admin_permission_catalog.py#L20-L77)); Super Admin access to policy-protected capabilities is principally covered by the server policy role bypass.

### Permission catalog checked in source

`0042_authorization_permissions.py` contains the initial grants (`admin.staff.manage`, `audit.read`, `blockchain.manage`, `certificate.read`, `cms.manage`, `council.manage`, `council.vote`, `dossier.manage`, `engagement.qr.manage`, `operations.read`, `payment.create`, `payment.manage`, `public_content.manage`, `ranking.manage`, `review.assign`, `review.submit`, `search.analytics.read`). `0063_admin_permission_catalog.py` adds the user/staff, submission, payment, blockchain, storage, security, system, reports, and settings codes: `dashboard.read`; `users.read`, `users.update`, `users.suspend`, `users.sessions.revoke`; `staff.read`, `staff.invite`, `staff.update`, `staff.permissions.assign`; `submissions.read`, `submissions.review`, `submissions.approve`, `submissions.reject`; `payments.read`, `payments.reconcile`, `payments.refund`, `payments.export`; `blockchain.read`, `blockchain.retry`; `storage.read`, `storage.delete`; `security.read`, `security.manage`; `system.read`, `system.manage`; `reports.read`, `reports.export`; `settings.read`, `settings.manage`.

Later source policies add capability codes for HR, community moderation, work allocation, blockchain signing, payment issue/reconcile, certificate version requests, job operations, dossier evidence, and other workflows. The active list of permission rows and account grants lives in the configured database, so a source-only scan cannot report the effective permissions of a real account. The local `.env` declares `APP_ENV=local` but its database URL points to a remote Neon host; it was not queried. The account Help Center reports the product role with a `Vai trò` label; it does not claim to list effective permission codes.

| Role | Current workspace and workflow inventory |
|---|---|
| `VIEWER` | Discovery (`/works`, `/community`, `/verify`), personal account tools, and account Help. No dossier or employee navigation. Persona fallback is `VIEWER` ([persona resolver](../frontend/src/lib/auth/role-workspaces.ts#L48-L55), [navigation sections](../frontend/src/components/layout/dashboard-navigation.tsx#L298-L312)). |
| `USER` | Viewer discovery and personal tools, plus `/dossiers` and `/certificates`; `/dossiers/new` is also role-gated to `USER` ([navigation items](../frontend/src/components/layout/dashboard-navigation.tsx#L79-L82), [dossier guard](../frontend/src/app/%28dashboard%29/dossiers/layout.tsx#L1-L6)). Employee self-service navigation is added when `isEmployee` is true ([conditional menu](../frontend/src/components/layout/dashboard-navigation.tsx#L298-L303)). |
| `MODERATOR` | Assigned reviews and work allocations, discovery, personal account, Help, and employee self-service menu items ([navigation](../frontend/src/components/layout/dashboard-navigation.tsx#L84-L96), [moderator sections](../frontend/src/components/layout/dashboard-navigation.tsx#L285-L295)). Review pages allow `MODERATOR` and `SUPER_ADMIN`; `/work-allocations` allows `MODERATOR` ([review guard](../frontend/src/app/%28dashboard%29/reviews/layout.tsx#L3-L6), [allocation guard](../frontend/src/app/%28dashboard%29/work-allocations/page.tsx#L1-L12)). The menu currently shows employee items for every moderator, regardless of `isEmployee`; backend self-service still requires a linked employee record ([attendance/leave/overtime policy](../backend/app/modules/hr/service.py#L1838-L1858), [leave policy](../backend/app/modules/hr/service.py#L2441-L2463), [overtime policy](../backend/app/modules/hr/service.py#L2863-L2885)). |
| `SUPER_ADMIN` | Admin operations (HR, payments, users/staff, audit/reports, publication/certificates, community, review assignment) and the admin guide; Super Admin or a holder of `blockchain.sign` sees the blockchain entry ([admin navigation](../frontend/src/components/layout/dashboard-navigation.tsx#L98-L218), [access filter](../frontend/src/components/layout/dashboard-navigation.tsx#L220-L234), [admin navigation sections](../frontend/src/components/layout/dashboard-navigation.tsx#L258-L282)). Admin dashboard and guide pages are role-gated ([dashboard](../frontend/src/app/%28dashboard%29/admin/dashboard/page.tsx#L5-L14), [guide](../frontend/src/app/%28dashboard%29/admin/guide/page.tsx#L89-L104)). |

The dashboard shell authenticates users, while individual pages apply role or permission gates ([dashboard layout](../frontend/src/app/%28dashboard%29/layout.tsx#L11-L25)). `RoleGate` treats an allowed role **or** one listed permission as sufficient ([gate condition](../frontend/src/components/auth/role-gate.tsx#L13-L27)); navigation entries that specify both role and permission require both ([navigation filter](../frontend/src/components/layout/dashboard-navigation.tsx#L220-L234)). Direct-permission holders can therefore have different menu discoverability from route authorization.

## Guide APIs and audience resolution

`/guide` uses the public guide center; `/help` uses the account center ([public page](../frontend/src/app/%28public%29/guide/page.tsx#L1-L20), [account page](../frontend/src/app/%28dashboard%29/help/page.tsx#L1-L6)). The centers choose the public or authenticated API; authenticated list and detail endpoints require a current principal and employee-link status ([center query](../frontend/src/components/guide/guide-center.tsx#L91-L115), [API routes](../backend/app/api/v1/cms.py#L125-L174)).

Audiences are `PUBLIC`, the four product roles, and `EMPLOYEE` ([audience enum](../backend/app/modules/cms/schemas.py#L107-L113)). Account guide access includes `PUBLIC` plus the principal's role tags; it adds `EMPLOYEE` for a linked employee. A `SUPER_ADMIN` additionally receives every role audience and `EMPLOYEE` even without an employee link ([service audience rules](../backend/app/modules/cms/service.py#L499-L523), [detail audience rules](../backend/app/modules/cms/service.py#L532-L545)). Employee status means an `Employee` row links to the account; the dependency does not filter employment status ([link check](../backend/app/modules/auth/dependencies.py#L44-L56)). Audience matching is any overlap, while public endpoints require `PUBLIC` and `PUBLISHED` ([repository filter](../backend/app/modules/cms/repository.py#L122-L155), [OR filter](../backend/app/modules/cms/repository.py#L280-L303)).

Guide authoring and CMS APIs require `cms.manage` or `SUPER_ADMIN` on the server ([CMS policy](../backend/app/modules/cms/service.py#L36-L36), [admin requirement](../backend/app/modules/cms/service.py#L1049-L1055)); the current editor page is frontend-gated to `SUPER_ADMIN` ([editor route](../frontend/src/app/%28dashboard%29/admin/guide/articles/page.tsx#L1-L10)).

## Seeded guide inventory and gaps

Revision `0112_cms_guide_articles` seeds nine articles as `PUBLISHED` ([seed rows](../backend/alembic/versions/0112_cms_guide_articles.py#L129-L220), [publish status](../backend/alembic/versions/0112_cms_guide_articles.py#L241-L271)). Follow-up revision `0113_help_center_role_audit` adds a `VIEWER` article and normalizes the two seed category values, without changing user-edited article rows ([follow-up migration](../backend/alembic/versions/0113_help_center_role_audit.py)).

| Slug | Audience | Topic / source |
|---|---|---|
| `explore-nominations` | `PUBLIC` | Search and view published nominations; `getting-started` ([seed](../backend/alembic/versions/0112_cms_guide_articles.py#L132-L140)). |
| `create-account-and-sign-in` | `PUBLIC` | Register, verify email, sign in, recover access; `account` ([seed](../backend/alembic/versions/0112_cms_guide_articles.py#L142-L150)). |
| `viewer-account-basics` | `VIEWER` | Open public discovery, use account tools, and choose the applicant account upgrade flow; `getting-started` ([seed](../backend/alembic/versions/0113_help_center_role_audit.py)). |
| `create-and-submit-a-dossier` | `USER` | Prepare, save, and submit a dossier; `dossiers` ([seed](../backend/alembic/versions/0112_cms_guide_articles.py#L152-L160)). |
| `track-and-update-a-dossier` | `USER` | Follow status, supplement documents, avoid duplicate payment; `dossiers` ([seed](../backend/alembic/versions/0112_cms_guide_articles.py#L162-L170)). |
| `my-certificates` | `USER` | View/download issued certificates, inspect versions and submit a qualified update request; `certificates` ([seed](../backend/alembic/versions/0113_help_center_role_audit.py)). |
| `review-an-assigned-dossier` | `MODERATOR` | Review assigned work and submit a conclusion; `reviews` ([seed](../backend/alembic/versions/0112_cms_guide_articles.py#L172-L180)). |
| `attendance-and-employee-requests` | `EMPLOYEE` | Attendance, leave, and overtime; `employee-workflows` ([seed](../backend/alembic/versions/0112_cms_guide_articles.py#L182-L190)). |
| `verify-a-certificate` | `PUBLIC` | Verify by code or QR and explain certificate limits; `verification` ([seed](../backend/alembic/versions/0112_cms_guide_articles.py#L192-L200)). |
| `admin-operations-start` | `SUPER_ADMIN` | Start-of-shift checks and guide CMS publishing; `administration` ([seed](../backend/alembic/versions/0112_cms_guide_articles.py#L202-L210)). |
| `common-account-and-guide-questions` | `PUBLIC` | Email, assignment, employee feature, and payment FAQs; `faq` ([seed](../backend/alembic/versions/0112_cms_guide_articles.py#L212-L220)). |

### Accuracy and completeness gaps

- The missing `VIEWER` article was added in `0113`. It documents discovery, personal tools, the existing applicant upgrade card, and the post-upgrade dossier guide link. `USER` certificate management also now has its own article.
- `EMPLOYEE` is a separate audience, not a role. Ordinary users and moderators receive that guide only when an employee profile is linked, but `SUPER_ADMIN` receives it unconditionally. The guide audience label describes it as for linked employees ([audience labels](../frontend/src/components/guide/guide-center.tsx#L43-L50)); the service's Super Admin expansion is broader ([service](../backend/app/modules/cms/service.py#L509-L514)).
- Direct admin permissions are not guide audiences: account guide filtering considers roles and employee-link status, not `principal.permissions` ([service filter](../backend/app/modules/cms/service.py#L499-L523)). Staff granted a specific operational permission therefore do not receive capability-specific filtering; instructions for those grants must remain conditional in role articles.
- The seeded CMS corpus has one broad Super Admin article. The admin navigation still routes “Hướng dẫn” to the separate static `/admin/guide` page, while the role-scoped CMS center is `/help` ([navigation target](../frontend/src/components/layout/dashboard-navigation.tsx#L67-L77), [static admin guide](../frontend/src/app/%28dashboard%29/admin/guide/page.tsx#L89-L104)). This splits admin guidance between the static guide and the CMS article list.
- The `0113` migration normalizes seeded `reviews` and `faq` categories. The frontend retains readable labels for these legacy values ([category labels](../frontend/src/components/guide/guide-center.tsx#L23-L58)).
- Moderator employee links now appear only when `isEmployee` is true; backend self-service still requires a linked employee profile ([navigation](../frontend/src/components/layout/dashboard-navigation.tsx#L285-L295), [attendance profile requirement](../backend/app/modules/hr/service.py#L1838-L1858)).

## Live website and visual checks

Read-only production inspection of `https://decu.tinhhoaviet.org.vn/guide` found the older static guide page, not the role-scoped CMS Help Center. It contains eight anchored sections: workflow overview, nominations, account, dossier submission, tracking, verification, installation, and security/support. All eight navigation anchors resolve. Screenshots: [desktop](help-center-audit/production-guide-desktop.png) and [mobile](help-center-audit/production-guide-mobile.png).

At desktop width 1440 px and mobile width 390 px, the production guide had no horizontal page overflow; the mobile page rendered all eight sections and the anchors remained present. This verifies the public deployed guide's layout only; no authenticated production account was used.

## Local role-account discovery and verification limits

The repository contains local Playwright auth fixtures for all four product roles. They are synthetic identities routed through `firebase-auth-shim.ts` and `mock-auth-server.mjs`, not reusable Firebase-emulator accounts or production credentials. Viewer is selected using the fixture's public-user account type; the other fixtures represent applicant/User, reviewer/Moderator, and Super Admin. No local Docker/Firebase service was running when checked, and the repository's bootstrap script requires explicit credentials rather than providing a saved account set. Although `.env` says `APP_ENV=local`, its database URLs target a remote Neon host; that database was not queried or used to look up accounts.

The focused browser run attempted these local identities against dashboard and review routes, but Next.js could not create/acquire its `.next` cache lock/directory (`EPERM`); the app server never listened, so those dashboard assertions did not execute. The production role dashboards, employee-linked variants, permission-only menu combinations, and authenticated Help API remain unverified in a live browser.

## Changes and test results

- Added `viewer-account-basics` for the Viewer audience and `my-certificates` for USER. The Viewer article reflects the actual “Gửi tác phẩm hoặc hồ sơ” card and its individual/organization choices; the certificate article uses the current list/detail labels, PDF readiness state, QR link, and 20-character update-reason rule.
- Hid Moderator attendance/leave/overtime navigation unless the account has a linked employee profile, matching the backend gate.
- Added human-readable category labels for legacy category keys and migrated untouched seed rows to canonical categories; the migration does not update an article with an author or a version beyond 1.
- Vitest: 16 focused tests passed across guide-center and dashboard-navigation suites.
- Pytest: 6 focused guide migration/service/API tests passed (two existing dependency/reflection warnings).
- ESLint on the edited guide/navigation files and Ruff on the migration/tests passed.
- Playwright: 3 local dashboard/review checks were attempted but blocked before app startup by Windows `EPERM` on the Next.js cache path; not counted as passing.

## Follow-up: documentation-first experience (2026-10-18)

### Findings and changes

- The topic selector combined `KNOWN_CATEGORIES` with returned article categories. That fixed list caused an account to see “Nhân sự” and “Quản trị” even when the filtered API returned no articles for those topics. The center now builds topic cards and filters only from the public or authenticated article response; the authenticated response remains filtered by role and employee link on the server.
- The previous search ranking scored the concatenated title, summary, and body as one string. A title match could therefore lose to an earlier body match. The new `search_title` and `search_summary` fields store normalized text for relevance ordering; the query still filters only articles visible to the caller and remains accent-insensitive.
- The home page now puts “Hướng dẫn sử dụng”, starter articles, available topics, and permission-filtered FAQs ahead of a compact search field. The visible Ctrl+K label and role/audience badges were removed. Ctrl/Cmd+K still focuses the inline search.
- Article pages now use an access-filtered left navigation, breadcrumb, mobile navigation disclosure, sticky table of contents with current-section highlighting, and same-topic related/previous/next links.
- Seed articles now include explicit usage conditions and role-scoped FAQs. The public FAQ article no longer contains reviewer, employee, or payment workflow answers. Migration `0114_guide_docs_search_and_faq` updates only untouched seed articles (`created_by`/`updated_by` are null and `version` is 1); it also rebuilds search text for current content without replacing author-edited bodies.
- The FAQ category is restored for the public FAQ seed. Search for “Nạp tiền” is expected to return no unrelated results: the verified project has dossier-fee payment flows, not a wallet top-up feature, and no equivalent article alias is configured.

### Verification scope

- Production was not written to. The public production guide was inspected read-only in the earlier audit; no authenticated production role was available.
- Authenticated role UI is shown with local preview identities and a read-only in-memory API fixture. Those screenshots verify the guide UI and filtering presentation, not a live production account or production data.
- Full test and browser results for this follow-up are recorded in the completion report for this task.
