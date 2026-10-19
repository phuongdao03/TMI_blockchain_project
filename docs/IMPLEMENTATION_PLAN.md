# Community implementation plan

Date: 2026-10-15. Community implementation and local release checks complete;
deployment remains separate.

## Phases and checkpoints

1. **Audit and contract** — confirm app boundaries, auth, database, media,
   routes, themes, current UX work; define module contract and test seams.
   **Complete.**
2. **Foundation** — permission model, schema/migration, default categories,
   repository/service/router, public category and paginated feed. Verify
   migration and public visibility.
3. **Posts** — drafts, submit/moderation states, editor, safe markdown, tags,
   inspected attachments, detail/SEO, `/cong-dong` redirect.
4. **Discussion and interactions** — threaded comments, likes, bookmarks,
   follows, saved/following feeds, member profiles, counts and notifications.
5. **Admin and nomination integration** — category/settings management, reports,
   moderation queue/logs/restrictions; link only published nominations and add
   discussion entry points to work details.
6. **Existing app UX refresh** — use the audit to order shell/design-token/theme
   and existing page improvements. Preserve current route/API/auth contracts;
   change each journey incrementally and verify light/dark/mobile/accessibility.
7. **Release readiness** — security, regression, performance, migration
   rollback, deployment notes, and handoff.

## Dependency graph

Permission/schema/migration → API contracts/services → public feed/post flows →
interactions/profile/notifications → admin/link integration → broad UX refresh →
release verification.

## Risks and mitigation

- **Private data leakage:** dedicated community profile/author DTO; test public
  responses against private account fields.
- **Moderator privilege mismatch:** add explicit community permissions; never
  infer authority from review-role names.
- **Public image exposure:** dedicated media purpose and association-aware
  delivery after scanning.
- **Moderation state leaks:** central visibility predicates shared by list,
  detail, search, sitemap, and media delivery.
- **Counter races:** use relation uniqueness and transactional aggregate/atomic
  updates.
- **Broad redesign regressions:** keep its phase after stable community vertical
  slices and use current audit evidence.

## Checkpoints

- After foundation: migration upgrade/downgrade, authorization, and feed API
  tests.
- After posts/discussion: backend feature tests and frontend behavior tests; no
  mocked production data.
- Before release: frontend lint/typecheck/build, backend focused/full tests,
  migration exercise, mobile/theme/accessibility checks, and nomination workflow
  regression.

## Current completion state

- Community foundation, posts, discussions, interactions, notification
  integration, nomination links, and admin workspaces are implemented locally.
  COM-013 adds arbitrary-depth replies, mention notifications, and controlled
  server draft autosave.
- The shared shell/navigation and new community journeys use the existing theme
  and responsive system. The broad existing-app refresh is partial: secondary
  HR, finance, publication, and settings journeys still need their own visual,
  accessibility, and device review.
- Final full-suite and production build results are recorded in `docs/TASKS.md`
  and `docs/handoffs/community-module.md`. Nothing has been deployed or migrated
  in production.
