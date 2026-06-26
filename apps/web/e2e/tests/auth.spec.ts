import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1')).toContainText(/Chào mừng trở lại/i);
    await expect(page.locator('button:has-text("Đăng nhập")').first()).toBeVisible();
  });

  test('register tab loads', async ({ page }) => {
    await page.goto('/login');
    // Click the "Đăng ký" tab selector
    await page.click('button:has-text("Đăng ký")');
    // Assert that username input fields for step 1 of registration are visible
    await expect(page.locator('input[placeholder="yourname"]')).toBeVisible();
  });

  test('login with invalid credentials shows error', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"]', 'invalid@test.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 5000 });
  });
});
