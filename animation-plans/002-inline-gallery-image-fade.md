# 002 — Fade loaded inline gallery photos

- **Status**: DONE
- **Commit**: `1b99685`
- **Severity**: MEDIUM
- **Category**: Continuity
- **Estimated scope**: 3 files, small

## Problem

`HeritageGallery` replaces the selected image using a `key` of
`${photo.file}-${retry}`. The newly mounted image has no transition state, so
the stage swaps abruptly after loading. The stage already keeps a fixed aspect
ratio and exposes loading and error feedback.

```tsx
/* frontend/src/components/public/heritage-gallery.tsx:143 — current */
<Image
  alt={photo.title}
  fill
  key={`${photo.file}-${retry}`}
  onLoad={() => setLoadedFile(photo.file)}
  src={`/assets/institution/${photo.file}`}
/>
```

## Target

- Unloaded selected image: `opacity: 0`.
- Loaded selected image: `opacity: 1`.
- Transition: `opacity 180ms var(--ease-standard)`; reduced motion keeps an
  opacity-only `120ms ease-out` response.
- Do not fade the spinner or error alert.

## Repo conventions to follow

- Gallery styling lives in `frontend/src/components/public/home-editorial.css`;
  shared image geometry is in `frontend/src/app/globals.css`.
- Keep image load state in `HeritageGallery` and use existing motion token
  `--ease-standard`.

## Steps

1. Expose whether the selected file is loaded on the image trigger button.
2. Keep the image opacity at zero until its own load callback marks it loaded;
   transition opacity only.
3. Add reduced-motion opacity timing without changing image size, position, or
   stage aspect ratio.

## Boundaries

- Do not change lightbox animation, loading thresholds, retry logic, or image
  sources.
- Do not add dependencies.
- If image loading ownership has changed since this commit, stop and report.

## Verification

- **Mechanical**: focused gallery tests, targeted ESLint, and typecheck pass.
- **Feel check**: advance with arrows and a swipe; confirm the spinner remains
  visible while the new image loads and the loaded photo fades in. Under reduced
  motion, only the brief opacity transition remains.
- **Done when**: gallery layout does not shift and loading/error states remain
  legible.
