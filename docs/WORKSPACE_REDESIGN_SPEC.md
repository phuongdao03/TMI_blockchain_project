# Workspace screen redesign

Date: 2026-10-15

## Objective

Give staff a consistent, readable workspace across HR, finance, publication, and account settings. Keep existing tasks easy to scan on desktop and mobile while using the app's current THV light/dark theme tokens.

## Scope

- HR: employee and department management, attendance setup and review, leave and overtime review, payroll, and employee self-service attendance/leave/overtime.
- Finance: administrator payment-fee decisions at `/admin/payments`.
- Publication: content management at `/admin/content` and public-work editing at `/admin/publications/[id]`.
- Settings: personal profile and organization settings at `/account`.

## Constraints

- Preserve route paths, API contracts, authorization gates, form validation, workflow states, confirmations, and mutations.
- Use the current Tailwind 4, Lucide, and semantic theme variables; add no dependencies or new theme palette.
- Keep visible labels, keyboard access, focus treatment, and responsive layouts.

## Design direction

- Use one compact, editorial page header with a clear section label, one page title, a short task-oriented description, and an optional action.
- Replace legacy fixed white/gray workspace surfaces with the active semantic theme.
- Keep distinct sections separated by spacing and fine borders; reserve contained panels for forms, lists, and status context.
- Use a split settings layout on wide screens and a horizontal section selector on narrow screens.

## Implementation plan

1. Add a reusable workspace page header and a scoped compatibility layer for existing neutral utility classes.
2. Apply the shared presentation to HR self-service and administrative workspaces without touching workflow code.
3. Apply it to finance and publication workspaces, then reshape account settings navigation for desktop and mobile.
4. Review the focused diffs and run related UI tests, lint, typecheck, and production build where available.

## Acceptance criteria

- All listed routes use semantic colors and the shared page-heading hierarchy in both themes.
- Existing actions, filters, forms, and authorization remain intact.
- At narrow widths, controls wrap or scroll intentionally and the page has no added horizontal overflow.
- Focusable controls retain visible focus, and screen-reader relationships for titles/tabs remain valid.
- Relevant component tests, lint, typecheck, and build complete successfully.

## Stack and verification commands

- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Vitest.
- `npm test -- --run <focused test files>`
- `npm run lint`
- `npm run typecheck`
- `npm run build`

## Open questions

None for this presentation-only scope. Product workflows and routes already exist.
