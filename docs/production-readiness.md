# Production Readiness — THV / Tinh Hoa Việt

## Current decision

**READY FOR PRODUCTION REVIEW (local code and test gates).** This is not an
authorization to deploy: production infrastructure, credentials and provider
configuration still need a separate approved staging/production review.

## Evidence-based blockers

| Severity | Area | Finding |
| --- | --- | --- |
| Resolved | Dynamic dossier domain | Versioned types, schemas, migration `0054`, seeded default catalog migration `0055`, API and service validation are present. |
| Resolved | Local dossier UX | The applicant can select one of 12 server-supplied dossier types, load the matching dynamic fields and create a draft. |
| Resolved | Brand and accessibility | The browser icon uses the THV emblem; selected light/dark dashboard and dossier form controls use semantic theme tokens. |
| Remaining | Deployment evidence | DNS, TLS, Firebase authorized domains, provider credentials, backups, monitoring and live readiness remain unverified. |

## Checks run

- Backend dynamic dossier migration/service tests: passed, including the
  reversible default catalog seed.
- Frontend unit tests: 76 files / 224 tests passed.
- Frontend typecheck: passed.
- Local browser regression tests: dossier type selection/draft creation and
  light/dark contrast passed.
- `npm.ps1` is blocked by local PowerShell execution policy; `npm.cmd` is the
  usable local command form.

## Required release sequence

1. Run the full backend test, lint and type gates in CI.
2. Apply migrations through `0055_seed_default_dossier_types` in staging and
   verify the 12 type catalog against the real API.
3. Run format, lint, typecheck, unit/API, browser/E2E and document-proof gates
   in the release environment.
4. Obtain separate approval and evidence for staging/production configuration.
