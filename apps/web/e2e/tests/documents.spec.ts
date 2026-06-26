import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

test.describe('Documents Batch Upload and Refresh', () => {
  let file1Path: string;
  let file2Path: string;

  test.beforeAll(() => {
    // Create temporary files for testing upload
    file1Path = path.join(__dirname, 'temp_test_file_1.txt');
    file2Path = path.join(__dirname, 'temp_test_file_2.txt');
    fs.writeFileSync(file1Path, 'This is test document content 1 for sequential upload verification.');
    fs.writeFileSync(file2Path, 'This is test document content 2 for sequential upload verification.');
  });

  test.afterAll(() => {
    // Cleanup temporary files
    if (fs.existsSync(file1Path)) fs.unlinkSync(file1Path);
    if (fs.existsSync(file2Path)) fs.unlinkSync(file2Path);
  });

  test('should login, click refresh, and batch upload files sequentially', async ({ page }) => {
    // 1. Log in
    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'Test1234!');
    await page.click('button:has-text("Đăng nhập hệ thống")');

    // 2. Click the transition continue button
    const continueBtn = page.locator('button:has-text("Tiếp tục tiến vào hệ thống")');
    await expect(continueBtn).toBeVisible({ timeout: 10000 });
    await continueBtn.click();

    // 3. Wait for the transition loading progress to complete and redirect to /chat
    await page.waitForURL('**/chat', { timeout: 10000 });

    // 4. Navigate directly to /documents
    await page.goto('/documents');
    await page.waitForLoadState('networkidle');

    // 5. Verify Refresh button exists and click it
    const refreshBtn = page.locator('button[title="Làm mới dữ liệu"]');
    await expect(refreshBtn).toBeVisible({ timeout: 10000 });
    await refreshBtn.click();

    // 6. Open Ingest Drawer
    const openIngestBtn = page.locator('button:has-text("Nhập tài liệu mới")');
    await expect(openIngestBtn).toBeVisible();
    await openIngestBtn.click();

    // 7. Select File Ingest Tab
    const fileTabBtn = page.locator('button:has-text("Tải lên tệp")');
    await expect(fileTabBtn).toBeVisible();
    await fileTabBtn.click();

    // 8. Select multiple files via input
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles([file1Path, file2Path]);

    // 9. Verify files list shows both files
    await expect(page.locator('text=Danh sách tệp (2)')).toBeVisible();
    await expect(page.locator('text=temp_test_file_1.txt')).toBeVisible();
    await expect(page.locator('text=temp_test_file_2.txt')).toBeVisible();

    // 10. Add tags
    await page.fill('input[placeholder*="hồ chí minh"]', 'test, playwright, batch');

    // 11. Click upload button
    const submitBtn = page.locator('button[form="drawer-file-form"]');
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    // 12. Wait for sequential processing and drawer closure
    await expect(page.locator('text=Đang xử lý').first()).toBeVisible();
    
    // The drawer should close after completion
    await expect(page.locator('text=Danh sách tệp (2)')).not.toBeVisible({ timeout: 25000 });
  });

  test('should sequentially ingest multiple URLs from textarea', async ({ page }) => {
    // 1. Log in
    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'Test1234!');
    await page.click('button:has-text("Đăng nhập hệ thống")');

    // 2. Click the transition continue button
    const continueBtn = page.locator('button:has-text("Tiếp tục tiến vào hệ thống")');
    await expect(continueBtn).toBeVisible({ timeout: 10000 });
    await continueBtn.click();

    // 3. Wait for redirect
    await page.waitForURL('**/chat', { timeout: 10000 });

    // 4. Navigate directly to /documents
    await page.goto('/documents');
    await page.waitForLoadState('networkidle');

    // 5. Open Ingest Drawer
    const openIngestBtn = page.locator('button:has-text("Nhập tài liệu mới")');
    await expect(openIngestBtn).toBeVisible();
    await openIngestBtn.click();

    // 6. Fill multiple URLs in the textarea
    const textarea = page.locator('textarea[placeholder*="vi.wikipedia.org"]');
    await expect(textarea).toBeVisible();
    await textarea.fill('https://vi.wikipedia.org/wiki/Tuyen_ngon_Doc_lap\nhttps://vi.wikipedia.org/wiki/Bao_Dai');

    // 7. Verify links list shows both URLs
    await expect(page.locator('text=Danh sách liên kết (2)')).toBeVisible();

    // 8. Add tags
    await page.fill('input[placeholder*="hồ chí minh"]', 'test, url, batch');

    // 9. Click submit button
    const submitBtn = page.locator('button[form="drawer-url-form"]');
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    // 10. Wait for sequential processing and drawer closure
    await expect(page.locator('text=Đang xử lý').first()).toBeVisible();
    
    // The drawer should close after completion
    await expect(page.locator('text=Danh sách liên kết (2)')).not.toBeVisible({ timeout: 25000 });
  });
});
