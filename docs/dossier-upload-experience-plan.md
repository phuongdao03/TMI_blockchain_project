# Dossier upload experience plan

1. Add regression tests for provider-neutral copy, append selection, per-file
   removal, partial failure, and retry behavior.
2. Replace the single global upload state with a per-file queue while preserving
   the existing signed-upload contract.
3. Normalize upload failures into safe, actionable Vietnamese messages.
4. Redesign the uploader around a compact drop zone, visible queue, per-file
   controls, and persistent add/upload actions.
5. Add motion tokens and reduced-motion-safe status transitions.
6. Run focused tests, frontend quality checks, and real-browser desktop/mobile
   verification.
