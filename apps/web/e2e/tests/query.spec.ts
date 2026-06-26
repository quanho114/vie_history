import { test, expect } from '@playwright/test';

test.describe('Query Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Inject localStorage API key so the chat input is not disabled, using "mock" provider
    await page.addInitScript(() => {
      window.localStorage.setItem('active_provider', 'mock');
      window.localStorage.setItem('mock_key', 'dummy-key-for-e2e');
    });

    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'Test1234!');
    await page.click('button[type="submit"]');
    
    // Wait for the transition button to appear and click it
    const transitionBtn = page.locator('button:has-text("Tiếp tục tiến vào hệ thống")');
    await expect(transitionBtn).toBeVisible({ timeout: 10000 });
    await transitionBtn.click();
    
    // Assert we transitioned to the chat page
    await page.waitForURL('**/chat', { timeout: 10000 });
  });

  test('query page loads', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.locator('textarea')).toBeVisible({ timeout: 10000 });
  });

  test('query submission shows loading state', async ({ page }) => {
    await page.goto('/chat');
    
    // Intercept the stream API and delay the response to ensure loading states show up
    await page.route('**/api/v1/query/stream', async route => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'data: {"type": "content", "content": "Chiến tranh Việt Nam..."}\n\n'
      });
    });

    const input = page.locator('textarea').first();
    await expect(input).toBeEnabled({ timeout: 5000 });
    await input.fill('Chiến tranh Việt Nam');
    await page.locator('form button[type="submit"]').click();
    
    // Check for loading indicator or stage updates (since it is delayed, this will reliably pass)
    const loading = page.locator('[class*="loading"], [class*="skeleton"], .spinner, [class*="Thinking"]').first();
    await expect(loading.or(page.locator('text=/Phân loại|Kiểm chứng|Tìm nguồn|Soạn câu trả lời/i'))).toBeVisible({ timeout: 5000 });
  });
});
