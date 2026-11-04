# 001 — Preserve reduced-motion feedback and mobile press response

- **Status**: DONE
- **Commit**: `1b99685`
- **Severity**: MEDIUM
- **Category**: Accessibility / interaction feedback
- **Estimated scope**: 3 files, small

## Problem

The coarse-pointer public control press state scales to 0.985 and is active
regardless of reduced-motion preference. A later reduced-motion rule then
removes all transition feedback from public buttons and menu links. The home
stylesheet also removes every transition from editorial content and the media
dialog.

```css
/* frontend/src/app/globals.css:11651 — current */
@media (hover: none) and (pointer: coarse) {
  .public-shell :is(.registry-button, .catalog-work-card__link,
    .public-mobile-nav__link, .public-header__menu):active {
    transform: scale(0.985);
  }
}
/* frontend/src/app/globals.css:11662 — current */
@media (prefers-reduced-motion: reduce) {
  .public-shell :is(.registry-button, .catalog-work-card__link,
    .public-mobile-nav__link), .public-header__menu { transition: none; }
}
```

`frontend/src/components/public/home-editorial.css:756` also sets
`transition: none !important` for every descendant of `.home-editorial` and
`.public-media-dialog`.

## Target

- Apply the coarse-pointer scale only under
  `(hover: none) and (pointer: coarse) and (prefers-reduced-motion: no-preference)`.
- Press scale: `0.96`; duration: `150ms`; easing: `ease-out`.
- Enter the mobile navigation drawer from `translateX(12px)` and opacity 0 to
  its natural position and opacity 1 over `180ms var(--ease-standard)`; fade
  the backdrop over `150ms ease-out`.
- Under reduced motion, preserve only `color`, `background-color`, `border-color`,
  and `opacity` feedback at `120ms ease-out`; do not transition transforms.
- Keep the current focus-visible treatment and selected navigation appearance.

## Repo conventions to follow

- Existing timing tokens are `--motion-fast: 160ms` and
  `--ease-standard: cubic-bezier(0.2, 0, 0, 1)` in
  `frontend/src/app/globals.css`.
- Match the existing public shell selector in `frontend/src/app/globals.css`
  and mobile drawer owner in `frontend/src/components/layout/navigation.css`.

## Steps

1. Add a no-preference condition and set `transform: scale(0.96)` with a
   `150ms ease-out` transition for the public coarse-pointer press state.
2. Replace reduced-motion `transition: none` with a named-property 120ms
   `ease-out` transition for color, background, border, and opacity only.
3. Remove the home stylesheet's blanket transition removal; keep animation and
   scroll suppression and add the same short feedback only to relevant controls.
4. Animate mobile drawer and backdrop entry only when reduced motion is not
   requested.

## Boundaries

- Do not change navigation structure, active route state, or touch targets.
- Do not add dependencies or animate layout/transform under reduced motion.
- If current selectors or token values drift from the cited commit, stop and
  report the difference.

## Verification

- **Mechanical**: targeted ESLint and `npx.cmd tsc --noEmit` pass.
- **Feel check**: press a bottom navigation item and menu control on a touch
  viewport; confirm the item compresses once and returns smoothly, and the
  drawer enters without overshoot. Enable reduced motion; confirm no movement
  and a short color/opacity response.
- **Done when**: selected state remains distinct, reduced-motion mode has no
  scaled controls, and focus styling remains visible.
