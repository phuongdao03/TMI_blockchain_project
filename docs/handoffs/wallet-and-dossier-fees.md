# Wallet top-ups and dossier fees

## User flow

- Wallet top-ups return PayOS QR payload and transfer details to the app. The wallet page renders the QR image from the authenticated API and displays the amount, receiving account, transfer description, expiry, and status without opening the provider checkout tab.
- Pending top-ups can be resumed from wallet history. The owner-scoped QR endpoint returns `image/png` with private, no-store caching.
- `SUPER_ADMIN` cannot create, resume, or reconcile wallet top-ups. The wallet page also hides the top-up form for this role.
- Admin-issued dossier fees debit the dossier owner's wallet in the same transaction. A successful debit marks the order and dossier paid, records a wallet journal entry, notifies the owner, and enqueues certificate issuance. If funds are insufficient, the fee stays pending and the notification asks the owner to add funds and pay from the in-app wallet page.
- Billing obligation requests create wallet payment orders. They do not create PayOS checkout sessions; the owner pays from the in-app wallet flow.

## Main implementation points

- `backend/app/api/v1/wallet.py`: wallet top-up response fields, role guard, and QR image endpoint.
- `backend/app/modules/wallet/service.py`: owner-scoped provider QR/bank detail retrieval.
- `backend/app/modules/payments/service.py`: atomic fee debit and wallet-only obligation orders.
- `frontend/src/components/wallet/wallet-workspace.tsx`: in-page top-up details and admin messaging.
- `frontend/src/components/payments/dossier-payment-action.tsx`: directs the dossier owner to wallet payment.

## Verification

- Focused backend wallet, payment, and billing tests pass.
- Python mypy passes for all 453 backend source files.
- Frontend tests could not run in the local checkout because the frontend `vitest` executable is unavailable; Prettier check passes for the changed frontend files.
