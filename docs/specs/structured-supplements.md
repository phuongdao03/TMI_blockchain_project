# Structured supplement requests

Extend the existing NEEDS_SUPPLEMENT transition, without a second dossier state
machine or extra fees. Requests are authored by an assigned, conflict-cleared
reviewer or administrator against the current frozen version and criterion. They
include a concrete issue/request, priority and optional explicit deadline. The
existing admin transition releases requests and sends its existing notice.

The applicant sees open requests only after that transition; answered/resolved
history remains visible later. Only the owner can respond, in NEEDS_SUPPLEMENT.
Responses are append-only. Revision checks prevent accidental overwrites.
Assigned staff can resolve or reopen with reasons; old responses remain intact.
No source is fetched, automatically verified, or made public.

Resubmission requires every released open request to be answered. New-policy
council approval requires resolution of every request for the dossier, including
requests on prior versions. All mutations lock the dossier before request rows.
No deadline or independent-review policy is invented.

Build sequence: real service tests -> additive migration -> authorized API ->
shared applicant/reviewer panel -> workflow guards -> regression and browser QA.
Run focused pytest, Vitest, lint, typecheck and migration roundtrip tests.
Rollback must refuse to remove populated request/response tables. No production
migration, live payment or deployment is authorized.
