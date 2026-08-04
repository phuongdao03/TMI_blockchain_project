# Frontend

This root contains the Next.js App Router application. Server Components are the
default; Client Components are limited to interactive UI and browser APIs.

The planned source boundaries are:

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

TASK-0005 initializes the frontend runtime, red identity design tokens, base UI
primitives, and public/auth/dashboard layout shells.

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
