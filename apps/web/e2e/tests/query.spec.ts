import { test, expect } from '@playwright/test';

test.describe('Query Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login if needed
    await page.goto('/login');
    try {
      await page.fill('input[type="email"]', 'test@example.com');
      await page.fill('input[type="password"]', 'Test1234!');
      await page.click('button[type="submit"]');
    } catch {
      // May already be logged in
    }
  });

  test('query page loads', async ({ page }) => {
    await page.goto('/query');
    await expect(page.locator('textarea, input[type="text"]')).toBeVisible({ timeout: 10000 });
  });

  test('query submission shows loading state', async ({ page }) => {
    await page.goto('/query');
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Chiến tranh Việt Nam');
    await page.click('button[type="submit"]');
    // Check for loading indicator
    const loading = page.locator('[class*="loading"], [class*="skeleton"], .spinner').first();
    await expect(loading.or(page.locator('text=/đang|loading/i'))).toBeVisible({ timeout: 3000 });
  });
});
