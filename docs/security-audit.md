# Security Audit — THV / Tinh Hoa Việt

## Scope and evidence

Reviewed the FastAPI authorization, staff-account, media, document-proof, and
configuration paths, their focused tests, and the current working tree on
2026-08-23. This is a source-and-test audit; production provider configuration
and live infrastructure were not available for verification.

## Status

| Area | Classification | Evidence |
| --- | --- | --- |
| Server-side authorization | IMPLEMENTED | Permission policy, ownership checks, and authorization tests are present. |
| Staff invitation and MFA lifecycle | IMPLEMENTED | Staff account service and dedicated migrations/tests are present. |
| Private document controls | IMPLEMENTED | Media encryption, signed access, document-hash claims, and runbooks are present. |
| Dynamic dossier access scopes | IMPLEMENTED | Versioned dossier type, evidence visibility/access scope, review persistence, migration and focused tests are present. |
| Production secret and provider configuration | NOT VERIFIED | Requires approved production environment evidence; no secrets were inspected. |

## Findings

### Resolved — dynamic dossier persistence slice

`DossierType`, `DossierTypeVersion`, dynamic form data, scoped evidence and
review fields are implemented through models, repositories, services, API
boundaries and migrations `0054`/`0055`. The API lists only active type versions
for applicant dossier creation, while type authoring remains behind the
`cms.manage` capability. The local browser suite verifies type selection and
draft creation; production authorization must still be exercised in staging.

### Remaining — release-environment evidence

The local frontend unit suite is green (76 files / 222 tests), but a production
security decision still requires CI evidence, real provider configuration,
authorized-domain verification, backups and monitoring. Presentation gates are
not authorization controls.

## Required remediation order

1. Run ownership/role/IDOR API tests for dynamic dossier fields and evidence
   visibility against the staging database.
2. Verify least-privilege staff capabilities and MFA in the real identity
   provider.
3. Run the full CI and browser release gates before deployment.
