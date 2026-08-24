# THV Brand Refresh Specification

## Objective

Apply the approved red-and-gold identity of **Trung tâm Đề cử Tinh Hoa Việt** across the existing THV product without changing business logic, RBAC, dossier, QR, upload, certificate, or blockchain flows.

## Approved sources

- `ChatGPT Image Aug 22, 2026, 11_44_01 AM.png`: official emblem.
- `ChatGPT Image Aug 24, 2026, 08_54_19 AM.png`: official gold wordmark.

## Brand tokens

| Token | Value | Use |
| --- | --- | --- |
| `--thv-red` | `#9D0000` | primary actions and links |
| `--thv-red-dark` | `#650000` | header, sidebar, footer |
| `--thv-red-deep` | `#470000` | dark feature surfaces |
| `--thv-red-light` | `#B51212` | hover and active |
| `--thv-gold` | `#F6C515` | logo and verification accents |
| `--thv-gold-light` | `#FFD83D` | restrained highlight |
| `--thv-gold-dark` | `#D49A00` | gold borders and hover |
| `--thv-bg-warm` | `#FFF9F3` | light canvas |
| `--thv-text` | `#241515` | primary light-mode text |
| `--thv-text-secondary` | `#6B5656` | secondary light-mode text |
| `--thv-border` | `#EAD9D3` | light-mode dividers |

Semantic success, warning, error and information colors remain distinct from brand colors.

## Acceptance criteria

- Official emblem and wordmark are used in header, dashboard, authentication, favicon, and branding component variants.
- Public header, footer, primary and secondary controls use the red/gold system in both themes.
- Applicant and operations shells use the same tokens while preserving readable, neutral data surfaces.
- Public, verification, and QR surfaces use branded accents without compromising QR scan contrast.
- The old olive-green identity is removed from global theme tokens and product-shell styling.
- Responsive checks pass at 320, 375, 768, 1024 and 1440 pixels.
- Lint, typecheck, targeted tests and production build pass.

## Boundaries

- Always: use semantic tokens; retain WCAG-aware contrast; retain all existing routes and behaviour.
- Ask first: schema, API, dependency, CI, and deployment changes.
- Never: alter business rules, payment, blockchain signing, RBAC, or status semantics as part of branding.
