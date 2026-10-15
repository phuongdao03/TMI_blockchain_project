# Community module architecture

Date: 2026-10-15. Status: implemented and locally verified; production release not performed.

## Boundaries

Add a `community` backend bounded context with its own SQLAlchemy models, schemas, repository, service, errors, dependencies, API router, and tests. It owns community profiles, categories, posts, comments, tags, relations, reports, settings, and moderation history. It references existing users, media assets, and published works by foreign key; it does not own or mutate the nomination lifecycle.

The frontend adds public routes under `(public)/community` and an admin workspace under `(dashboard)/admin/community`. Data access stays in the shared typed API client and presentation stays in focused components. Shared shells and auth guards remain the existing ones.

## Data model

Initial entities: `community_profiles`, `community_categories`, `community_posts`, `community_post_tags`, `community_comments`, `community_post_likes`, `community_comment_likes`, `community_bookmarks`, `community_follows`, `community_reports`, `community_moderation_logs`, and one community settings row. Attachments reference inspected media assets. Include foreign keys, status checks, unique constraints, list indexes, soft-delete fields, and timestamps.

Important uniqueness: profile username; category slug; post slug; post/tag pair; one like per user/target; one bookmark per user/post; one follow per follower/followee; deduplicated unresolved report where appropriate. Reject self-follow and self-notifications.

## API surface

- Public reads: category list, paginated post feed/search, post-by-slug, public member profile, post comments, and published-work discussion references.
- Authenticated writes: profile setup/update, post draft/submit/update/delete, comments/replies, like/unlike, bookmark/unbookmark, follow/unfollow, and report.
- Permission-gated admin: category/settings management, post/comment transitions, report queue/resolution, member restrictions, and moderation history.
- Use standard envelope/pagination shapes, camelCase response fields, stable status codes, backend input validation, session auth, and CSRF on mutations.

## Backend slice contract (COM-001/002/003/005)

All routes use `/api/v1`; JSON uses camelCase. Reads return the shared
`{ success, data, meta }` envelope. Paginated reads put `{ requestId, page,
pageSize, total }` in `meta`. Mutations require the existing cookie session and
`X-CSRF-Token`, then return `{ success, data, meta: { requestId } }`.

### Public reads

- `GET /community/categories` -> `data[]`: `{ id, name, slug, description,
  icon, sortOrder }`; only active categories, ordered by `sortOrder`, then name.
- `GET /community/posts?page=1&pageSize=20&category=<slug>` -> paginated
  `data[]`: `{ id, slug, title, excerpt, category: { id, name, slug }, author:
  { displayName }, publishedAt }`. `category` is optional; page size is 1–50.
- `GET /community/posts/{slug}` -> `{ id, slug, title, content, excerpt,
  category: { id, name, slug }, author: { displayName }, publishedAt }`.
- Public reads include only `PUBLISHED` posts in active categories. Missing,
  draft, pending, rejected, hidden, or deleted slugs all return 404.
- Author projection contains only a community display name (nullable, with a
  generic fallback in UI); never email, phone, employment, or identity data.

### Authenticated post writes

- `POST /community/posts` body `{ title, content, categoryId }` creates a
  `DRAFT`; response `data` is `{ id, slug, title, content, status, category:
  { id, name, slug }, createdAt, updatedAt }` (201).
- `POST /community/posts/{postId}/submit` submits an owned draft or resubmits
  an edited rejected post; state becomes `PENDING` (200). Approval is
  pre-moderated; create never publishes directly.
- `PATCH /community/posts/{postId}` body `{ title, content, categoryId }` edits
  an owned `DRAFT` or `REJECTED` post. Editing a rejected post returns it to
  `DRAFT`; owner must submit again. Other states return 409.
- `DELETE /community/posts/{postId}` soft-deletes an owned `DRAFT`, `PENDING`,
  `REJECTED`, or `PUBLISHED` post (204); it can no longer be read publicly.
- Inputs are plain text / Markdown source; API stores source text, strips
  control characters, trims outer whitespace, and rejects empty or oversized
  title/content. No HTML rendering is allowed. Attachment behavior is defined
  by the COM-003 media contract below.

### Moderation

- `GET /admin/community/posts?status=PENDING&page=1&pageSize=20` returns the
  paginated moderation queue using the write projection plus `author` and
  `submittedAt`.
- `POST /admin/community/posts/{postId}/publish` body `{ reason }` moves only
  `PENDING` to `PUBLISHED`; `reason` is required and recorded with actor,
  request ID, action, and timestamps.
- `POST /admin/community/posts/{postId}/reject` body `{ reason }` moves only
  `PENDING` to `REJECTED`; reason is required and returned to the moderator
  caller, then stored with the transition. An owner-readable status/detail
  endpoint is outside this backend slice.
- Both transitions require permission `community.moderate` or the
  `SUPER_ADMIN` role. `MODERATOR` by itself is not sufficient. Failed owner or
  capability checks return 403; missing resources and unpublished public
  lookups return 404; invalid state transitions return 409.

The six seeded category slugs are `general`, `heritage-culture`,
`vietnamese-creativity`, `people-community`, `sharing-experiences`, and
`feedback-suggestions`, with Vietnamese names and descriptions from the
product brief.

## Backend interaction and member contract (COM-004)

All responses use the envelopes and `page`/`pageSize`/`total` metadata above.
`community_profiles` is the sole source of public community identity fields:
`username`, `displayName`, nullable `avatarUrl`, and nullable `bio`. Existing
legal/account profile fields are never copied into it. Backfill creates a
stable generated username, leaves optional fields unset, and display names use
the neutral `Thành viên` fallback until the member sets one. Public comment
post/comment authors use `{ id, username, displayName, avatarUrl }`; the safe member projection
is `{ id, username, displayName, avatarUrl, bio, joinedAt,
publishedPostCount, followerCount, followingCount, viewerIsFollowing }`.
`viewerIsFollowing` and public post viewer flags are false for anonymous reads.
`/members/me` uses the same safe identity projection. Never return email,
phone, employment, or other account/profile fields.

Published post summaries and detail also include `{ likeCount, commentCount,
viewerHasLiked, viewerHasBookmarked }`; comment counts exclude deleted comments.
Counts come from indexed correlated subqueries on the paginated post query. Viewer flags use an optional principal.
Personalized response caches must key by viewer identity as well as post/query.

- `GET /community/posts/{postId}/comments?page=1&pageSize=20` returns a
  paginated list of top-level threads: `{ id, parentId, content, author,
  isDeleted, createdAt, replies: [{ id, parentId, content, author,
  isDeleted, createdAt }] }`.
  `total` counts top-level threads. Replies have no nested `replies` field.
- `POST /community/posts/{postId}/comments` body `{ content, parentId? }`
  creates a comment and returns `{ id, postId, parentId, content, author,
  isDeleted: false, createdAt }` (201). A reply must target a top-level comment on the same post;
  replying to a reply returns 409. Content is plain text, bounded, and HTML is
  rejected. Public listing and comment creation require a published post.
- `PATCH /community/comments/{commentId}` body `{ content }` edits only the
  author's live comment (200); `DELETE` on the same path soft-deletes only the
  author's comment (204). Both require session+CSRF. Deleted comments retain
  thread IDs and reply links, but public DTOs set `isDeleted: true`, use the
  neutral `Bình luận đã bị xóa.` content, and set `author: null`.
- `PUT` and `DELETE /community/posts/{postId}/like` are idempotent and return
  `{ postId, likeCount, isLiked }` (200). `PUT` and `DELETE
  /community/posts/{postId}/bookmark` return `{ postId, isBookmarked }` (200).
- `GET /members/me/bookmarks?page=1&pageSize=20` lists the current member's
  bookmarked public post summaries; hidden/unpublished posts are excluded.
- `GET /members/me` requires a session and returns the safe member projection.
  `GET /members/{username}` is public and returns the same projection;
  `GET /members/{username}/posts?page=1&pageSize=20` returns only that
  member's published post summaries. Browser routes use the username; follow
  actions use the opaque `id` in the projection. Inactive/missing members
  return 404.
- `PUT` and `DELETE /members/{memberId}/follow` are idempotent and return
  `{ memberId, isFollowing, followerCount }` (200). Self-follow returns 409.
- Comment, like, bookmark, and follow mutations require the current session and
  CSRF dependency. Relation tables enforce unique user/post or follower/followed
  pairs; handlers preserve idempotent behavior. Owners can PATCH or DELETE
  their comments; deleted text is scrubbed, and public tombstones preserve
  thread IDs while hiding author identity. Public post/comment author fields
  are the opaque member ID, username, display name, and avatar URL from the
  community profile projection.

## Security and content visibility

Authorize at service and route boundaries. Public reads filter to published, non-deleted content before pagination and slug lookup. Owner operations compare the authenticated principal to the stored owner. Admin operations require explicit `community.manage`/`community.moderate` capability; a generic reviewer role is insufficient. Keep private author attributes out of community schemas.

Community markdown is plain text and is safely rendered. Uploads extend the existing scanned-media workflow with a dedicated purpose and a policy that permits delivery only when the asset is attached to a visible community post. Reports and moderation transitions write actor, target, action, reason, and request ID to an append-only moderation log.

## Integration points

- Register models in `backend/alembic/env.py` and router in `backend/app/main.py`.
- Reuse published-work read models for nomination links, media upload/inspection, session/CSRF dependencies, notification persistence, shared API envelopes, public shell, theme, and admin workspace patterns.
- Add explicit permission migration and seed the six default categories. Migration downgrade removes only community-owned objects/permissions.

## Backend reports and administration contract (COM-005)

All paths below are under `/api/v1`. Reads use standard success/pagination
envelopes. Mutations use the current cookie session and CSRF dependency.

- `POST /community/posts/{postId}/reports` and
  `POST /community/comments/{commentId}/reports` accept
  `{ reason: "SPAM" | "HARASSMENT" | "HATE_SPEECH" | "MISINFORMATION" |
  "COPYRIGHT" | "ADVERTISING" | "PRIVACY_VIOLATION" | "OTHER", details? }`; optional details are plain text bounded
  to 2,000 characters. They return
  `{ id, targetType: "POST" | "COMMENT", targetId, status: "OPEN" |
  "RESOLVED" | "DISMISSED", reason, details, createdAt, resolvedAt,
  resolutionAction, resolutionReason, reporter, targetPreview }`.
  A new report returns 201; repeating a report by the same member for the same
  still-open target returns the same DTO with 200. A target must be public when reported: posts
  must be published in an active category, and comments must be live on a
  published post. The reporter and initial request ID are stored privately.
- `GET /admin/community/reports?status=OPEN&page=1&pageSize=20` requires
  `community.moderate` or `SUPER_ADMIN`; each report item has the report DTO
  above. `reporter` is `{ id, username, displayName, avatarUrl }`; post preview
  is `{ type: "POST", id, slug, title, excerpt, author }`; comment preview is
  `{ type: "COMMENT", id, postId, postSlug, postTitle, content, isDeleted,
  author }`. Both preview authors use `{ id, username, displayName, avatarUrl }`;
  comment `author` is null for hidden/deleted comments. Never return email,
  phone, employment, or account profile data.
- `POST /admin/community/reports/{reportId}/resolve` body
  `{ action: "HIDE" | "DISMISS", reason }` requires the same capability and
  CSRF. `HIDE` applies only to currently public targets; `DISMISS` leaves
  content unchanged. Only an open report can be resolved. Invalid state
  transitions return 409. Hiding comments creates a neutral authorless
  tombstone in public threads.
- `POST /admin/community/posts/{postId}/hide|restore` and
  `POST /admin/community/comments/{commentId}/hide|restore` body `{ reason }`
  require `community.moderate` or `SUPER_ADMIN` and CSRF. Hide accepts only
  currently visible published posts or live comments; restore accepts only
  moderator-hidden posts/comments, and post restore requires an active category.
  Owner-deleted comments cannot be restored. These routes return
  `{ targetType, targetId, state: "HIDDEN" | "VISIBLE" }` and append a
  moderation event.
- `GET /admin/community/moderation-history?targetType=&targetId=&page=1&pageSize=20`
  requires `community.moderate` or `SUPER_ADMIN` and returns append-only events
  `{ id, targetType, targetId, action, actorId, actor, reason, requestId,
  createdAt }`. `actor` is `{ id, username, displayName, avatarUrl }` from the
  safe community profile projection.
  Report resolution, post/comment transitions, category changes, and settings
  changes record actor, reason, and request ID. Original report submissions
  retain reporter, reason, and request ID on the report record.
- `GET /admin/community/categories` lists active and inactive categories.
  `POST /admin/community/categories` body
  `{ name, slug, description, icon?, sortOrder?, isActive?, reason }` creates a
  category (201). `PATCH /admin/community/categories/{categoryId}` accepts the
  same editable fields optionally plus required `reason`. These routes require
  `community.manage` or `SUPER_ADMIN` and CSRF. Slug is unique, names/slugs are
  non-empty and length-bounded, and `sortOrder >= 0`; deactivation preserves
  category/post history and removes its posts from public reads. Category DTOs
  are `{ id, name, slug, description, icon, sortOrder, isActive }`.
- `GET /admin/community/settings` returns
  `{ preModerationEnabled, updatedAt, updatedBy }`.
  `PUT /admin/community/settings` body
  `{ preModerationEnabled, reason }` updates it and returns that projection.
  Access requires `community.manage` or `SUPER_ADMIN`; writes require CSRF. The
  singleton row defaults to `preModerationEnabled: true`; when false, submitting
  an owned draft publishes it immediately and records the publish action.
- `community.moderate` and `community.manage` are distinct permission codes.
  `SUPER_ADMIN` can use either capability. A `MODERATOR` role alone grants
  neither, and migrations do not bind either permission to a generic role.
  Migration 0103 adds reports/settings, report deduplication, comment moderation
  state, and expanded audit targets/actions; its downgrade removes only 0103
  objects/columns/permissions and restores the existing audit constraint.

## Backend published-work links and notifications contract (COM-006)

All paths below are under `/api/v1`. Community post create/edit accepts optional
`relatedWorkId` referencing an existing public work only when it is currently
published, public, not deleted, and has a published timestamp. A missing or
non-public work returns 404. Public feed/detail and owner write DTOs include
`relatedWork: { id, title, slug } | null`; every read rechecks current public
visibility, so hiding/archiving a work removes the link projection without
exposing dossier, certificate, owner, organization, or nomination fields.
Migration 0104 adds a nullable `related_work_id` reference with `SET NULL` and
an index.

Community engagement and moderation create only in-app notifications through
the existing `NotificationService`; the notification write shares the domain
transaction. Event types, recipients, and safe link payloads are:

- `COMMUNITY_COMMENT`: post author for a new root comment, unless they wrote it;
  data `{ actionPath: "/community/posts/{postSlug}" }`.
- `COMMUNITY_REPLY`: parent comment author for a new reply, unless they wrote
  it; action path uses the published post slug.
- `COMMUNITY_FOLLOW`: followed member for a new follow, unless self (self-follow
  is already rejected); action path uses the follower's public community
  username at `/community/members/{username}`.
- `COMMUNITY_POST_LIKED`: post author for a newly-created like, unless they
  wrote it; action path uses the public post slug.
- `COMMUNITY_POST_PUBLISHED` and `COMMUNITY_POST_REJECTED`: post author after an
  explicit moderator transition, unless the actor is the author. The former
  links to `/community/posts/{postSlug}` and the latter to `/community/new`.

Notification titles/bodies use community display names and public post titles
only. Data contains the relative `actionPath`; it never includes email, phone,
employment, dossier ids/content, moderation reasons, or nomination data. Each
notification uses its originating comment, relation, or moderation-event UUID
as `source_event_id`; the existing unique `(user_id, source_event_id)` constraint
deduplicates retries. Repeated idempotent like/follow requests do not create new
notifications. No email or push delivery is added.

## Community image attachment contract (COM-003 backend)

Uploads reuse the signed media API and inspection worker. The authenticated,
CSRF-protected `POST /api/v1/media/upload-signature` accepts
`{ purpose: "COMMUNITY_POST", filename, mimeType, size,
confidentiality: "PRIVATE" }`. `mimeType` must be `image/jpeg`, `image/png`, or
`image/webp`; `size` is 1–5,242,880 bytes. `POST /api/v1/media/complete` retains
its existing contract and metadata/signature checks. The asset stays
`QUARANTINED` until existing AV/content inspection marks it `ACTIVE`; clients
poll the owner-only `GET /api/v1/media/{mediaId}` status before attaching it.

Migration `0105_community_post_media` adds nullable `media_assets.purpose` and
does not backfill legacy assets. New upload intents persist their purpose;
legacy rows with `purpose IS NULL` never qualify for community posts. The
`community_post_media` relation stores `postId`, `mediaId`, and zero-based
`sortOrder`; each media asset can belong to at most one post, `(postId,
sortOrder)` is unique, order is non-negative, and the relation references
community posts and media assets with cascading post deletion and restricted
hard media deletion. Downgrade removes the relation and provenance column.

Post create/edit accepts optional `imageMediaIds: UUID[]` (at most five unique
ids, preserving request order; omission means no images / replaces the current
set). Each ID must identify a non-deleted asset owned by the post author, with
persisted purpose `COMMUNITY_POST`, status `ACTIVE`, non-null `inspectedAt`, an
allowed image MIME type, and size at most 5,242,880 bytes. Attachment changes
commit atomically with the post mutation. Public and owner post DTOs include
ordered `images: [{ id, url }]`; each URL is the relative app path
`/api/v1/community/posts/{slug}/media/{mediaId}`, never a provider URL.

`GET /api/v1/community/posts/{slug}/media/{mediaId}` returns the image bytes
with the stored safe image MIME type, `X-Content-Type-Options: nosniff`, and
`Cache-Control: private, no-store`. Anonymous delivery requires the exact
post/media relation, a currently `PUBLISHED` post with a published timestamp,
no deletion, an active category and author, and an active, inspected,
non-deleted `COMMUNITY_POST` image asset. An authenticated exact post owner may
preview an attached image while the post is `DRAFT`, `PENDING`, or `REJECTED`.
Missing, detached,
hidden, deleted, pending/rejected, quarantined, rejected, or deleted assets
return 404 to anonymous callers. Delivery proxies bytes through the app; no
raw Cloudinary/provider URL is returned.

## Backend tags, feed discovery, and owner reads (COM-009)

All paths below are under `/api/v1`; list responses use the standard
paginated success envelope. Existing community post DTOs gain
`tags: [{ id, name, slug }]`, ordered by `name` then `slug`. Create/edit accepts
`tags: string[]` of display labels (1–40 characters each, at most 10). The
server trims/collapses whitespace, rejects empty labels and duplicates after
case folding, and reuses or creates global tags with a normalized unique slug.
Omitting `tags` means an empty set on create and replaces the set on edit.
Feed filtering accepts one exact `tag=<slug>`.

`GET /community/posts` accepts `category=<categorySlug>`, `tag=<tagSlug>`,
`relatedWorkId=<publicWorkId>`, `q=<text>`,
`sort=recent|popular|discussed|following`, `page=1`, and `pageSize=20`.
`relatedWorkId` filters to a work that is currently published, public, and not
deleted; an unknown or non-public ID yields an empty page and reveals no work
fields. `q` is optional, trimmed, 1–120 characters, and performs a
case-insensitive literal substring search over title and content. `pageSize`
is capped at 50. `sort` defaults to `recent`; `following` requires an
authenticated principal and returns posts by members the viewer follows
(otherwise 401). Every feed mode returns only published, non-deleted posts in
active categories by active authors. `recent` orders `publishedAt DESC, id
DESC`; `popular` orders `likeCount DESC, publishedAt DESC, id DESC`; `discussed`
orders `commentCount DESC, publishedAt DESC, id DESC`; `following` uses recent
ordering. Category/tag/search filters compose with the selected sort. Counts
exclude hidden/deleted comments and inactive-user likes; optional viewer flags
remain personalized, so clients key cached feed results by viewer ID.

Authenticated owners manage their posts through
`GET /community/members/me/posts?status=DRAFT|PENDING|PUBLISHED|REJECTED&page=1&pageSize=20`
and `GET /community/members/me/posts/{postId}`. `status` is optional; when
omitted, the list includes all four statuses. These endpoints return the
existing owner `CommunityPostWriteData` projection, including tags, content,
moderation reason, category, related work, timestamps, and safe image paths.
The list sorts by `updatedAt DESC, id DESC`; page size is capped at 50. Reads
require the current authenticated principal. The detail endpoint returns 404
for posts not owned by the caller, deleted posts, or posts outside those four
statuses. Published items in this owner view are read-only; existing edit
service status rules remain unchanged. Public post, profile, and member-post
routes continue to expose only published posts. No response includes email,
phone, employment, or private account-profile fields.

An authenticated exact owner may preview attached community image bytes while
the post is `DRAFT`, `PENDING`, or `REJECTED`; no other viewer may retrieve
those bytes. Hidden/deleted posts and inactive, quarantined, rejected, or
detached assets remain unavailable, so a rejected post can be read and resumed
without making its media public.

Migration revision `0106_community_post_tags` adds the global tag table and
unique post/tag association with cascading post deletion and restricted tag
deletion; downgrade removes only these two community-owned tables.

## Community write limits and report-reason parity (COM-010)

Authenticated mutations use Redis counters keyed by a hash of the opaque
principal user ID; raw account IDs are never included in Redis keys. Community
content and admin writes use `community_write_rate_limit` attempts per
`community_write_rate_window_seconds` (default 30 per 60 seconds). Likes,
bookmarks, and follows use `community_engagement_write_rate_limit` per
`community_engagement_write_rate_window_seconds` (default 60 per 60 seconds).
Report submissions use the stricter `community_report_write_rate_limit` per
`community_report_write_rate_window_seconds` (default 5 per 3,600 seconds).
Successful writes and rejected requests count; reads are not rate limited here.
Limits run after session/CSRF validation and before mutation. Exceeded requests
return the standard error envelope with HTTP 429 and `retry_after_seconds`;
Redis unavailability fails closed with HTTP 503. Admin writes use the content
bucket, and no generic role bypasses limits.

Reports accept reasons `SPAM`, `HARASSMENT`, `HATE_SPEECH`, `MISINFORMATION`,
`COPYRIGHT`, `ADVERTISING`, `PRIVACY_VIOLATION`, and `OTHER`. The migration
updates the database check constraint; existing reasons and reports remain
valid. Downgrade maps the two new reason values to `OTHER` before restoring the
previous constraint.

## Community profile, comment likes, and view counts (COM-011)

All paths are under `/api/v1`. The existing public member projection stays
`{ id, username, displayName, avatarUrl, bio, joinedAt, publishedPostCount,
followerCount, followingCount, viewerIsFollowing }` and remains based only on
`community_profiles`. `PATCH /community/members/me` accepts a non-empty subset
of `{ username?, displayName?, avatarUrl?, avatarMediaId?, bio? }` and returns that projection.
It requires the current session and CSRF. Username edits are normalized to
lowercase, 3–30 characters (`a-z`, digits, `_`, `-`), case-insensitively unique,
and reject reserved route names; collisions return 409. For backwards
compatibility, an existing generated `member-<32 lowercase hex>` username is
accepted when a client submits it unchanged. `displayName` may be
null to restore the neutral fallback and otherwise is plain text up to 120
characters. `avatarUrl` remains available for legacy HTTPS profile values;
new community avatars use an owned, inspected `AVATAR` media asset referenced
by `avatarMediaId`. Its public URL is served only while attached to an active
community profile. `avatarMediaId: null` removes the attached avatar. `bio` may
be null or plain text up to 500 characters. No account,
employment, phone, or email fields are accepted or returned.

`GET /community/members/{username}/followers?page=1&pageSize=20` and
`GET /community/members/{username}/following?page=1&pageSize=20` are public,
paginated lists ordered by relation creation descending then relation ID
descending. They include active members only and return safe cards
`{ id, username, displayName, avatarUrl, viewerIsFollowing }`; the optional
principal controls only `viewerIsFollowing`, false for anonymous reads. Page
size is capped at 50. Missing/inactive profiles return 404. No private account
fields are returned.

`GET /community/posts/{postId}/comments` accepts `sort=oldest|newest`, default
`oldest` for compatibility. The selected order applies to both root threads
and each thread's replies; equal timestamps use comment ID as a stable tie
breaker. Thread pagination and `total` still count root comments only. Every
live root/reply comment DTO gains `likeCount` and `viewerHasLiked`; tombstones
always return zero and false. `PUT` and `DELETE /community/comments/{commentId}/like`
are idempotent and return `{ commentId, likeCount, isLiked }`. These writes
require session+CSRF and target only a live comment on a currently published
post; unavailable targets return 404. A unique `(commentId, userId)` relation
constraint prevents duplicate likes. Comment likes do not emit notifications.

Public post summaries/detail and owner post DTOs expose `viewCount`, a
persistent non-negative aggregate. `POST /community/posts/{postId}/views` has
no body and returns 204; it accepts anonymous callers and optional session,
and counts only posts that are currently public. Detail/feed reads do not
increment it. The endpoint reuses the signed HttpOnly visitor cookie, HMAC
visitor digest, Redis NX deduplication, 24-hour configurable TTL, and IP-based
engagement limiter. Each signed visitor counts at most once per post per TTL;
the counter increments only when Redis accepts the event. Clearing cookies or
distributed clients can still inflate counts, so this is an approximate
engagement signal, not a billing, ranking-integrity, or security metric. Redis
unavailability fails closed. Migration 0108 adds the comment-like relation and
non-negative post counter; downgrade removes only these additions.

### COM-012 moderation workspace and member restrictions (contract)

All routes are under `/api/v1/admin/community`. Post/comment workspace reads and
moderation actions require the explicit `community.moderate` permission or
`SUPER_ADMIN`; category/settings management retains `community.manage` or
`SUPER_ADMIN`. The generic `MODERATOR` role grants neither. Mutations require
session+CSRF and a bounded non-empty `reason`. Every mutation appends an
immutable moderation event containing target, action, reason, actor ID, safe
`actor:{id,username,displayName,avatarUrl}`, request ID, and timestamp. No DTO
returns email, phone, employment, or other private account fields.

`GET /posts?q=&status=&page=1&pageSize=20` provides a bounded searchable,
status-filtered workspace (`q` searches title, excerpt, and body; page size is
at most 50). It includes hidden and soft-deleted records for authorized review,
with the existing safe post DTO, safe author, `isPinned`, `commentsLocked`, and
deletion metadata. `POST /posts/{postId}/pin` and `/unpin` accept `{reason}` and
apply only to currently published, visible posts; attempts on hidden, deleted,
draft, pending, or rejected posts return 409.
`POST /posts/{postId}/comments/lock` and `/unlock` accept `{reason}` and return
`{postId,commentsLocked}`. A locked post rejects new comments/replies with 409;
existing reads and normal owner comment edits/deletes remain available. Locks
do not block editing or deleting existing comments.

The searchable moderator post workspace includes full post `content` for review.
`DELETE /posts/{postId}` with `{reason}` soft-deletes the post, records its
pre-delete status, and makes it unavailable in public feed/detail/media. `POST
/posts/{postId}/restore` with `{reason}` restores that status, including hidden
or unpublished states. Owner-deleted posts cannot be wrapped in an admin delete
or revived through admin restore. Invalid transitions return 409. `GET
/comments?q=&postId=&authorUsername=&visibility=VISIBLE|HIDDEN|DELETED|ALL&page=1&pageSize=20`
searches comment text and filters by post, public member username, and
visibility. Results include the stored comment text and safe community author
projection for moderator review, including hidden or deleted comments, plus
`{id,slug,title}` post preview. Public projections continue to mask deleted/hidden
text and authors. `POST /comments/{commentId}/hide`,
`/restore`, and `/delete` accept `{reason}`. Delete preserves the prior visible
or hidden state; restore reinstates that state. Public projections continue to
mask deleted/hidden text and authors and preserve thread structure. Admin
restore applies only to a moderator soft-delete and cannot revive a comment
deleted by its owner.

Migration rollback removes the COM012 restriction table and new post/comment
columns. It deliberately leaves the widened moderation-event CHECK constraints
in place: a deployment may already have COM012 audit actions, and narrowing
those checks would make existing audit rows invalid or require deleting them.

`POST /members/{memberId}/restrictions` accepts
`{scope:"POSTS"|"COMMENTS",durationMinutes,reason}`, with duration 1–525600.
The safe result is `{id,member:{id,username,displayName,avatarUrl},scope,status,
reason,startsAt,expiresAt,actor,requestId}`. Active `POSTS` restrictions reject
post creation, editing, and submission; owner post deletion remains allowed.
Active `COMMENTS` restrictions reject creating or editing comments/replies;
owner comment deletion remains allowed. Expiry uses database timestamps;
moderators can revoke early with
`DELETE /members/{memberId}/restrictions/{restrictionId}` and `{reason}`.
Expired/revoked records remain auditable and do not suspend login. Restriction
changes and all moderation transitions are appended to the immutable event log.

`GET /members?q=&page=1&pageSize=20` is the PII-free admin member finder. It
searches username/display name and returns safe member cards with published
post, follower, and following counts plus current active restriction summaries;
page size is at most 50. `GET /members/{memberId}/restrictions?page=1&pageSize=20`
returns that member's active, expired, and revoked restriction history ordered
newest first, with safe actor projections and request IDs. Both routes require
`community.moderate` or `SUPER_ADMIN`; opaque member IDs are only used by these
admin routes, never substituted for public username URLs.

All list routes return the standard `PaginatedSuccessEnvelope` with request ID,
page, page size, and total. Mutations return the standard `SuccessEnvelope`
with request ID and the following exact data:

- Post workspace item: existing `CommunityPostData` (including its safe
  `author`) plus full `content`, `status`, `isPinned`, `commentsLocked`, `deletedAt`, and
  `preDeleteStatus`. `POST /posts/{postId}/pin|unpin` returns
  `{postId,isPinned}`; `/comments/lock|unlock` returns
  `{postId,commentsLocked}`; `DELETE /posts/{postId}` and
  `POST /posts/{postId}/restore` return
  `{postId,isDeleted,deletedAt,restoredStatus}` (`restoredStatus` is null on
  delete).
- Comment workspace item: existing safe comment fields plus
  `visibility:"VISIBLE"|"HIDDEN"|"DELETED"` and `post:{id,slug,title}`.
  `POST /comments/{commentId}/hide|restore|delete` returns
  `{commentId,visibility}`.
- Member finder item:
  `{member:{id,username,displayName,avatarUrl},publishedPostCount,commentCount,
  followerCount,followingCount,lastActivityAt,activeRestrictions:[{id,scope,
  expiresAt}]}`. Restriction create, revoke, and history items all use
  `{id,member,scope,status,reason,startsAt,expiresAt,actor,requestId}`; history
  is paginated and each `actor` is the same safe community author projection.

## Deep replies, mentions, and draft autosave (COM-013)

Comments may reference any existing comment on the same post as `parentId`.
Reads page root comments, then load all descendants for those roots using a
recursive query. The response keeps replies flat under each root and preserves
their original `parentId`; clients can label the direct reply target without
nesting the full conversation. Comment totals include descendants.

The mention parser accepts case-insensitive `@username` handles and returns at
most 20 distinct usernames per item. Only active community profiles are
resolved. A comment mention notifies immediately; a post mention notifies only
when that post becomes published, including moderator approval. The author is
excluded, a mentioned reply target gets one mention event instead of a duplicate
generic reply event, and notification routes contain only the public post path.
The existing notification delivery layer redacts fragments and private data.

The post editor server-autosaves a valid draft after 1.2 seconds without input.
Title, content, and category must be present; incomplete forms are not persisted.
In-flight saves are coalesced, upload queues pause autosave, and save errors stay
visible with a manual retry path. The explicit Save Draft action remains.

Community image policy accepts inspected JPEG/PNG/WebP images. Backend settings
`COMMUNITY_POST_IMAGE_MAX_COUNT` and `COMMUNITY_POST_IMAGE_MAX_BYTES` default to
five images and 5 MiB each, bounded to 1–10 images and 1–20 MiB. Matching
`NEXT_PUBLIC_COMMUNITY_POST_IMAGE_MAX_COUNT` and
`NEXT_PUBLIC_COMMUNITY_POST_IMAGE_MAX_BYTES` values configure build-time browser
validation; backend validation is authoritative. Removing a transferred upload
from the pre-attachment queue calls the authenticated media delete endpoint.
Removing an image already attached to a saved draft detaches it but does not
delete its provider object.

## Guest access and community avatars (COM-015)

Unauthenticated visitors may read public feeds, categories, posts, and member
profiles. Participation and profile changes require the existing signed session
and CSRF dependencies; the public feed shows a read-only notice and directs
guests to sign in before writing.

`PATCH /community/members/me` may include `avatarMediaId`. A non-null ID must
refer to an active, inspected, private `AVATAR` asset owned by the current
member and within the configured avatar byte limit. Null clears the attachment.
Migration `0110_community_avatar_media` adds the nullable FK with
`ON DELETE SET NULL`. The existing safe author projection carries the
same-origin `/api/v1/community/avatars/{mediaId}` path.

The public avatar route serves JPEG/PNG/WebP only when the media remains
attached to an active community profile and its retained private asset checks
pass before and after reading. Upload selection reuses the shared signed upload
and inspection flow; removing or canceling an unattached upload requests its
deletion through the authenticated media API.
