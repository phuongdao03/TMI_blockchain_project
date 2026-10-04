import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

afterEach(() => vi.unstubAllEnvs());

describe("local interface preview", () => {
  it("opens a real applicant screen with mock-only session cookies", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("AUTH_E2E_SHIM", "true");

    const response = await GET(
      new NextRequest(
        "http://127.0.0.1:3100/local-preview?screen=applicant-dossiers",
        { headers: { host: "127.0.0.1:3100" } },
      ),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "http://127.0.0.1:3100/dossiers",
    );
    expect(response.cookies.get("cns_access")?.value).toBe("e2e-access");
    expect(response.cookies.get("cns_access")?.httpOnly).toBe(true);
    expect(response.cookies.get("cns_e2e_persona")?.value).toBe("applicant");
    expect(response.headers.get("cache-control")).toBe("no-store");
  });

  it("does not provide a login bypass outside the local mock environment", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("AUTH_E2E_SHIM", "true");
    const request = new NextRequest(
      "http://127.0.0.1:3100/local-preview?screen=admin-dashboard",
    );
    expect((await GET(request)).status).toBe(404);

    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("AUTH_E2E_SHIM", "false");
    expect((await GET(request)).status).toBe(404);
  });

  it("rejects unknown screens and non-loopback hosts", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("AUTH_E2E_SHIM", "true");

    expect(
      (
        await GET(
          new NextRequest(
            "http://127.0.0.1:3100/local-preview?screen=../../admin",
          ),
        )
      ).status,
    ).toBe(404);
    expect(
      (
        await GET(
          new NextRequest(
            "https://example.com/local-preview?screen=admin-dashboard",
          ),
        )
      ).status,
    ).toBe(404);
  });
});
