# Icon-system research for THV

Research date: 2026-08-29. Sources are limited to official project sites and
first-party repositories.

## Recommendation

Use **Lucide** as THV's default product icon system. Its consistent 24px outline
language, adjustable stroke, typed React components, explicit tree-shaking
promise, and first-party accessibility guidance suit a polished data/product UI.
Use fills sparingly for selected/active states; Lucide supports filled treatment
but is fundamentally outline-led.

Choose **Phosphor** instead if THV needs a more expressive visual voice or
frequently switches one glyph among thin/light/regular/bold/fill/duotone states.
That flexibility costs more per imported icon because the official maintainer
notes that all six weights are currently bundled for each imported icon.

## Comparison

| System       | Visual consistency / character                                                                                                                     | React + Next.js                                                                                                                       | Weights / fill                                                                                                                    | Accessibility                                                                                                                                    | Bundle behavior                                                                                                                                                                                                            | License                                  |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| **Lucide**   | Minimal, geometric outline system; standalone SVG components expose size, color, and stroke width. Best neutral fit for dense, premium product UI. | `lucide-react`; fully typed.                                                                                                          | Adjustable stroke width. Filled-icon guidance exists, but the core family is outline-first rather than separately drawn weights.  | Dedicated React accessibility guidance and an in-depth accessibility resource are linked from the official React guide.                          | Officially documented as tree-shakable: only imported icons enter the final bundle. Avoid indiscriminate dynamic imports.                                                                                                  | ISC; inherited Feather icons remain MIT. |
| **Phosphor** | Cohesive but warmer and more expressive; designed as a flexible family for interfaces and diagrams.                                                | `@phosphor-icons/react`; dedicated `/ssr` import for React Server Components/SSR; official Next.js `optimizePackageImports` guidance. | Six designed variants: thin, light, regular, bold, fill, duotone. Strongest option for visual hierarchy and state changes.        | `alt` prop is documented; standard SVG/ARIA props and `aria-label` can pass through.                                                             | Tree-shakes unused icons. First-party maintainer clarification: every imported icon currently carries all six weights (~4–5 KB/icon plus ~2 KB shared code); namespace imports can prevent tree-shaking.                   | MIT.                                     |
| **Tabler**   | Very large, consistent 24×24 family with a default 2px stroke. More utilitarian than distinctive; stroke is freely adjustable.                     | `@tabler/icons-react`; TypeScript declarations and standard SVG props.                                                                | Outline catalog plus a substantial separately drawn filled catalog; stroke-width changes create lighter/heavier outline variants. | Official React accessibility guidance recommends `aria-hidden="true"` for decorative SVGs and putting the accessible name on icon-only controls. | React package states it uses ES modules and is “completely tree-shakable.”                                                                                                                                                 | MIT.                                     |
| **Iconoir**  | Clean 24×24 system with a finer default 1.5 stroke; slightly more editorial/technical feel.                                                        | `iconoir-react`; standard SVG props and an `IconoirProvider` for global defaults. Current package declares React 18/19 peers.         | Regular and solid entry points; adjustable stroke width. Less nuanced than Phosphor's six weights.                                | No dedicated first-party accessibility guidance was found in the React README; apply an app-level accessibility wrapper/policy.                  | Package exposes ESM, sets `sideEffects: false`, and separates `./regular` and `./solid`; these are tree-shaking-friendly signals, but the docs do not make as explicit a final-bundle guarantee as Lucide/Tabler/Phosphor. | MIT.                                     |

## Suggested THV usage rules

- Standardize on 20px for compact controls and 24px for primary actions; keep
  one optical stroke token per size.
- Decorative icons: `aria-hidden="true"`. Icon-only controls: accessible button
  name via `aria-label` or visible/visually-hidden text. Never rely on the glyph
  alone to convey status.
- Import named icons statically. Avoid whole-library namespace imports and
  runtime icon-name maps unless code-split.
- Use filled icons only for binary selected states (bookmark, favorite, active
  navigation), not as a competing general style.
- Wrap the chosen library behind a small THV `Icon` convention (size, stroke,
  accessibility), while retaining direct static imports so bundlers can
  eliminate unused glyphs.

## Official sources

- Lucide: [React guide](https://lucide.dev/guide/react),
  [license](https://lucide.dev/license)
- Phosphor:
  [official React repository/README](https://github.com/phosphor-icons/react),
  [maintainer bundle-size explanation](https://github.com/orgs/phosphor-icons/discussions/581)
- Tabler: [official repository/README](https://github.com/tabler/tabler-icons),
  [React package README](https://github.com/tabler/tabler-icons/tree/main/packages/icons-react),
  [React accessibility guide](https://tabler.io/guides/how-to-use-svg-icons-in-react)
- Iconoir:
  [official repository/README](https://github.com/iconoir-icons/iconoir),
  [React package README](https://github.com/iconoir-icons/iconoir/tree/main/packages/iconoir-react),
  [React package manifest](https://github.com/iconoir-icons/iconoir/blob/main/packages/iconoir-react/package.json),
  [MIT license](https://github.com/iconoir-icons/iconoir/blob/main/packages/iconoir-react/LICENSE)

## Evidence limits

“Premium,” “editorial,” and “utilitarian” are visual-fit judgments derived from
the documented grids, stroke defaults, and variant systems—not claims made by
the projects. Bundle conclusions are limited to what maintainers document; no
local benchmark was run.
