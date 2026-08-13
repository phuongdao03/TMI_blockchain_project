---
name: Immutable Prestige
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#e7bdb7'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#ad8883'
  outline-variant: '#5d3f3b'
  surface-tint: '#ffb4aa'
  primary: '#ffb4aa'
  on-primary: '#690003'
  primary-container: '#ff5545'
  on-primary-container: '#5c0002'
  inverse-primary: '#c0000a'
  secondary: '#fff9ef'
  on-secondary: '#3a3000'
  secondary-container: '#ffdb3c'
  on-secondary-container: '#725f00'
  tertiary: '#c8c6c5'
  on-tertiary: '#313030'
  tertiary-container: '#929090'
  on-tertiary-container: '#2a2a2a'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad5'
  primary-fixed-dim: '#ffb4aa'
  on-primary-fixed: '#410001'
  on-primary-fixed-variant: '#930005'
  secondary-fixed: '#ffe16d'
  secondary-fixed-dim: '#e9c400'
  on-secondary-fixed: '#221b00'
  on-secondary-fixed-variant: '#544600'
  tertiary-fixed: '#e5e2e1'
  tertiary-fixed-dim: '#c8c6c5'
  on-tertiary-fixed: '#1c1b1b'
  on-tertiary-fixed-variant: '#474746'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 64px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '500'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.0'
    letterSpacing: 0.1em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
  section-gap: 120px
---

## Brand & Style

The design system is engineered to evoke **authority, security, and timeless value**. As a digital certificate platform, it must transcend the fleeting nature of the web, presenting documents as immutable assets. The target audience includes academic institutions, luxury brands, and government agencies who require a platform that feels as prestigious as a physical parchment but as advanced as the blockchain technology powering it.

The visual style is **Corporate / Modern** with **Glassmorphic** accents. It utilizes a deep, multi-layered dark aesthetic to create a "command center" feel. Subtle technical motifs—such as thin grid lines, node-and-link patterns, and microscopic data points—reinforce the blockchain narrative without cluttering the interface. The emotional response should be one of absolute trust and high-end exclusivity.

## Colors

This design system employs a **high-contrast dark palette** to establish a premium atmosphere.

- **Primary (Ruby Red):** Used sparingly for high-intent actions (CTAs), critical status indicators, and brand accents. It represents energy and the "seal" of authenticity.
- **Secondary (Gold):** Reserved for excellence, achievement, and premium tiers. It is often used in gradients to simulate metallic light reflections on certificates.
- **Backgrounds:** A tiered system of blacks. The base layer is `#0F0F0F`, with elevated surfaces using `#1A1A1A`.
- **Gradients:** Use "Ruby Glow" (Ruby to deep Crimson) for buttons and "Auric Light" (Gold to soft Amber) for decorative elements and achievement badges.

## Typography

The system utilizes **Hanken Grotesk** for its sharp, contemporary geometry that feels both professional and innovative. To anchor the "technical" nature of blockchain, **JetBrains Mono** is introduced for labels, metadata, and ID strings, providing a clear distinction between narrative content and data-driven facts.

Headlines should utilize tight letter-spacing to appear more authoritative. Large display text may occasionally use a "Gold" gradient to highlight key value propositions. Ensure a high line-height for body text to maintain the "airy" and spacious feel required for luxury positioning.

## Layout & Spacing

This design system follows a **Fluid Grid** model built on an 8px base unit.

- **Desktop:** 12-column grid with 64px side margins to create a focused, center-weighted experience.
- **Sectioning:** Large vertical gaps (120px+) between major sections to allow the brand's graphic elements (nodes/networks) to breathe and occupy the periphery.
- **Rhythm:** Use "Generous Padding" inside cards and containers (minimum 32px) to prevent the UI from feeling cramped, maintaining the "Premium" look.
- **Data Density:** While the overall layout is spacious, data tables and certificate details should maintain a structured, logical alignment to ensure readability.

## Elevation & Depth

Hierarchy is achieved through **Tonal Layering** and **Backdrop Blurs**.

1. **Base (Level 0):** Pure `#0F0F0F`. No shadows.
2. **Surface (Level 1):** `#1A1A1A`. Soft, large-radius shadows (0px 20px 40px rgba(0,0,0,0.4)).
3. **Glass Overlay (Level 2):** Semi-transparent layers (`rgba(255,255,255,0.03)`) with a 12px backdrop blur. These are used for navigation bars and floating info-panels.
4. **Interactive (Hover):** When hovering over cards, a subtle "Ruby" or "Gold" outer glow (shadow) is applied to indicate life and interactivity.

Avoid heavy solid borders; instead, use 1px "Ghost Borders" with low-opacity white or brand-tinted strokes to define boundaries.

## Shapes

The shape language is **Soft yet Structured**.

- **Containers & Cards:** Use a standard `0.5rem` (8px) radius. This provides a modern touch without appearing too "bubbly" or informal.
- **Primary Buttons:** May use a slightly higher radius (`0.75rem`) to make them more inviting and distinct from structural containers.
- **Search Inputs:** Utilize pill-shaped styling (3) for the main search bar to contrast against the rectangular grid of certificates.
- **Graphic Accents:** Use perfect circles for "nodes" and thin, 1px lines for "network connections."

## Components

- **Buttons:** Primary buttons use the Ruby-to-Crimson gradient with white text. Secondary buttons are "Ghost" style (transparent with a 1px border and Ruby text).
- **Certificate Cards:** Feature a subtle Gold-tinted border on hover. The ID string is always set in `label-sm` (JetBrains Mono).
- **Status Chips:** Use a circular dot icon (pulsing if "Verifying") next to the text. Green for "Verified," Ruby for "Revoked," and Amber for "Pending."
- **Input Fields:** Deep black background with a 1px border that turns Ruby Red on focus. Labels are always positioned above the field in `label-sm`.
- **Blockchain Nodes:** A decorative component consisting of small circular points connected by low-opacity curved lines. These should animate subtly in the background to imply "Live Data."
- **Verification Seal:** A complex, multi-layered circular component featuring the secondary Gold color and a "Check" icon, used as the primary visual reward upon successful certificate validation.
