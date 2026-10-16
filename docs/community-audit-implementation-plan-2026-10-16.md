# Community audit implementation plan — 2026-10-16

## Scope

Implement the supplied Community hardening request against the existing Next.js/FastAPI module. Preserve existing auth, media, notification, ORM, and UI infrastructure. Leave unrelated working-tree changes untouched. Do not run production migrations or modify production data.

## Audit findings

| Area | Current behavior | Gap and action |
|---|---|---|
| Public identity | Community authors use `community_profiles`; account profile uses `user_profiles`. Public author DTOs expose only username, display name, and avatar URL. | Identity can diverge and author role is absent. Establish one public display-name/avatar source; derive admin/moderator labels only from persisted server roles; cover post, comment, member, and header identity. |
| Tags | Editor collects tags; feed/detail contracts project them. | Remove tag controls and visible tag UI for new and legacy posts while retaining stored records and API compatibility. |
| Owner deletion | `delete_post` changes status to `DELETED` and retains post content and interaction rows. Admin deletion is a separate reversible tombstone with audit and notification. | Permanently remove the owner post and dependent content, retain a content-free `OWNER_DELETED` event, and clean only media safely owned by the author. Keep moderation removal reversible. |
| Existing safeguards | Session-backed writes, CSRF, rate limits, immediate publish, drafts/autosave, safe Markdown, public visibility filters, inspected media, comment/post hearts, and moderation notifications already exist. | Keep these contracts; add focused regressions where changes touch them. |

## Ordered implementation slices

1. **Public identity contract — complete** — `user_profiles` is the canonical public identity source for display name and avatar; migration `0111_public_profile_identity` backfills existing Community values and has a tested downgrade. Public author/comment/member DTOs derive staff labels from persisted `Role`/`UserRole`; account headers use the shared profile query and invalidate Community caches after edits.
2. **Remove tags from the experience — complete** — editor, My Posts, post cards, Community feed filters, and Community URL state no longer expose tags. Legacy database/API tag data stays intact, and new frontend writes omit tags.
3. **Owner deletion and media cleanup — complete** — after explicit user approval, owner deletion hides the post, records one content-free `OWNER_DELETED` event, deletes only owned Community image assets, then transactionally removes the post, comments/replies, reactions, bookmarks, linked reports, prior moderation logs/events, and notifications. Foreign-owned and unrelated media remain. If provider cleanup fails, the post stays hidden and the owner can retry. Admin moderation deletion remains reversible and distinct.
4. **Focused UX and verification — complete** — identity, editor, feed, comments, and My Posts now use shared identity and theme-aware avatar components; focused tests and static checks are recorded in the handoff.
5. **Review and handoff — complete** — see `docs/handoffs/community-audit-hardening-2026-10.md` for implementation details, verification, migration deployment requirement, and the approved owner-deletion policy.

## Verification commands

- Frontend: `npm test -- --run <focused community and profile tests>`, `npm run typecheck`, `npm run lint`.
- Backend: `python -m pytest app/tests/test_community_api.py app/tests/test_user_profile_api.py app/tests/test_user_profiles.py app/tests/test_public_profile_identity_migration.py -q --tb=short`, plus Ruff check/format on touched modules.
- Build only after code changes; no production deploy or database migration execution in this task.

## Boundaries

- Never trust a client-supplied role or user ID.
- Do not drop legacy tag/profile data.
- Do not delete shared media or alter unrelated module behavior.
- Treat moderation removal as reversible and distinct from owner deletion.
- No production data or migration application is authorized by this local implementation task.
