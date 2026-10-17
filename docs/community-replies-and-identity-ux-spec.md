# Community replies and identity UX

## Goal

Make community identities and comment threads easier to scan on mobile, route
reply notifications to the discussion, and simplify the public home hero to show
the organization logo without crane or bronze-drum artwork.

## Decisions

- Keep the existing in-app `COMMUNITY_REPLY` notification event and route it to
  the comment section of its post.
- Show the moderator-facing community role as “Thẩm định viên”. This changes the
  label only, not permissions or authorization.
- Keep role badges separate from display names; comment authors do not show role
  badges.
- Remove crane and bronze-drum decorations from the public home hero; keep the
  logo asset and leave certificate artwork unchanged.
- Keep existing comment, edit, delete, like, report, reply, and pagination
  behavior.

## Acceptance criteria

- Reply notification links open the related post at its discussion section.
- A notification for a reply is still sent only to the replied-to author,
  without self-notifications.
- Account and post author identity layouts keep names readable and role badges
  on one line at narrow widths.
- Moderator role labels read “Thẩm định viên” in community surfaces.
- Comment and reply headers have a clear name/date hierarchy and remain free of
  role badges.
- The public home heritage visual contains only the logo.
- Focused backend and frontend tests cover notification routing and comment
  identity presentation.

## Implementation plan

1. Extend existing notification and component tests to describe the target
   behavior.
2. Route reply notifications to the post discussion section and improve comment
   thread presentation.
3. Update the moderator label and constrain responsive identity/badge layout.
4. Remove decorative crane/drum artwork from the public home hero while
   preserving the logo.
5. Run focused tests, type checking, and formatting checks; record a concise
   handoff.
