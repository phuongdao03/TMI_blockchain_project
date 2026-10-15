# ADR-0007: Keep community discussions separate from official public works

## Status

Accepted

## Date

2026-10-15

## Context

The application publishes nomination/work records with established review, privacy, and publication controls. A community forum also needs user-written posts, comments, attachments, and moderation. Reusing CMS or public-work records would conflate official content with user discussion and inherit authorization policies that do not fit a forum.

## Decision

Implement a separate `community` bounded context with its own tables, API, moderation lifecycle, and public author profile. Reference a public work only through its stable identifier and resolve display data through the existing published-work read model. Reuse account sessions, notification persistence, and inspected media infrastructure through explicit adapters and permissions.

## Consequences

- Official nomination state and community post state remain independent.
- Public responses can guarantee that draft or moderated content does not leak into existing public APIs.
- Community needs its own moderation permissions, migrations, visibility checks, and media association policy.
- Notifications and media are reused without making their existing authorization policies implicitly public.
