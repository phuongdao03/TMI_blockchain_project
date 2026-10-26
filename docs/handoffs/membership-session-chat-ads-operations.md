# Membership, sessions, chat, and operations handoff

## Behavior

- Admin accounts do not have personal membership tiers or purchase flows. Their
  access to member rooms comes from admin permissions.
- Membership cards and identity badges use one palette per tier; admin identity
  is shown separately from member rank.
- Sessions expire after 30 minutes without user activity by default. Configure
  this with `AUTH_IDLE_TIMEOUT_SECONDS`; browser activity is synchronized across
  tabs and recorded by the API.
- Community chat history uses cursor pagination (50 messages by default, up to
  100 per page). Authors can edit or remove their messages; moderators can
  remove messages. Edits and removals are audited.
- The advertising setup shows a placement-specific page wireframe with the
  selected slot highlighted.
- Payment reconciliation still polls pending payments every minute. Routine
  successful polls are excluded from the default operator job list; failed
  reconciliation jobs remain visible and history can be queried by task name.

## Data and deployment

- Apply migrations `0141_membership_chat_history` and
  `0142_auth_session_idle_timeout` before deploying the API and frontend.
- Deploy the Celery worker and beat with the API so the scheduled reconciliation
  task continues to run.
- `AUTH_IDLE_TIMEOUT_SECONDS` defaults to `1800` and accepts 60–86400 seconds.

## Verification

- Root repository tests: 48 passed.
- Focused backend tests for sessions, membership, chat, migrations, job
  operations, and worker durability: 40 passed. The full backend suite was
  stopped at 32% without a reported failure.
- Formatting and Ruff checks passed after formatting four Python files.
- Frontend lint/typecheck could not run because local `frontend/node_modules`
  lacked the locked executables. Local mypy also stopped with an internal error
  from the installed mypy 2.3.0. GitHub Actions remains the full verification
  gate for the pushed revision.
