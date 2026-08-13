# Frontend

This root contains the Next.js App Router application. Server Components are the
default; Client Components are limited to interactive UI and browser APIs.

The source boundaries are:

```text
src/
  app/
  components/
  features/
  hooks/
  lib/
  services/
  types/
```

The application separates public discovery, applicant workflows and internal
operations while sharing one typed API client and a consistent design system.

Brand assets supplied for the project belong in `public/assets/brand/`. Use
stable kebab-case filenames so components do not depend on upload-generated
names.

## Local validation

```bash
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```
