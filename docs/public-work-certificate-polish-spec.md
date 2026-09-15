# Spec: Public work administration and certificate polish

## Objective

Make public-work preparation understandable and responsive for administrators,
and make the public certificate feel trustworthy, branded, and actionable.

## Commands

- Unit tests: `npm --prefix frontend test -- --run`
- Type check: `npm --prefix frontend run typecheck`
- Format check: `npm run format:check`
- Browser tests: `npm --prefix frontend run test:e2e`

## Project structure

- `frontend/src/components/admin/`: public-work editor and media state UI.
- `frontend/src/components/public/`: public certificate and verification UI.
- `frontend/src/lib/api/`: typed API contracts.
- `backend/app/modules/public/`: public-work data and taxonomy services.
- `backend/app/api/v1/`: public-work administration endpoints.

## Code style

Use the existing TypeScript, React Query, Tailwind, and accessible semantic HTML
patterns. Prefer localized state labels and mobile-first layouts. Do not add a
dependency or expose internal provider/worker details.

## Testing strategy

- Component tests cover inline tag creation, work-code labels, automatic media
  status refresh, localized states, certificate branding, and navigation.
- Backend tests cover the added dossier-code projection if the API contract must
  change.
- Typecheck and formatting remain release gates.

## Boundaries

- Always: preserve existing publication, certificate, and privacy behavior.
- Ask first: schema changes, new dependencies, or external service changes.
- Never: publish private evidence, fabricate certificate facts, or expose
  secrets.

## Success criteria

1. An administrator can create the first classification tag without leaving the
   editor and immediately assign it.
2. Pending/processing media refreshes automatically and displays a clear
   Vietnamese status instead of the raw enum.
3. The left list identifies each entry by its dossier/work code, with its title
   as supporting text.
4. The certificate uses the supplied Tinh Hoa Viet logo, a stable high-contrast
   burgundy/ivory/gold palette, a working QR image, and an action that navigates
   to an independent public record when available.
5. The editor and certificate remain usable at 320 px and at desktop widths.

## Implementation plan

1. Add regression tests for tag creation, media polling/state copy, and
   work-code presentation.
2. Extend the existing API projection only as needed to expose the dossier code;
   wire tag creation through the already-existing endpoint.
3. Add bounded media polling and improve status/retry affordances.
4. Add the supplied logo and redesign the certificate as one coherent document,
   then make its verification action meaningful.
5. Run focused tests, full frontend tests, typecheck, formatting, and browser
   checks at mobile and desktop breakpoints.
