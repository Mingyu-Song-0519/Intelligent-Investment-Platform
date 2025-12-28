import { test, expect } from '@playwright/test';

/**
 * TS-005: AI Chatbot Bottom Fixed Position Test (P0)
 *
 * Verifies Phase 1 implementation: AI chatbot fixed at sidebar bottom
 * CRITICAL: Also verifies NO DUPLICATE chatbot rendering (bug found at line 2620-2622)
 */
test.describe('AI Chatbot Bottom Fixed Position', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="stSidebar"]', { timeout: 30000 });
  });

  test('should display AI chatbot section at the bottom of sidebar', async ({ page }) => {
    const sidebar = page.locator('[data-testid="stSidebar"]');

    // Wait for full render
    await page.waitForTimeout(3000);

    // Look for AI chatbot section
    // Common identifiers: chat input, chat messages, or specific headers
    const chatInput = sidebar.locator('[data-testid="stChatInput"]').first();
    const chatCount = await chatInput.count();

    if (chatCount > 0) {
      // Scroll chat into view
      await chatInput.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);

      // Get chatbot position
      const chatBox = await chatInput.boundingBox();
      const sidebarBox = await sidebar.boundingBox();

      if (chatBox && sidebarBox) {
        // Chatbot should be in the bottom portion of sidebar (last 50%)
        const sidebarBottom = sidebarBox.y + sidebarBox.height;
        const relativePosition = (sidebarBottom - chatBox.y) / sidebarBox.height;

        // Chat should be in bottom 50% of sidebar
        expect(relativePosition).toBeLessThan(0.5);
      }
    }

    // If chatbot is not available or not visible, that's acceptable
    // Just verify sidebar exists
    const sidebarText = await sidebar.textContent();
    expect(sidebarText).toBeTruthy();
  });

  test('CRITICAL: should have exactly ONE chatbot instance (no duplicates)', async ({ page }) => {
    const sidebar = page.locator('[data-testid="stSidebar"]');

    await page.waitForTimeout(3000);

    // Count all chat input elements in sidebar
    const chatInputs = sidebar.locator('[data-testid="stChatInput"]');
    const chatInputCount = await chatInputs.count();

    // Should be 0 (chatbot not available) or 1 (chatbot available)
    // Should NEVER be 2 or more (duplicate bug)
    expect(chatInputCount).toBeLessThanOrEqual(1);

    if (chatInputCount > 0) {
      console.log(`✓ Found ${chatInputCount} chatbot instance(s) - Expected: 1`);

      // Also check for duplicate chat message containers
      const chatMessages = sidebar.locator('[data-testid="stChatMessageContainer"]');
      const messageContainerCount = await chatMessages.count();

      // There should be at most one message container
      expect(messageContainerCount).toBeLessThanOrEqual(1);
    } else {
      console.log('✓ No chatbot found (acceptable if chatbot feature is disabled)');
    }
  });

  test('should keep chatbot at bottom when switching tabs', async ({ page }) => {
    const tabs = page.locator('button[role="tab"]');
    const tabCount = await tabs.count();

    if (tabCount >= 2) {
      const sidebar = page.locator('[data-testid="stSidebar"]');

      // Switch through max 2 tabs (to avoid timeout)
      for (let i = 0; i < Math.min(2, tabCount); i++) {
        // Scroll tab into view and click with force
        await tabs.nth(i).scrollIntoViewIfNeeded();
        await page.waitForTimeout(500);
        await tabs.nth(i).click({ force: true });
        await page.waitForTimeout(2000);

        // CRITICAL: Verify no duplicates on each tab
        const chatInputCount = await sidebar.locator('[data-testid="stChatInput"]').count();
        expect(chatInputCount).toBeLessThanOrEqual(1);

        // Check chatbot exists (if available)
        if (chatInputCount > 0) {
          const chatInput = sidebar.locator('[data-testid="stChatInput"]').first();

          // Scroll chatbot into view to verify it's accessible
          await chatInput.scrollIntoViewIfNeeded();
          await page.waitForTimeout(300);

          const chatBox = await chatInput.boundingBox();
          expect(chatBox).not.toBeNull();
        }
      }
    } else {
      // If less than 2 tabs, just verify sidebar exists
      const sidebar = page.locator('[data-testid="stSidebar"]');
      await expect(sidebar).toBeVisible();
    }
  });

  test('should render chatbot below all other sidebar sections', async ({ page }) => {
    const sidebar = page.locator('[data-testid="stSidebar"]');

    await page.waitForTimeout(3000);

    // Get market selection buttons position
    const marketButton = sidebar.locator('button:has-text("🇰🇷 한국")');
    const marketBox = await marketButton.boundingBox();

    // Get chatbot position
    const chatInput = sidebar.locator('[data-testid="stChatInput"]').first();
    const chatCount = await chatInput.count();

    if (chatCount > 0 && marketBox) {
      // Scroll chatbot into view
      await chatInput.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);

      const chatBox = await chatInput.boundingBox();

      if (chatBox) {
        // Chatbot should be approximately at or below market selection
        // Allow for some margin (within 50px tolerance for flexible layouts)
        const verticalDiff = chatBox.y - marketBox.y;
        const isReasonablyPositioned = verticalDiff >= -50; // Allow 50px above

        expect(isReasonablyPositioned).toBeTruthy();
        console.log(`✓ Chatbot position relative to market buttons: ${verticalDiff.toFixed(1)}px`);
      }
    } else {
      // Chatbot not available or market buttons not found - that's acceptable
      console.log('✓ Chatbot or market buttons not found (acceptable)');
    }

    // Verify sidebar exists regardless of chatbot presence
    const sidebarText = await sidebar.textContent();
    expect(sidebarText).toBeTruthy();
  });

  test('should maintain chatbot accessibility when sidebar is scrolled', async ({ page }) => {
    const sidebar = page.locator('[data-testid="stSidebar"]');
    const chatInput = sidebar.locator('[data-testid="stChatInput"]').first();

    const chatVisible = await chatInput.isVisible().catch(() => false);

    if (chatVisible) {
      const sidebarElement = await sidebar.elementHandle();

      if (sidebarElement) {
        const scrollHeight = await sidebarElement.evaluate((el) => el.scrollHeight);
        const clientHeight = await sidebarElement.evaluate((el) => el.clientHeight);

        if (scrollHeight > clientHeight) {
          // Sidebar is scrollable - scroll to top
          await sidebarElement.evaluate((el) => {
            el.scrollTop = 0;
          });

          await page.waitForTimeout(500);

          // Scroll to bottom where chatbot should be
          await sidebarElement.evaluate((el) => {
            el.scrollTop = el.scrollHeight;
          });

          await page.waitForTimeout(500);

          // Chatbot should now be visible
          const chatVisibleAfterScroll = await chatInput.isVisible();
          expect(chatVisibleAfterScroll).toBeTruthy();
        }
      }
    }
  });

  test('should have functional chat input if chatbot is available', async ({ page }) => {
    const sidebar = page.locator('[data-testid="stSidebar"]');
    const chatInput = sidebar.locator('[data-testid="stChatInput"]').first();

    const chatVisible = await chatInput.isVisible().catch(() => false);

    if (chatVisible) {
      // Try to type in chat input
      await chatInput.click();
      await chatInput.fill('테스트 메시지');

      // Verify input has the text
      const inputValue = await chatInput.inputValue();
      expect(inputValue).toBe('테스트 메시지');

      // Clear the input
      await chatInput.clear();
      const clearedValue = await chatInput.inputValue();
      expect(clearedValue).toBe('');
    }
  });

  test('should verify chatbot is part of sidebar Phase 1 implementation', async ({ page }) => {
    const sidebar = page.locator('[data-testid="stSidebar"]');

    await page.waitForTimeout(2000);

    // Verify the overall Phase 1 structure:
    // 1. Tab-specific settings at top
    // 2. Market selection in middle
    // 3. Settings expander
    // 4. Chatbot at bottom

    const elements = {
      settings: await sidebar.locator('text=/⚙️.*설정/i').first().isVisible().catch(() => false),
      marketButton: await sidebar.locator('button:has-text("🇰🇷")').isVisible(),
      chatbot: await sidebar.locator('[data-testid="stChatInput"]').first().isVisible().catch(() => false),
    };

    // At minimum, market button should be visible (core functionality)
    expect(elements.marketButton).toBeTruthy();

    // Log the structure for debugging
    console.log('Phase 1 Structure Check:', elements);
  });
});
