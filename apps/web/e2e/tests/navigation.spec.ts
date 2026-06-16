import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('main pages are accessible', async ({ page }) => {
    const pages = ['/', '/query', '/documents', '/projects'];
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
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const critical = errors.filter(e => !e.includes('favicon') && !e.includes('DevTools'));
    expect(critical).toHaveLength(0);
  });
});
