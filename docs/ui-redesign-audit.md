# THV UI/UX Redesign Audit

## Scope

Audit of the current Next.js frontend for Đề cử Tinh Hoa Việt. Backend contracts, authentication, authorization, blockchain verification, database schema, and deployment behavior remain unchanged.

## Findings

### High priority

- Public pages change into the authenticated dashboard shell after sign-in. This breaks navigation continuity and forces users to return to the dashboard manually.
- Mobile dashboard navigation is hidden behind a disclosure menu. Frequent destinations are not always reachable with one hand.
- Light-mode contrast is inconsistent on several empty, error, and verification states.
- The visual language still mixes the previous dark/red certificate identity with the new THV identity.
- Navigation and headings sometimes describe internal roles or system structure instead of the user’s goal.

### Medium priority

- Large cards are repeated too often, reducing information density and hierarchy.
- Page titles and hero sections are oversized on wide screens and create unnecessary empty space.
- Active, disabled, loading, empty, success, and error states do not share one semantic system.
- Auth pages are visually heavy and expose more operational detail than users need.
- Mobile and desktop shells behave like separate products instead of responsive variants of one system.

### Low priority

- Some Vietnamese labels are inconsistent or overly technical.
- Focus, hover, and reduced-motion behavior need a single accessibility standard.
- Theme controls occupy too much header space and lack concise accessible labels.

## Product direction

- Public: discover the program, browse published content, verify public records.
- Participant: manage profile, follow saved content, receive updates, and later submit nominations when enabled.
- Operations: process assigned work through invitation-only internal accounts.

Public screens must not expose role codes, database details, API terminology, infrastructure, or internal workflow rules.

## Invariants

- No API, database, authentication, authorization, or blockchain contract changes.
- No mock production data.
- Public and private documents retain their current access rules.
- Feature availability remains controlled by the existing release gates.
