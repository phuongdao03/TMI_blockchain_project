# Voucher payment integration

`PromotionCheckout` joins the caller's transaction and never independently commits
or invokes a payment provider. The server reads service prices; client values are
not authoritative. A reservation snapshots original, discount and payable values.

- Dossier payment orders permit voucher changes only while pending and before a
  provider checkout identifier exists.
- Membership purchases reserve, debit the net amount and redeem in one transaction.
  Fully discounted purchases create no zero-value wallet journal. Replay with a
  different voucher or payload is rejected.
- Advertising reservations use server package pricing and existing membership
  benefits. The policy selects the applicable benefit without accidental stacking.
- Provider confirmation, wallet settlement or verified manual settlement redeems;
  browser redirects do not. Duplicate confirmation is idempotent.
- Definitive cancellation/failure releases holds. A clock alone cannot release an
  ambiguous provider payment, because a late confirmation may still arrive.

Budget and claim changes use database row locks and transaction boundaries.
Append-only release/refund adjustments preserve reservation history. Partial refunds
reverse a proportional discount; the final refund reverses rounding remainder.
Restoration requires the snapshotted policy and an unexpired claim.

The refund adjustment helper is not a provider refund API. The existing payment
platform does not expose a confirmed-refund workflow here; a future verified refund
event must call it in the same business transaction. Do not call it from a browser
or use it as evidence that money has been returned.
