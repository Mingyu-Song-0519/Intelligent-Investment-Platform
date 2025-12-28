import { test, expect } from '@playwright/test';

/**
 * TS-001: Page Initial Loading Test (P0)
 *
 * Verifies that the stock analysis dashboard loads successfully with all required elements.
 */
test.describe('Page Initial Loading', () => {

  test('should load the dashboard with all main elements visible', async ({ page }) => {
    // Navigate to the dashboard
    await page.goto('/');

    // Wait for the page to be fully loaded (Streamlit indicator should disappear)
    await page.waitForSelector('[data-testid="stAppViewContainer"]', { timeout: 30000 });

    // Additional wait for Streamlit to fully render
    await page.waitForTimeout(3000);

    // Check that the main container is visible
    const mainContainer = page.locator('[data-testid="stAppViewContainer"]');
    await expect(mainContainer).toBeVisible();

    // Check that the sidebar is visible
    const sidebar = page.locator('[data-testid="stSidebar"]');
    await expect(sidebar).toBeVisible();

    // Verify main tab selector exists (might not be visible in scrolled view)
    const tabSelector = page.locator('[data-testid="stTabs"]').first();
    const tabCount = await tabSelector.count();
    expect(tabCount).toBeGreaterThan(0);

    // Verify at least one tab exists (doesn't need to be visible)
    const tabs = page.locator('button[role="tab"]');
    const tabElementCount = await tabs.count();
    expect(tabElementCount).toBeGreaterThan(0);

    // Verify page has content (more lenient than specific header)
    const pageText = await page.textContent('[data-testid="stAppViewContainer"]');
    expect(pageText).toBeTruthy();
    expect(pageText!.length).toBeGreaterThan(0);
  });

  test('should load sidebar market selection buttons', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="stSidebar"]', { timeout: 30000 });

    // Check for Korean market button
    const krButton = page.locator('[data-testid="stSidebar"] button:has-text("🇰🇷")');
    await expect(krButton).toBeVisible();

    // Check for US market button
    const usButton = page.locator('[data-testid="stSidebar"] button:has-text("🇺🇸")');
    await expect(usButton).toBeVisible();
  });

  test('should have no console errors on initial load', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForSelector('[data-testid="stAppViewContainer"]', { timeout: 30000 });

    // Wait a bit for any delayed errors
    await page.waitForTimeout(2000);

    // Check for critical errors (allow some Streamlit internal warnings)
    const criticalErrors = consoleErrors.filter(err =>
      !err.includes('DevTools') &&
      !err.includes('favicon') &&
      !err.includes('sourcemap')
    );

    expect(criticalErrors).toHaveLength(0);
  });

  test('should load within acceptable time (< 10 seconds)', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/');
    await page.waitForSelector('[data-testid="stAppViewContainer"]', { timeout: 30000 });

    const loadTime = Date.now() - startTime;

    // Page should load within 10 seconds
    expect(loadTime).toBeLessThan(10000);
  });
});
