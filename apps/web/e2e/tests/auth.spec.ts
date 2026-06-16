import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1, h2')).toContainText(/login|đăng nhập/i);
  });

  test('register page loads', async ({ page }) => {
    await page.goto('/register');
    await expect(page.locator('h1, h2')).toContainText(/register|đăng ký/i);
  });

  test('login with invalid credentials shows error', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"]', 'invalid@test.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    await expect(page.locator('[role="alert"], .error, .text-red')).toBeVisible({ timeout: 5000 });
  });
});
