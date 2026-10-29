# Voucher system

The promotion module extends the existing FastAPI, SQLAlchemy, Next.js, wallet,
payment and notification modules. It does not create a second wallet.

## Access and ownership

- Recipients must be active accounts whose only role is `USER`, with no employee
  profile or internal administrative permissions. Eligibility is checked again
  during issuance and checkout.
- `promotions.manage` controls campaign/media/distribution mutations;
  `promotions.read` controls reporting. `SUPER_ADMIN` can do both.
- All user voucher reads and checkout operations are scoped to the account.
- Mutation endpoints use existing authentication and CSRF dependencies.

## Data and migrations

Apply normal Alembic upgrades through `0148` in a reviewed environment.

| Migration | Change |
| --- | --- |
| 0145 | Campaigns, account claims, initial early-member campaign |
| 0146 | Policies, lifecycle, immutable claim snapshots, presentation state, permissions; early-member campaign becomes DRAFT |
| 0147 | Reservations, refund/release adjustments, zero-net purchase support |
| 0148 | Media assets, distribution previews/jobs, expiry reminder deduplication |

`EARLY_MEMBER_2026` requires an explicit registration cutoff before publication.
The migration does not select a cutoff or issue production vouchers.
Normal membership purchases retain journal identifiers; a zero-net purchase has
an independent identifier and a nullable journal reference.

## User experience

Eligible users see the configured login offer outside payment and active form
flows. AUTO grants are persisted before presentation and survive dismissal.
`/vouchers` has available, locked, redeemed and expired tabs, code redemption,
and links to voucher details. The account overview includes an available-voucher
banner. Header avatars use the existing membership frame assets.

See [engine](PROMOTION_ENGINE.md), [operations](VOUCHER_ADMIN_GUIDE.md),
[payments](VOUCHER_PAYMENT_INTEGRATION.md) and [verification](VOUCHER_TEST_PLAN.md).
