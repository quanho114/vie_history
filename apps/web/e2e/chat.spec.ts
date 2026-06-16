import { test, expect } from '@playwright/test';

test.describe('Chat', () => {
  test('should display welcome message', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('HistoriAI')).toBeVisible();
  });

  test('should send query and receive response', async ({ page }) => {
    await page.goto('/');
    
    // Type a query
    await page.getByRole('textbox').fill('Chiến dịch Điện Biên Phủ diễn ra năm nào?');
    
    // Submit
    await page.getByRole('button', { name: /gửi/i }).click();
    
    // Wait for response (with timeout)
    await expect(page.getByText('1954')).toBeVisible({ timeout: 30000 });
  });
});
