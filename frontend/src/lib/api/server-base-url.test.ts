import { afterEach, describe, expect, it } from "vitest";

import { resolveServerApiBaseUrl } from "./server-base-url";

const originalApiBaseUrl = process.env.API_BASE_URL;
const originalBackendUrl = process.env.BACKEND_URL;

afterEach(() => {
  process.env.API_BASE_URL = originalApiBaseUrl;
  process.env.BACKEND_URL = originalBackendUrl;
});

describe("resolveServerApiBaseUrl", () => {
  it("prefers an explicit API base URL", () => {
    process.env.API_BASE_URL = "https://api.example.test";
    process.env.BACKEND_URL = "https://deployment.vercel.app/backend";

    expect(resolveServerApiBaseUrl()).toBe("https://api.example.test");
  });

  it("uses the Vercel backend service URL", () => {
    delete process.env.API_BASE_URL;
    process.env.BACKEND_URL = "https://deployment.vercel.app/backend/";

    expect(resolveServerApiBaseUrl()).toBe(
      "https://deployment.vercel.app/backend",
    );
  });

  it("falls back to the local backend during development", () => {
    delete process.env.API_BASE_URL;
    delete process.env.BACKEND_URL;

    expect(resolveServerApiBaseUrl()).toBe("http://localhost:8000");
  });
});
