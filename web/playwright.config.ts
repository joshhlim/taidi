import { defineConfig } from "@playwright/test";

// Web runs on :3100, not Next.js's usual :3000 — this is a shared dev
// machine and :3000 is already occupied by an unrelated project (found the
// hard way: reuseExistingServer silently ran a test suite against someone
// else's app). The API's default :8000 was confirmed free. reuseExistingServer
// is off so a future collision fails loudly instead of repeating that mistake.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3100",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "cd ../api && uvicorn app.main:app --port 8000",
      url: "http://localhost:8000/healthz",
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "npm run dev -- --port 3100",
      url: "http://localhost:3100",
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
});
