# Public mobile and video performance

## Production finding

On 2026-10-05 the public work `52504e0f-09d9-45f4-a167-d3ca710a8dbc`
returned a 3840 × 2160 MP4 through the public media proxy. The first
`Range: bytes=0-` response advertised 52,574,976 bytes, had `Cache-Control:
no-store`, and the work had no HLS URL. The player reported failure after six
seconds even while a slow MP4 was still loading. The light theme also recolored
the play and retry text to dark against the dark video surface.

## Changes

- Range responses for proxied video are limited to 2 MiB. Byte seeking and
  authorization checks remain in place; the original encrypted source still
  needs to be read before a cache miss can serve the first chunk.
- The player waits for slow MP4 files without declaring a timeout failure when
  no alternate stream exists. It shows a loading state and reserves retry for
  actual media errors.
- The periodic media job also detects older `READY` videos whose URL still
  points to `/api/v1/public/works/.../media/...` and generates a public,
  optimized derivative. The source-backed video stays visible during repair.
  If the provider fails, the source-backed video remains available and the job
  records a failure code instead of repeatedly retrying every 30 seconds.
- The public header shows the full brand name on phones. The install link moves
  into the phone menu, opaque sticky controls avoid unnecessary blur, and the
  public search page no longer shows backend request duration.

## Production check

After deployment, confirm `worker` and `scheduler` are healthy in the full
release profile. Reopen the work and check that its public API media entry
eventually has a `res.cloudinary.com` URL and a non-null `streamingUrl`. The
benefit of the optimized video depends on that derivative completing; a
provider failure keeps the slower source fallback available for review.

Focused backend tests, frontend unit tests, desktop/mobile public E2E, lint,
formatting, TypeScript and a production frontend build passed locally.
