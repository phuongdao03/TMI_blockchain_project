# Spec: Public membership pricing and navigation

## Objective

Make the public membership offer easy to find and complete enough to compare. Add a standalone **Hội viên** destination beside Cộng đồng and Quy trình. Keep the backend membership catalog as the source of paid plan names, prices, descriptions, benefits, and conditions.

## Requirements

- Keep the four approved levels: Đồng (Thành viên, free), Bạc (Kết nối, 490,000 VND/year), Vàng (Đồng hành, 1,490,000 VND/year), and Kim cương (Tinh hoa, 3,990,000 VND/year).
- Show the public pricing route at `/cong-dong/hoi-vien` from the primary public navigation and the mobile discovery menu.
- Show each plan's badge asset, name, annual price, fit, included rights, call to action, and conditions.
- Show inherited rights in the comparison view. Keep full comparison usable on mobile through the existing per-tier disclosure layout.
- Make the admin plan editor identify its benefit entries as the additions supplied by that tier.
- Preserve the eight approved FAQ topics and explain that Diamond requires approval before payment and is separate from Tinh Hoa Việt recognition.
- Do not copy paid plan prices or benefits into frontend fallbacks. If the API is unavailable, show a clear retry state instead of empty cards or a blank comparison section.
- Do not introduce scarcity claims or promise business outcomes.

## Boundaries

- Reuse `/cong-dong/hoi-vien` and the existing public shell.
- Do not change authentication, payment, or nomination review flows.
- Do not apply migrations to a configured database as part of this UI change.
- Membership catalog data remains controlled by backend/database and existing admin tools.

## Plan

1. Add the public Hội viên navigation item and a regression check for its route and active state.
2. Expand the seeded backend benefit copy to cover the approved rights and conditions for all four levels; keep the existing annual prices and plan names.
3. Render cumulative rights in the pricing comparison, keep the cards focused on each tier's own additions, clarify the admin plan editor, and give API error state an explicit comparison placeholder.
4. Run focused frontend and backend checks, inspect the changed route in the browser, and update the membership handoff.

## Acceptance criteria

- The desktop primary navigation includes Hội viên next to Cộng đồng and Quy trình; the mobile discovery menu points to the same route.
- The free-tier CTA opens registration; paid-tier CTAs lead to the membership workspace.
- Once the public catalog API is available, all four cards show the configured plan content and the comparison includes inherited benefits.
- Diamond terms and the distinction from nomination recognition remain visible.
- When the API is unavailable, the user sees a clear error and retry action, with no silently blank comparison area.
- Focused frontend and migration tests pass; no migration is applied to the user's configured database.

## Verification

- Frontend: `npm.cmd test -- src/components/layout/shells.test.tsx src/components/membership/membership-pricing-page.test.tsx src/components/membership/membership-admin-workspace.test.tsx`
- Backend: `pytest app/tests/test_membership_plan_benefits_migration.py`
- Browser: inspect `/cong-dong/hoi-vien` at desktop and mobile widths when the local backend catalog is available.
