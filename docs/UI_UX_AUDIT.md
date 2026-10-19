# UI/UX audit: Tinh Hoa Việt community

Date: 2026-10-15. Static source and repository-document audit; the live host
could not be fetched by the available browser search tool.

## Existing foundation

- Public pages use the shared `PublicExperienceShell` / `PublicShell` and
  central header navigation.
- The global stylesheet defines THV red/gold brand colors, semantic light/dark
  tokens, spacing, radius, and motion variables. Public routes already use a
  mobile-aware shell and theme toggle.
- Existing public discovery routes are `/works`, `/works/[slug]`, `/search`,
  `/verify`, `/process`, and `/guide`.
- Authentication and API requests use shared session state and the typed API
  client. Public reads can remain shareable; writing must require a signed-in
  user.
- The repository includes prior redesign and mobile performance evidence in
  `docs/thv-system-ux-redesign-2026-10.md`,
  `docs/mobile-performance-audit-2026-10.md`, and related handoffs. Preserve
  their tested route, focus, and mobile-navigation behavior.

## Community integration results and gaps

- The community feed, post detail, editor, member profile, saved posts,
  moderation workspaces, SEO routes, and primary navigation entry now exist and
  reuse the public shell. `/cong-dong` redirects to `/community`.
- No public handle/bio model exists. Existing account profile data contains
  private contact and employment fields and must not be used as a public author
  DTO.
- Existing CMS posts are editorial content; existing reports apply to published
  works. Neither is a forum model.
- Existing media processing is secure but purpose-scoped; community images need
  an explicit association and delivery rule.
- Existing moderator permissions are scoped to review workflows. Community
  moderation needs explicit authorization rather than assuming the global
  `MODERATOR` role grants it.

## Direction

Use a three-column desktop reading layout only where space allows: compact topic
rail, broad continuous post list, and one optional sidebar. On tablet/mobile,
collapse rails into accessible controls and keep one content column. Use
typography and separators in place of repeated cards. Reuse THV colors and
semantic tokens; do not introduce a second theme or change global styles without
measured evidence.

The new community journeys were implemented against the shared shell and theme
tokens, with mobile layout and light/dark behavior covered by component and
route tests. Existing nomination detail pages include published-work
discussions. A local backend service was unavailable during browser review, so
end-to-end API behavior still needs staging validation.

The broad redesign of existing pages is only partially complete. Prior evidence
is summarized in `docs/thv-system-ux-redesign-2026-10.md` and
`docs/mobile-performance-audit-2026-10.md`; the remaining HR, finance,
publication, and settings journeys still need route-by-route visual,
accessibility, and physical-device review. Do not report the sitewide redesign
as complete until that audit is done.
