import { defineConfig, devices } from "@playwright/test";

const webPort = Number(process.env.E2E_WEB_PORT || 3000);
const mockApiPort = Number(process.env.E2E_MOCK_API_PORT || 4010);
const webBaseUrl = process.env.E2E_BASE_URL || `http://127.0.0.1:${webPort}`;
const mockApiBaseUrl = process.env.E2E_MOCK_API_BASE_URL || `http://127.0.0.1:${mockApiPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: webBaseUrl,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `E2E_MOCK_API_PORT=${mockApiPort} node tests/e2e/helpers/mockApiServer.mjs`,
      url: `${mockApiBaseUrl}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: `NEXT_PUBLIC_API_BASE_URL=${mockApiBaseUrl} NEXT_PUBLIC_APP_NAME="AI Trading SaaS Starter Kit" npm run dev -- --hostname 127.0.0.1 --port ${webPort}`,
      url: webBaseUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 90_000,
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
