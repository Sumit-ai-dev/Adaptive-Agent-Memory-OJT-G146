/**
 * AEMA Chrome Extension - Background Service Worker (Manifest V3)
 * Orchestrates Side Panel behavior, active tab tracking, text clipping,
 * and cross-tab context menus.
 */

// Automatically open Side Panel upon clicking the extension toolbar icon
if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error('[AEMA Background] setPanelBehavior failed:', error));
}

chrome.runtime.onInstalled.addListener(() => {
  // Create context menu for highlighted text selection
  chrome.contextMenus.create({
    id: 'solve-with-aema',
    title: 'Solve with AEMA Memory',
    contexts: ['selection'],
  });

  console.log('[AEMA Background] Service worker initialized with Side Panel support.');
  updateActiveTabContext();
});

// Active tab tracking for zero-click "Sharing '<tab>'" context
async function updateActiveTabContext(tabId) {
  try {
    let tab = null;
    if (tabId) {
      tab = await chrome.tabs.get(tabId);
    } else {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      tab = tabs[0];
    }

    if (tab && tab.url && !tab.url.startsWith('chrome://')) {
      const context = {
        title: tab.title || 'Current Page',
        url: tab.url,
        favIconUrl: tab.favIconUrl || '',
        id: tab.id,
      };
      await chrome.storage.local.set({ activeTabContext: context });
      chrome.runtime.sendMessage({ type: 'ACTIVE_TAB_CHANGED', context }).catch(() => {});
    }
  } catch (err) {
    // Suppress errors on restricted Chrome internal tabs
  }
}

chrome.tabs.onActivated.addListener((activeInfo) => {
  updateActiveTabContext(activeInfo.tabId);
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab?.active) {
    updateActiveTabContext(tabId);
  }
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'solve-with-aema' && tab?.id) {
    if (chrome.sidePanel && chrome.sidePanel.open) {
      try {
        await chrome.sidePanel.open({ tabId: tab.id });
      } catch (err) {
        console.warn('[AEMA Background] Failed to open side panel directly:', err);
      }
    }

    const clip = {
      text: (info.selectionText || '').trim(),
      pageUrl: tab.url || '',
      pageTitle: tab.title || '',
      timestamp: Date.now(),
    };

    await chrome.storage.local.set({ pendingClip: clip });
    chrome.runtime.sendMessage({ type: 'PENDING_CLIP_READY', clip }).catch(() => {});
    console.log('[AEMA Background] Context menu clipped text saved:', clip);
  }
});

// Message relay
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'GET_ACTIVE_TAB') {
    chrome.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
      const tab = tabs[0];
      if (tab && tab.url && !tab.url.startsWith('chrome://')) {
        sendResponse({
          title: tab.title || 'Current Page',
          url: tab.url,
          favIconUrl: tab.favIconUrl || '',
          id: tab.id,
        });
      } else {
        sendResponse(null);
      }
    });
    return true;
  }

  if (message.type === 'CLEAR_BADGE') {
    chrome.action.setBadgeText({ text: '' }).catch(() => {});
    sendResponse({ success: true });
    return true;
  }
});
