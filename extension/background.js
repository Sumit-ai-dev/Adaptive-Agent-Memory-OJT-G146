/**
 * AEMA Chrome Extension - Background Service Worker (Manifest V3)
 * Manages context menus, text clipping, and background badge status.
 */

chrome.runtime.onInstalled.addListener(() => {
  // Create context menu for highlighted text selection
  chrome.contextMenus.create({
    id: 'solve-with-aema',
    title: 'Solve with AEMA Memory',
    contexts: ['selection'],
  });

  console.log('[AEMA Background] Service worker initialized and context menu registered.');
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'solve-with-aema' && info.selectionText) {
    const clip = {
      text: info.selectionText.trim(),
      pageUrl: tab?.url || '',
      pageTitle: tab?.title || '',
      timestamp: Date.now(),
    };

    // Persist clip to extension local storage for popup consumption
    await chrome.storage.local.set({ pendingClip: clip });

    // Set badge to indicate an active clip is queued
    await chrome.action.setBadgeText({ text: '1' });
    await chrome.action.setBadgeBackgroundColor({ color: '#38bdf8' });

    console.log('[AEMA Background] Clipped text saved:', clip);
  }
});

// Listen for messages from popup or content script
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'CLEAR_BADGE') {
    chrome.action.setBadgeText({ text: '' });
    sendResponse({ success: true });
    return true;
  }

  if (message.type === 'GET_STATUS') {
    sendResponse({ active: true, timestamp: Date.now() });
    return true;
  }
});
