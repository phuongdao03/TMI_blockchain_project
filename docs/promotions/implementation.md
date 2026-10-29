# Promotion management implementation contract

## Scope
Implement the supplied professional promotion-management master prompt on the
existing Next.js/FastAPI platform. Preserve the confirmed recipient restriction:
roles exclusively USER, no employee profile, active account. No cash conversion.
Existing payment, wallet and audit modules remain authoritative.

## Ordered work
1. Upgrade campaign policies, claim snapshots, audience rules and lifecycle;
   retain old claims. Seed early-member campaign as DRAFT with no invented cutoff.
2. Build campaign CRUD, presentation editor, audience preview/distribution, image
   library, reports and audit. Add separate Admin sections and step-based builder.
3. Add server quotes/reservations/redemption to dossier, membership and advertising
   purchase flows. Provider/wallet confirmation drives redemption, never redirect.
4. Integrate backend popup states, auto distribution and personal voucher tabs.
5. Run policy/API/concurrency/payment regressions and browser Admin/user tests.

## Shared data contract
VoucherCampaign retains id/code/title/description/terms/image_path/amount_vnd/
validity_days/active/starts_at/ends_at. Adds name, internal_description, status
(DRAFT/SCHEDULED/ACTIVE/PAUSED/ENDED/ARCHIVED), program_type
(AUTO/CLAIM/CODE/MANUAL/FIRST_ORDER), policy_version, policy_json, created_by,
created_at/updated_at, budget_reserved_vnd, budget_spent_vnd.

`PromotionPolicy` in promotions/schemas.py validates policy_json (camelCase wire):
- discountType FIXED/PERCENT, percentageBps (integer 0..10000), discountCapVnd,
  minimumOrderVnd, maximumOrderVnd, serviceCodes (DOSSIER_SUBMISSION,
  DOSSIER_APPROVAL, MEMBERSHIP, ADVERTISING), productIds, firstOrderOnly,
  subsequentOrderOnly, stackingPolicy NONE/BEST/MEMBERSHIP_FIRST,
  budgetVnd, issuanceLimit, redemptionLimit, usesPerVoucher, dailyLimit,
  userDiscountLimitVnd, fixedExpiresAt, allowUseAfterEnd, restoreOnRefund.
- audience: mode ALL/ANY, registeredBefore/registeredAfter, membershipTiers,
  userIds (UUID strings), purchaseHistory ANY/FIRST/RETURNING.
- presentation: template GIFT/PREMIUM/MINIMAL/LIMITED, theme CLASSIC/LIGHT/PREMIUM/MINIMAL,
  subtitle, primaryCta, secondaryCta, altText, imageAssetId, mobileImageAssetId,
  cardImageAssetId, thumbnailAssetId, imageFit contain/cover, focalX/focalY 0..100,
  backgroundColor/textColor/ctaColor (hex), borderRadius 0..32, overlay 0..0.8,
  trigger LOGIN/DASHBOARD/ISSUED/CHECKOUT/NOTIFICATION/BANNER,
  frequency ONCE/SESSION/LIMITED, maxViews, cooldownHours, enabled, notifyInApp.

VoucherClaim adds policy_json snapshot (same model dump using snake_case),
policy_version, status AVAILABLE/RESERVED/REDEEMED/REVOKED, unique_code,
valid_from, redeemed_at, uses_used, issue_reason. All new fields have defaults
for existing tests/fixtures. Existing amount_vnd holds maximum nominal discount;
percent discounts use percentageBps and cap from the snapshot.

Root provides `audience.py`: async `recipient_eligibility(session,user_id,policy)`
returns `(bool,reason)`; all issuance and checkout must enforce this restriction.
Root VoucherService provides `issue(user_id,campaign_id,reason="claim",commit=True)`
returning persistent VoucherClaim; commit=False integrates caller-owned transactions.

## API (existing SuccessEnvelope, /api/v1 prefix)
Admin: /admin/promotions, /admin/promotions/{id}, /{id}/{publish|pause|end|archive|copy},
/{id}/audience-preview, /{id}/issue, /{id}/distribution-jobs, /{id}/recipients,
/{id}/stats, /{id}/redemptions, /analytics, /audit, /services, /settings.
Campaign POST/PATCH body: code,name,internalDescription,title,description,terms,
imagePath,amountVnd,validityDays,startsAt,endsAt,programType,policy (above).
GET collection returns `{items,page,pageSize,total}`; detail has fields above plus
status,policyVersion,createdAt,updatedAt,budgetReservedVnd,budgetSpentVnd.
Audience preview POST `{userIds?:string[]}` returns eligibleCount,excludedCount,
nominalValueVnd,exclusionReasons,sample[{id,email,reason}],previewToken.
Issue POST `{userIds?:string[],reason,idempotencyKey,previewToken}` returns job.
Media GET/POST /admin/promotion-media; POST raw image bytes with query filename,
altText; response id,url,mimeType,width,height,size,altText. DELETE /{id} soft deletes.
Public image GET /promotion-media/{id}. Admin permission promotions.manage,
reporting promotions.read; SUPER_ADMIN compatible. All mutations CSRF protected.

User retain /vouchers/{offer,mine}, /vouchers/{campaignId}/claim; add /vouchers/redeem-code
POST {code}, GET /vouchers/{id}, POST /vouchers/{campaignId}/presentation
{event:SEEN/CLICKED/DISMISSED/OPT_OUT}. Offer returns offer plus policy presentation,
claimedVoucherId if automatically issued. No popup over payment/form/modal flows.

Checkout contract owned by payment implementation; existing session and endpoint
conventions, integer VND, source service price, no client amount authority.
Reservations hold budget atomically and follow actual provider order lifetime.

## Validation and boundaries
Use focused pytest/Vitest, typecheck, Ruff/ESLint and real Chrome desktop/mobile.
Critical: inactive/internal users, cutoff edges, unknown services, integer rounding,
concurrent issuance/reservation/budget, duplicate webhook, ambiguous provider state,
refund ledger adjustments, historical snapshots, malicious uploads and RBAC.
No new dependencies or production deployment required. No invented cutoff date.
Master matrix and final handoff must distinguish implemented/tested/pending work.
