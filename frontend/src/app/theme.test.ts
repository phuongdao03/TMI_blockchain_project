import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const stylesheet = readFileSync(
  resolve(process.cwd(), "src/app/globals.css"),
  "utf8",
);
const publicSearchPage = readFileSync(
  resolve(process.cwd(), "src/app/(public)/search/page.tsx"),
  "utf8",
);
const publicWorkDetail = readFileSync(
  resolve(process.cwd(), "src/components/public/public-work-detail.tsx"),
  "utf8",
);
const publicLibrary = readFileSync(
  resolve(process.cwd(), "src/components/public/public-library.tsx"),
  "utf8",
);
const publicWorkCard = readFileSync(
  resolve(process.cwd(), "src/components/public/public-work-card.tsx"),
  "utf8",
);

describe("THV identity theme", () => {
  it.each([
    ["--thv-red", "#9d0000"],
    ["--thv-red-dark", "#650000"],
    ["--thv-red-deep", "#470000"],
    ["--thv-red-light", "#b51212"],
    ["--thv-gold", "#f6c515"],
    ["--thv-gold-light", "#ffd83d"],
    ["--thv-gold-dark", "#d49a00"],
    ["--thv-bg-warm", "#fff9f3"],
    ["--thv-text", "#241515"],
    ["--thv-text-secondary", "#6b5656"],
    ["--thv-border", "#ead9d3"],
    ["--color-primary-700", "#650000"],
    ["--color-primary-600", "#9d0000"],
    ["--color-primary-500", "#b51212"],
    ["--color-primary-100", "#fce8df"],
    ["--color-primary-50", "#fff4ed"],
    ["--color-accent-gold", "#f6c515"],
    ["--color-neutral-950", "#241515"],
    ["--color-neutral-700", "#6b5656"],
    ["--color-neutral-500", "#8d7474"],
    ["--color-neutral-200", "#ead9d3"],
    ["--color-surface", "#ffffff"],
    ["--color-background", "#fff9f3"],
    ["--color-success", "#347a4a"],
    ["--color-warning", "#a87324"],
    ["--color-error", "#b54343"],
    ["--color-ink-950", "#241515"],
    ["--color-ink-900", "#470000"],
    ["--color-ink-800", "#650000"],
    ["--color-gold-300", "#f6c515"],
  ])("defines %s as %s", (token, value) => {
    expect(stylesheet).toContain(`${token}: ${value};`);
  });

  it("provides a visible keyboard focus treatment", () => {
    expect(stylesheet).toContain(":focus-visible");
    expect(stylesheet).toContain("outline-offset");
  });

  it("defines semantic public status styles for both color schemes", () => {
    expect(stylesheet).toContain("--theme-warning:");
    expect(stylesheet).toContain(".public-status-panel");
    expect(stylesheet).toContain(".public-status-panel__title");
    expect(stylesheet).toContain(".public-status-panel__action");
    expect(stylesheet).toContain("color: var(--theme-text)");
  });

  it("keeps editorial labels legible on the light audience surface", () => {
    expect(stylesheet).toContain(".home-audiences .registry-section-label");
    expect(stylesheet).toContain("color: var(--thv-red-dark);");
  });

  it("uses the approved red-and-gold treatment for the public hero", () => {
    expect(stylesheet).toContain(".public-home .registry-hero");
    expect(stylesheet).toContain("var(--thv-red-deep)");
    expect(stylesheet).toContain(".public-home .registry-hero h1 span");
    expect(stylesheet).toContain("var(--thv-gold-light)");
  });

  it("overrides public home utility colors for the dark surface", () => {
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .home-journey .font-mono',
    );
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .home-audiences .text-primary-700',
    );
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .home-audiences .text-slate-600',
    );
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .home-featured .text-neutral-950',
    );
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .home-featured .text-primary-800',
    );
  });

  it("keeps dossier state surfaces semantic and legible in dark workspaces", () => {
    expect(stylesheet).toContain(".dossier-state-card");
    expect(stylesheet).toContain(".dossier-readonly-notice");
    expect(stylesheet).toContain(".dossier-payment-notice");
    expect(stylesheet).toContain(".dossier-workflow");
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .dashboard-main .dossier-state-card',
    );
  });

  it("keeps dashboard navigation in the red-and-gold brand system in dark mode", () => {
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .dashboard-navigation__link:hover',
    );
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .dashboard-navigation__link--active,',
    );
    expect(stylesheet).toContain("background: var(--thv-gold);");
    expect(stylesheet).toContain("color: var(--thv-red-deep);");
  });

  it("forces compact public headers to keep the workspace action inside the menu", () => {
    expect(stylesheet).toContain(
      ".public-shell .public-header__workspace {\n    display: none !important;",
    );
    expect(stylesheet).toContain(
      ".public-shell .public-header__menu {\n    display: grid !important;",
    );
  });

  it("maps every authenticated status palette to dark workspace tokens", () => {
    expect(stylesheet).toContain(".dashboard-main .bg-neutral-50\\/70");
    expect(stylesheet).toContain(".dashboard-main .bg-emerald-50");
    expect(stylesheet).toContain(".dashboard-main .bg-amber-50");
    expect(stylesheet).toContain(".dashboard-main .bg-blue-50");
    expect(stylesheet).toContain(".dashboard-main .bg-red-50");
    expect(stylesheet).toContain(".dashboard-main .text-emerald-800");
    expect(stylesheet).toContain(".dashboard-main .text-amber-800");
    expect(stylesheet).toContain(".dashboard-main .text-blue-800");
    expect(stylesheet).toContain(".dashboard-main .text-red-800");
  });

  it("keeps public search on semantic surfaces instead of a permanently dark panel", () => {
    expect(publicSearchPage).not.toContain("bg-[#151515]");
    expect(publicSearchPage).not.toContain("text-white");
    expect(stylesheet).toContain(".public-search-surface");
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .public-search-surface',
    );
  });

  it("maps public work detail and dashboard cards to semantic theme surfaces", () => {
    expect(publicWorkDetail).toContain("public-theme-surface");
    expect(stylesheet).toContain(".public-theme-surface .text-white");
    expect(stylesheet).toContain(".public-theme-surface .bg-ink-900");
    expect(stylesheet).toContain(
      'html[data-theme="light"] .public-theme-surface .text-emerald-300',
    );
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .public-theme-surface .text-emerald-300',
    );
    expect(stylesheet).toContain(".dashboard-main .bg-surface");
  });

  it("uses restrained warm surfaces for the public library in both color schemes", () => {
    expect(stylesheet).toContain(".public-library-page {");
    expect(stylesheet).toContain("--theme-bg: #fcf5f0;");
    expect(stylesheet).toContain(
      'html[data-theme="dark"] .public-library-page',
    );
    expect(stylesheet).toContain("--theme-bg: #24100f;");
  });

  it("keeps the featured work card stacked until a wide desktop is available", () => {
    expect(publicLibrary).toContain(
      "xl:grid-cols-[minmax(0,1.35fr)_minmax(18rem,.65fr)]",
    );
    expect(publicWorkCard).toContain(
      "xl:grid-cols-[minmax(0,1.15fr)_minmax(18rem,.85fr)]",
    );
  });

  it("disables branded motion when reduced motion is requested", () => {
    expect(stylesheet).toContain(".evidence-register:hover .evidence-document");
    expect(stylesheet).toContain("transition-duration: 0.01ms !important");
  });
});
