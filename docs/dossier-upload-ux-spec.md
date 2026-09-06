# Spec: Simplified dossier upload experience

## Objective

Make profile and dossier preparation easier for Vietnamese applicants: accept
familiar local phone numbers, support practical video evidence, and emphasize
the next action instead of presenting every workflow detail with equal visual
weight.

## Commands

- Frontend tests: `npm --prefix frontend test -- --run`
- Backend tests: `python -m pytest backend/app/tests`
- Formatting: `npm run format:check`
- Types: `npm --prefix frontend run typecheck`

## Project structure

- `frontend/src/components/account`: profile input and presentation
- `frontend/src/components/media`: reusable secure upload experience
- `frontend/src/components/dossiers`: applicant dossier workspace
- `backend/app/modules/users`: authoritative phone validation and normalization
- `backend/app/modules/media`: authoritative upload authorization limits
- `backend/alembic/versions`: persisted dossier document policies
- `infrastructure/nginx`: request-size boundary for VPS deployments

## Code style

Use existing semantic design tokens and accessible native controls. Keep
validation at the browser and API boundaries; preserve the existing API
representation (`+84...`).

## Testing strategy

- Unit tests prove local Vietnamese phone input is normalized to `+84...`.
- API tests prove both local and existing international input remain compatible.
- Upload tests prove the evidence fallback policy is 100 MB.
- Component tests prove the uploader exposes concise instructions and status.
- Migration and nginx tests prove production limits match the application
  contract.

## Boundaries

- Always: retain MIME restrictions, server authorization, malware inspection and
  access checks.
- Ask first: limits above 100 MB or a change to supported media types.
- Never: trust browser-only validation or expose upload-provider credentials.

## Success criteria

- A Vietnamese number such as `0901234567` saves without an error and remains
  familiar in the UI.
- The API normalizes that number to `+84901234567` without breaking existing
  E.164 clients.
- Video-capable evidence rules and global evidence authorization allow up to 100
  MB.
- The dossier page clearly identifies the current state, next action and three
  completion steps.
- The evidence uploader explains select/upload/verification and gives clear file
  feedback.
