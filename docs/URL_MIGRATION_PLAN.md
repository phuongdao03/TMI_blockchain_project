# Community URL migration plan

Date: 2026-10-15

## Canonical URLs

- `/community` — feed and filters
- `/community/categories/[slug]` — category feed
- `/community/posts/[slug]` — public post detail
- `/community/new` — authenticated editor
- `/community/saved` and `/community/following` — authenticated feeds
- `/community/members/[username]` — public member profile
- `/admin/community` — permission-gated moderation workspace
- `/api/v1/community/...` — versioned English API paths

## Compatibility

The requested Vietnamese entry `/cong-dong` redirects permanently to
`/community`. Do not rename existing `/works`, `/verify`, `/search`, account, or
admin routes. Community UI labels remain Vietnamese.

## SEO and privacy

Only `PUBLISHED` posts, visible categories, and public profiles receive
canonical metadata. Draft, pending, hidden, saved, following, editor, and admin
pages are `noindex`. Community post canonical URL uses its stable slug; profile
URLs use the unique username. Include community pages in sitemap only after
publication and remove them from sitemap on hide/delete. Never put private
profile fields in metadata or structured data.
