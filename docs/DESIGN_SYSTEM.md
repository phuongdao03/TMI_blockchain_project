# Design system guidance for the community module

Date: 2026-10-15

## Existing system to reuse

The app already defines THV red and gold brand colors, semantic theme variables,
spacing/radius/motion tokens, and `data-theme="light|dark"` support in
`frontend/src/app/globals.css`. Community components must use existing
`--theme-bg`, `--theme-surface`, `--theme-text`, `--theme-muted`,
`--theme-border`, and brand tokens. Do not add hard-coded theme colors or a
second token system.

## Community composition

- Follow the existing public shell, header, content width, button, form, dialog,
  and loading primitives.
- Use one editorial feed column with light separators; reserve cards for
  distinct nomination embeds or moderation states.
- Keep titles and author metadata scannable. Show category/tag, publication
  status, and community-authored labels as text, not color alone.
- On mobile, use a single column, compact filter controls, comfortable touch
  targets, and no horizontal overflow.
- Support keyboard operation, visible focus, labeled icon buttons, reduced
  motion, and loading/error/empty states.

## Theme and responsive verification

Validate light and dark themes at 360, 768, and 1440 CSS pixels. Check text
contrast, focus visibility, filter wrapping, long usernames/titles, image aspect
ratios, and dialog focus return. Do not redesign unrelated routes as part of a
community component change.
