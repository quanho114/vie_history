import { test, expect } from '@playwright/test';

test.describe('Chat', () => {
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

  test('should display welcome message', async ({ page }) => {
    await expect(page.getByText(/Chào mừng đến với HistoriAI/i)).toBeVisible();
  });

  test('should send query and receive response', async ({ page }) => {
    // Type a query in the textarea
    const textarea = page.locator('textarea');
    await expect(textarea).toBeEnabled({ timeout: 5000 });
    await textarea.fill('Chiến dịch Điện Biên Phủ diễn ra năm nào?');
    
    // Click submit button (can locate by icon class, type="submit", or parent form submit)
    await page.locator('form button[type="submit"]').click();
    
    // Wait for response inside the AI bubble (with timeout)
    await expect(page.locator('.bubble-ai').getByText('1954')).toBeVisible({ timeout: 30000 });
  });
});
