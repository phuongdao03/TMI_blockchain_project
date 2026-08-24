import { afterEach, describe, expect, it, vi } from "vitest";

const { permanentRedirect } = vi.hoisted(() => ({
  permanentRedirect: vi.fn((destination: string) => {
    throw new Error(`redirect:${destination}`);
  }),
}));

vi.mock("next/navigation", () => ({ permanentRedirect }));

import LegacyVerificationPage from "@/app/(public)/kiem-tra/[token]/page";
import LegacyWorkPage from "@/app/(public)/tai-san/[slug]/page";
import nextConfig from "../next.config";

describe("public route compatibility", () => {
  afterEach(() => {
    permanentRedirect.mockClear();
    vi.unstubAllEnvs();
  });

  it("permanently redirects the former work address to /works", async () => {
    await expect(
      LegacyWorkPage({ params: Promise.resolve({ slug: "bo-nhan-dien-tmi" }) }),
    ).rejects.toThrow("redirect:/works/bo-nhan-dien-tmi");

    expect(permanentRedirect).toHaveBeenCalledWith(
      "/works/bo-nhan-dien-tmi",
    );
  });

  it("permanently redirects the former verification address to /verify", async () => {
    await expect(
      LegacyVerificationPage({ params: Promise.resolve({ token: "demo-token" }) }),
    ).rejects.toThrow("redirect:/verify/demo-token");

    expect(permanentRedirect).toHaveBeenCalledWith("/verify/demo-token");
  });

  it("proxies opaque QR redirects without exposing a backend-only route", async () => {
    vi.stubEnv("API_BASE_URL", "https://api.example.test");
    const rewrites = await nextConfig.rewrites?.();

    expect(rewrites).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "/r/:token",
          destination: "https://api.example.test/r/:token",
        }),
      ]),
    );
  });

  it("prevents an opaque QR token from being cached or forwarded as a referrer", async () => {
    const headers = await nextConfig.headers?.();

    expect(headers).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "/r/:token",
          headers: expect.arrayContaining([
            expect.objectContaining({ key: "Cache-Control", value: "no-store" }),
            expect.objectContaining({ key: "Referrer-Policy", value: "no-referrer" }),
            expect.objectContaining({ key: "X-Robots-Tag", value: "noindex, nofollow" }),
          ]),
        }),
      ]),
    );
  });

  it("prevents certificate verification tokens from being indexed or cached", async () => {
    const headers = await nextConfig.headers?.();

    expect(headers).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "/verify/:token",
          headers: expect.arrayContaining([
            expect.objectContaining({ key: "Cache-Control", value: "no-store" }),
            expect.objectContaining({ key: "Referrer-Policy", value: "no-referrer" }),
            expect.objectContaining({ key: "X-Robots-Tag", value: "noindex, nofollow" }),
          ]),
        }),
      ]),
    );
  });
});
