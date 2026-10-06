# Cloudinary upload error logging

## Objective

When Cloudinary rejects a public video derivative upload with HTTP 400, the
worker log must show the provider's short error reason so operations can
diagnose the failure without an Advanced Cloudinary plan. The reason must not
expose credentials, private URLs, or source asset identifiers.

## Commands

- Focused test:
  `python -m pytest backend/app/tests/test_cloudinary_gateway.py -q`
- Lint:
  `python -m ruff check backend/app/modules/media/gateway.py backend/app/tests/test_cloudinary_gateway.py`

## Project structure and style

- `backend/app/modules/media/gateway.py` owns the Cloudinary HTTP boundary and
  uses structured `logger.warning` fields.
- `backend/app/tests/test_cloudinary_gateway.py` uses `httpx.MockTransport` to
  verify responses and captured logs without a network request.
- Keep the existing exception types and Celery retry behavior.

## Acceptance criteria

1. For upload HTTP 400, log a single-line `reason` from `X-Cld-Error` or the
   JSON `error.message`; if neither is usable, log `unknown`.
2. Redact credentials, URLs, private asset IDs, and sensitive named values;
   bound the logged text to 240 characters.
3. Preserve the existing status, operation, and error type fields and public
   `MediaProviderRejectedError` behavior.
4. Focused tests and lint pass before release.

## Boundaries

- Keep the provider message in server logs; do not return it to the browser.
- Do not log raw response bodies, upload data, signed URLs, or secrets.
- Release through the existing immutable image workflow; the production worker
  must run the new image before retrying the video to obtain a `reason`.
