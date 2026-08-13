---
status: accepted
---

# Treat near-duplicate detection as a review signal

Exact canonical-content fingerprints remain the only automatic duplicate
rejection. Normalized-title similarity and perceptual image hashes may create a
private similarity-review case, but never label an asset fraudulent, copied or
authentic automatically. This favors explainability and false-positive safety
over opaque embeddings; embeddings require a later privacy, benchmark and cost
decision.

## Consequences

- Threshold equality creates a review case; below-threshold signals do not.
- Reviewer dispositions require a reason and are audited.
- Candidate images and scores remain internal and ownership-scoped.
- SHA-256 is used for exact bytes only, never for resized/recompressed-image
  similarity.
