# Affiliate Attribution Policy

## Status

Attribution is not implemented. This document records the decisions that must
be approved before tracking or commission processing is enabled. The configured
`AFFILIATE_ATTRIBUTION_WINDOW_DAYS` default is 30, but no current code reads
clicks or applies that value.

## Decisions required before launch

| Decision | Current status | Required decision |
|---|---|---|
| Attribution model | Unset | Approve first-touch or last eligible touch; store the selected result once |
| Window | Config default: 30 days | Approve the duration and whether it ends at registration, first paid service, or both |
| Eligible referral | Not implemented | Define which new/returning customer accounts qualify |
| Service conversion | Not implemented | Enumerate service types and qualifying final paid state |
| Self-referral | Not implemented | Reject same-user, shared-identity, and other prohibited relationships using an approved method |
| Multiple devices/codes | Not implemented | Define deterministic conflict resolution and audit evidence |
| Privacy and consent | Not implemented | Approve cookie/storage purpose, notice, retention, and opt-out behavior |

## Minimum target invariants

- A referral code is unique, stable, and resolved by the server.
- A click is a tracking event only; it does not create a commission.
- The server records the selected affiliate and attribution time before a
  qualifying conversion can be credited.
- A user cannot receive commission for their own service purchase. Accounts
  with excluded roles or privileged permissions cannot earn commissions.
- One eligible conversion can create at most one direct commission.
- Attribution changes after conversion require a reasoned, audited correction;
  they do not overwrite history silently.
- Store only the identifiers and timing needed for the approved purpose. Keep
  raw network/client signals out of URLs and routine application logs.

## Activation conditions

The policy owner must fill the decision table, privacy/legal review must approve
tracking and retention, and tests must cover expiry, duplicate clicks,
conflicting codes, self-referral, excluded roles, cross-device handling, and
idempotent conversion processing. Until then, referral tracking and commissions
remain disabled.
