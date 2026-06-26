import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Inject localStorage API key so the chat page doesn't throw or show warning states
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

  test('main pages are accessible', async ({ page }) => {
    const pages = ['/chat', '/documents', '/wiki', '/timeline', '/graph'];
    for (const path of pages) {
      await page.goto(path);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('no console errors on main pages', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');
    
    const critical = errors.filter(e => !e.includes('favicon') && !e.includes('DevTools') && !e.includes('HMR'));
    expect(critical).toHaveLength(0);
  });
});
