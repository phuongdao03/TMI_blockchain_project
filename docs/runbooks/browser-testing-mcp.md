# Browser testing with Chrome DevTools MCP

## Installed configuration

Chrome DevTools MCP is installed globally for Codex as `chrome-devtools`:

```text
npx -y chrome-devtools-mcp@latest --isolated --no-usage-statistics --no-performance-crux
```

Restart Codex/IDE after installation. Google Chrome Stable is installed on the
workstation. The MCP server itself does not require database, OAuth, payment,
or blockchain credentials.

Do not attach a personal or production Chrome profile to MCP. Use the isolated
MCP profile or the local mock-auth E2E environment. Browser content is exposed
to the agent while DevTools MCP is connected.

## Local test modes

1. **Frontend-only:** `npm --prefix frontend run lint`, `typecheck`, `test`, and
   `build`. No secrets required.
2. **Mock E2E:** `npm --prefix frontend run test:e2e -- --project=desktop-chrome`.
   The Playwright fixture starts the mock auth/API server on port `4010` and
   Next.js on `3100`; no real credentials are used.
3. **Integrated local stack:** copy `.env.example` to `.env`, start Postgres,
   Redis, Anvil, backend, and frontend, then use seeded test accounts only.

## Values needed before integrated testing

### Required for backend/auth

- `DATABASE_URL` and `DATABASE_DIRECT_URL`
- `JWT_SECRET` and `AUTH_CSRF_SECRET`
- `AUTH_OUTBOX_ENCRYPTION_KEY` and `PII_ENCRYPTION_KEY`
- `ENGAGEMENT_VISITOR_HMAC_SECRET`
- `REDIS_URL`

### Google OAuth

- `FIREBASE_PROJECT_ID`
- `NEXT_PUBLIC_FIREBASE_API_KEY`
- `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
- `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
- Authorized JavaScript origin for the frontend URL
- Authorized redirect URI for the backend callback URL

### Media, email, and payments

- Cloudinary: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`,
  `CLOUDINARY_API_SECRET`
- SMTP/provider: `SMTP_HOST`, `SMTP_PORT`, `SMTP_SENDER`, and provider API key
  when applicable
- Payment gateway: `PAYMENT_PROVIDER`, `PAYMENT_WEBHOOK_SECRET`, and the
  provider checkout/webhook endpoint

### Blockchain

- `BLOCKCHAIN_NETWORK`, matching `BLOCKCHAIN_CHAIN_ID`
- HTTPS `BLOCKCHAIN_RPC_URL`
- `CERTIFICATE_CONTRACT_ADDRESS`
- `BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES` containing the exact contract
- `BLOCKCHAIN_SIGNER_PRIVATE_KEY` (production only; never commit or expose it)
- `BLOCKCHAIN_EXPLORER_BASE_URL`

Provide secrets through the local environment/secret manager, not in chat,
screenshots, test fixtures, or MCP configuration.

## Test evidence to capture

- Console errors/warnings: zero expected.
- Network: public routes must not call protected APIs; auth failures must be
  intentional and handled.
- Accessibility tree: named controls, heading order, keyboard focus, contrast.
- Screenshots at desktop and mobile breakpoints.
- Performance trace for landing, catalog, search, dossier workspace, and
  certificate detail.
