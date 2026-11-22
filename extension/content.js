/**
 * AEMA Chrome Extension - Content Script
 * Extracts selection context and page metadata for grounding agent queries.
 */

(() => {
  // Listen for extraction requests from extension popup
  chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    if (request.type === 'EXTRACT_PAGE_CONTEXT') {
      const selection = window.getSelection()?.toString()?.trim() || '';
      sendResponse({
        selection,
        title: document.title,
        url: window.location.href,
        metaDescription: document.querySelector('meta[name="description"]')?.getAttribute('content') || '',
      });
      return true;
    }
  });
})();
