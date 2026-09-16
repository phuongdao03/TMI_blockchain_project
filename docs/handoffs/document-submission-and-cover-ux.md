# Document submission and editorial covers

## Implemented

- Mobile-first three-step dossier guidance; preparation checklist, missing-evidence navigation and explicit upload-versus-submit instructions.
- Admin image cover sources: approved submitted images or dedicated JPEG/PNG/WebP upload (5 MiB, super admin only).
- Landscape cover preview and normalized position/zoom controls. Server crops to 1280 × 720 without modifying original bytes.
- Editorial uploads reuse the inspected asset, remain separate from signed dossier evidence, and follow existing publication authorization.
- Named cover fallback for works without an image; container-based responsive public work preview.
- Short-lived bounded in-memory cropped-cover cache; access checks run before cache lookup.

## Deployment

- Run existing deployment migration workflow through `0078_editorial_covers` before serving updated backend.
- No new environment variables or dependencies.
- No commit, push or deployment performed in this implementation turn.

## Verification

- 46 focused frontend component tests and 40 backend media/catalog tests passed.
- 8 CMS desktop/mobile Playwright tests passed using local mock API.
- Frontend TypeScript, targeted ESLint, backend Ruff and targeted Mypy passed.
- Live Cloudinary upload and production deployment not exercised locally.
