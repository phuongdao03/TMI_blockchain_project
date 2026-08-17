import { defineConfig, devices } from "@playwright/test";

const externalServers = process.env.E2E_EXTERNAL_SERVERS === "1";
const previewRun = process.env.E2E_RELEASE_MODE === "preview";
const applicationPort = previewRun ? 3101 : 3100;
const applicationUrl = `http://127.0.0.1:${applicationPort}`;
const previewTestName = /preview dashboard keeps submission closed/i;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "line",
  grep: previewRun ? previewTestName : undefined,
  grepInvert: previewRun ? undefined : previewTestName,
  expect: {
    timeout: 15000,
    toHaveScreenshot: {
      // Tolerate sub-pixel font/transform rasterization while keeping the
      // visual gate strict enough to catch real layout or content changes.
      maxDiffPixelRatio: 0.001,
    },
  },
  use: {
    baseURL: applicationUrl,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: externalServers
    ? undefined
    : [
        {
          command: "node e2e/mock-auth-server.mjs",
          port: 4010,
          reuseExistingServer: !process.env.CI,
        },
        {
          command: `node node_modules/next/dist/bin/next dev --webpack --hostname 127.0.0.1 --port ${applicationPort}`,
          port: applicationPort,
          reuseExistingServer: !process.env.CI,
          env: {
            API_BASE_URL: "http://127.0.0.1:4010",
            APP_BASE_URL: applicationUrl,
            AUTH_E2E_SHIM: "true",
            NEXT_DIST_DIR: previewRun ? ".next-e2e-preview" : ".next-e2e",
            NEXT_PUBLIC_RELEASE_MODE: previewRun ? "preview" : "full",
            NEXT_PUBLIC_FIREBASE_API_KEY: "e2e-api-key",
            NEXT_PUBLIC_FIREBASE_APP_ID: "1:123:web:e2e",
            NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: "e2e.firebaseapp.com",
            NEXT_PUBLIC_FIREBASE_PROJECT_ID: "e2e-project",
          },
        },
      ],
  projects: (previewRun
    ? ["desktop-chrome"]
    : ["desktop-chrome", "mobile-chrome"]
  ).map((name) => ({
    name,
    use:
      name === "desktop-chrome"
        ? { ...devices["Desktop Chrome"], channel: "chrome" }
        : { ...devices["Pixel 7"], channel: "chrome" },
  })),
});
