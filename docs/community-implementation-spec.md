# Community Authentication and Publishing

## Objective

Use the platform's existing backend session for community identity across public
and dashboard routes. Publish new posts immediately, retain safe
post-publication moderation, and make the community feed compact and usable on
mobile. Preserve legacy pending rows without publishing or deleting them.

## Tech Stack and Structure

- Next.js 16 App Router, React 19, TanStack Query, TypeScript, Tailwind/CSS
  tokens.
- FastAPI, SQLAlchemy async sessions, PostgreSQL-compatible models, Alembic,
  existing notifications.
- Frontend community: `frontend/src/app/(public)/community` and
  `frontend/src/components/community`.
- Backend community: `backend/app/api/v1/community*.py` and
  `backend/app/modules/community`.

## Commands

- Frontend focused tests:
  `npm test -- --run src/components/community src/components/layout/shells.test.tsx`
- Frontend checks: `npm run typecheck`, `npm run lint`, `npm run build`
- Backend focused tests:
  `python -m pytest app/tests/test_community_api.py app/tests/test_community_admin_api.py`
- Backend lint: `ruff check app/modules/community app/api/v1/community.py`

## Code Style

Use the backend session and principal as the authority; frontend state is a
presentation of that session:

```tsx
const user = useAuthUser();
const authStatus = useAuthStatus();
if (authStatus === "loading") return <CommunityLoadingState />;
```

Keep UI colors on `--theme-*` tokens, validate all writes in the backend, and
preserve the existing API envelope and service/repository boundaries.

## Testing Strategy

- Frontend unit tests for public auth propagation, safe login destinations,
  publish success, mobile navigation priority, and compact feed controls.
- Backend API/service tests for immediate publication, ownership checks, removal
  reason, moderation log, author notification, and public invisibility after
  removal.
- Run focused tests plus typecheck, lint, and production build; report any
  environment-blocked checks.

## Boundaries

- Always: use the existing session, enforce backend authorization, retain
  soft-deleted/legacy content, keep login returns local, and keep removal plus
  notification in one transaction.
- Ask first: destructive data migration, new dependency, or schema migration
  affecting existing rows.
- Never: create a second account system, trust client-supplied identity,
  auto-publish legacy pending posts, or expose moderation data through public
  APIs.

## Success Criteria

- A valid platform session and role reach the community feed as authenticated;
  unresolved session checks show loading/error instead of guest messaging.
- Login from community returns to a validated local destination.
- New submissions become `PUBLISHED` regardless of old pre-moderation settings
  and open their detail page.
- Admins can remove a published post with a required reason; a moderation event
  and author notification commit with the removal; public reads no longer return
  it.
- Dashboard mobile quick navigation exposes `/community` with the correct active
  state.
- Feed filters remain usable without horizontal overflow and reduce mobile
  vertical space in both themes.
- Existing pending rows remain untouched and are not newly created by the
  publish flow.

## Implementation Plan

1. **Shared auth** — propagate the server session through the public shell;
   resolve refresh-only sessions in the shared query; add auth loading/error
   states and safe local return validation.
2. **Navigation and feed** — prioritize community in mobile quick navigation;
   combine search/category/sort controls and compact the header and empty state.
3. **Immediate publishing** — force new submissions to `PUBLISHED`, remove
   approval controls from admin navigation/settings, allow owners to edit
   published posts, and redirect successful submits to detail.
4. **Post-moderation** — notify post authors transactionally when a moderator
   hides a post, retaining moderation history and existing soft-hide/restore
   behavior.
5. **Verification and handoff** — update focused tests, run frontend/backend
   checks, and document remaining legacy pending data behavior.

## Root Cause

`(public)/layout.tsx` fetched the authenticated user and passed it only as a
prop to `PublicShell`. `CommunityFeed` instead read `useAuthUser()`, whose
provider existed only under `DashboardAuthGuard`; it therefore saw `null` on
public community routes even when the backend session was valid. A
refresh-cookie-only session also had no public client-side revalidation path.
