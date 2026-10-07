import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import PreviewTabsPage from "@/app/preview-tabs/page";

describe("PreviewTabsPage", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("shows four role tabs in development without the mock auth shim", () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("AUTH_E2E_SHIM", "false");

    const markup = renderToStaticMarkup(<PreviewTabsPage />);

    for (const role of ["VIEWER", "USER", "MODERATOR", "SUPER_ADMIN"]) {
      expect(markup).toContain(`/ui-preview?role=${role}`);
    }
    expect(markup).not.toContain("/local-preview?screen=");
  });

  it("keeps mock API screens behind the explicit shim", () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("AUTH_E2E_SHIM", "true");

    const markup = renderToStaticMarkup(<PreviewTabsPage />);

    expect(markup).toContain("/local-preview?screen=applicant-home");
  });

  it("does not expose the preview launcher in production", () => {
    vi.stubEnv("NODE_ENV", "production");

    expect(() => renderToStaticMarkup(<PreviewTabsPage />)).toThrow(
      "NEXT_HTTP_ERROR_FALLBACK;404",
    );
  });
});
