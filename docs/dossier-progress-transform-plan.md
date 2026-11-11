# Dossier progress transform plan

- **Status**: Deferred
- **Commit**: `1b99685`
- **Severity**: MEDIUM
- **Category**: Rendering performance
- **Estimated scope**: 2 files, small

## Problem

The dossier creation progress indicator animates `width`, which causes layout
work on each step change. Current source is
`frontend/src/components/dossiers/dossier-create-form.tsx:1058`.

```tsx
/* frontend/src/components/dossiers/dossier-create-form.tsx:1058 — current */
<div
  className="h-full rounded-full bg-primary-600 transition-[width]"
  style={{
    width: `${(informationComplete / informationTotal) * 100}%`,
  }}
/>
```

## Target

Keep the same progress value and visual origin while scaling a full-width inner
bar with `transform: scaleX(informationComplete / informationTotal)` and
`transform-origin: left center`. Retain the existing Tailwind default
`150ms cubic-bezier(0.4, 0, 0.2, 1)` transition timing when using
`transition-[transform]`. Preserve the global reduced-motion override.

## Repo conventions to follow

- Keep the current progress calculation and component owner.
- Use CSS transforms only for the visual fill; do not change step semantics.

## Steps

1. Replace `transition-[width]` with `transition-[transform]`; set the inner
   bar width to 100% and scale it using the existing completion ratio.
2. Keep the bar anchored with `transform-origin: left center` and preserve the
   global reduced-motion transition-duration override.

## Boundaries

- Deferred outside current mobile home/navigation scope.
- Do not change dossier steps or validation behavior.
- Re-open the cited source before execution; stop if it has changed.

## Verification

- **Mechanical**: dossier form tests and targeted typecheck pass.
- **Feel check**: move across form steps and confirm the progress fill remains
  anchored to the left edge; confirm reduced motion skips the animation.
- **Done when**: progress percentages remain identical and no layout shift is
  introduced.
