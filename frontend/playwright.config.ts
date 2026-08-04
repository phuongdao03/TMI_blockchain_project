import { defineConfig, devices } from "@playwright/test";

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
  webServer: [
    {
      command: "node e2e/mock-auth-server.mjs",
      port: 4010,
      reuseExistingServer: false,
    },
    {
      command:
        "node node_modules/next/dist/bin/next dev --webpack --hostname 127.0.0.1 --port 3100",
      port: 3100,
      reuseExistingServer: false,
      env: {
        API_BASE_URL: "http://127.0.0.1:4010",
        APP_BASE_URL: "http://127.0.0.1:3100",
        NEXT_DIST_DIR: ".next-e2e",
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
