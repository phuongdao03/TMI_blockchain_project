import { defineConfig, devices } from "@playwright/test";

const externalServers = process.env.E2E_EXTERNAL_SERVERS === "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:3100",
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
          command:
            "node node_modules/next/dist/bin/next dev --webpack --hostname 127.0.0.1 --port 3100",
          port: 3100,
          reuseExistingServer: !process.env.CI,
          env: {
            API_BASE_URL: "http://127.0.0.1:4010",
            APP_BASE_URL: "http://127.0.0.1:3100",
            AUTH_E2E_SHIM: "true",
            NEXT_DIST_DIR: ".next-e2e",
            NEXT_PUBLIC_FIREBASE_API_KEY: "e2e-api-key",
            NEXT_PUBLIC_FIREBASE_APP_ID: "1:123:web:e2e",
            NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: "e2e.firebaseapp.com",
            NEXT_PUBLIC_FIREBASE_PROJECT_ID: "e2e-project",
          },
        },
      ],
  projects: [
    {
      name: "desktop-chrome",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 7"], channel: "chrome" },
    },
  ],
});
