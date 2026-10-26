import { defineConfig, devices } from '@playwright/test'

/**
 * Chromium, one worker, no retries.
 *
 * `E2E_BASE_URL` points the suite at an environment that is already running
 * (`make e2e` otherwise builds and starts the Compose stack first). Artifacts
 * are kept only for failing tests: a trace, a screenshot, and a video.
 */
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:8080'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  timeout: 120_000,
  expect: { timeout: 10_000 },
  outputDir: 'test-results',
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
