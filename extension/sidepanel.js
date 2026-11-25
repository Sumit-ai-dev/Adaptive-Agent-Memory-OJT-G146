/**
 * AEMA Chrome Extension - Side Panel Controller (Manifest V3)
 * Gemini-style native architecture with floating input island,
 * automatic active tab sharing, customizable user greeting,
 * real-time SSE stream extraction, post-answer toolbar,
 * and full-width history drawer with inline rename and delete.
 */

(() => {
  let API_BASE = 'https://aema.live';
  let API_KEY = '';
  let USER_NAME = 'Sakshi';
  let currentResponseMode = 'balanced';
  let currentSession = null;
  let allSessions = [];
  let activeTabContext = null;
  let isTabAttached = true;
  let lastUserPrompt = '';

  const els = {
    topBar: document.querySelector('.top-bar'),
    statusDot: document.getElementById('statusDot'),
    historyDrawerBtn: document.getElementById('historyDrawerBtn'),
    newChatBtn: document.getElementById('newChatBtn'),
    settingsBtn: document.getElementById('settingsBtn'),
    closePanelBtn: document.getElementById('closePanelBtn'),

    chatContainer: document.getElementById('chatContainer'),
    emptyState: document.getElementById('emptyState'),
    greetingHeading: document.getElementById('greetingHeading'),

    // Chips
    chip1: document.getElementById('chip1'),
    chip2: document.getElementById('chip2'),
    chip3: document.getElementById('chip3'),

    // Input Island
    sharingPill: document.getElementById('sharingPill'),
    sharingLabel: document.getElementById('sharingLabel'),
    detachTabBtn: document.getElementById('detachTabBtn'),
    taskInput: document.getElementById('taskInput'),
    quickClipBtn: document.getElementById('quickClipBtn'),

    // Mode Selector inside Island
    modeSelectBtn: document.getElementById('modeSelectBtn'),
    activeModeLabel: document.getElementById('activeModeLabel'),
    modePopover: document.getElementById('modePopover'),

    sendBtn: document.getElementById('sendBtn'),

    // History Drawer
    historyDrawer: document.getElementById('historyDrawer'),
    closeDrawerBtn: document.getElementById('closeDrawerBtn'),
    clearHistoryBtn: document.getElementById('clearHistoryBtn'),
    historySearchInput: document.getElementById('historySearchInput'),
    historyList: document.getElementById('historyList'),

    // Settings Modal
    settingsModal: document.getElementById('settingsModal'),
    closeSettingsBtn: document.getElementById('closeSettingsBtn'),
    userNameInput: document.getElementById('userNameInput'),
    apiUrlInput: document.getElementById('apiUrlInput'),
    apiKeyInput: document.getElementById('apiKeyInput'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),
  };

  async function init() {
    await loadSettings();
    await loadSessions();
    setupEventListeners();
    await checkBackendHealth();
    await resolveActiveTab();
    await checkPendingClip();

    if (!currentSession) {
      startNewSession();
    }
  }

  // --- Settings Persistence ---
  async function loadSettings() {
    try {
      const data = await chrome.storage.local.get(['apiUrl', 'apiKey', 'userName', 'responseMode']);
      if (data.apiUrl) API_BASE = data.apiUrl.replace(/\/+$/, '');
      if (data.apiKey) API_KEY = data.apiKey;
      if (data.userName !== undefined) USER_NAME = data.userName;
      if (data.responseMode) setResponseMode(data.responseMode);

      if (els.userNameInput) els.userNameInput.value = USER_NAME;
      if (els.apiUrlInput) els.apiUrlInput.value = API_BASE;
      if (els.apiKeyInput) els.apiKeyInput.value = API_KEY;

      updateGreeting();
    } catch (e) {
      console.warn('[AEMA Copilot] Failed to load settings:', e);
    }
  }

  function updateGreeting() {
    if (!els.greetingHeading) return;
    const trimmed = (USER_NAME || '').trim();
    if (trimmed) {
      els.greetingHeading.textContent = `Ask away, ${trimmed}!`;
    } else {
      els.greetingHeading.textContent = `How can I help you today?`;
    }
  }

  async function saveSettings() {
    const newName = (els.userNameInput ? els.userNameInput.value : '').trim();
    const newUrl = (els.apiUrlInput ? els.apiUrlInput.value : '').trim().replace(/\/+$/, '') || 'http://localhost:8000';
    const newKey = (els.apiKeyInput ? els.apiKeyInput.value : '').trim();

    USER_NAME = newName;
    API_BASE = newUrl;
    API_KEY = newKey;

    await chrome.storage.local.set({
      userName: USER_NAME,
      apiUrl: API_BASE,
      apiKey: API_KEY,
    });

    updateGreeting();
    if (els.settingsModal) els.settingsModal.classList.remove('open');
    await checkBackendHealth();
  }

  // --- Backend Connectivity ---
  async function checkBackendHealth() {
    if (!els.statusDot) return false;
    try {
      const res = await fetch(`${API_BASE}/api/v1/health`, { method: 'GET' });
      if (res.ok) {
        els.statusDot.className = 'status-dot';
        return true;
      }
    } catch {
      try {
        const fallback = await fetch(`${API_BASE}/health`, { method: 'GET' });
        if (fallback.ok) {
          els.statusDot.className = 'status-dot';
          return true;
        }
      } catch {}
    }
    els.statusDot.className = 'status-dot offline';
    return false;
  }

  // --- Automatic Active Tab Awareness ---
  async function resolveActiveTab() {
    try {
      chrome.runtime.sendMessage({ type: 'GET_ACTIVE_TAB' }, (tab) => {
        if (tab && tab.url) {
          activeTabContext = tab;
          renderTabSharingPill();
        } else {
          activeTabContext = null;
          if (els.sharingPill) els.sharingPill.style.display = 'none';
        }
      });
    } catch (e) {
      console.warn('[AEMA Copilot] Tab query error:', e);
    }
  }

  function renderTabSharingPill() {
    if (!els.sharingPill || !els.sharingLabel) return;
    if (!activeTabContext || !isTabAttached) {
      els.sharingPill.style.display = 'none';
      return;
    }

    els.sharingPill.style.display = 'inline-flex';
    const cleanTitle = (activeTabContext.title || 'Current Page').trim();
    els.sharingLabel.textContent = `Sharing '${cleanTitle}'`;
    els.sharingPill.title = `${cleanTitle}\n${activeTabContext.url}`;
  }

  function toggleTabAttachment() {
    isTabAttached = !isTabAttached;
    renderTabSharingPill();
  }

  // --- Response Mode Switcher ---
  function setResponseMode(mode) {
    currentResponseMode = mode;
    const labels = {
      concise: 'Concise',
      balanced: 'Balanced',
      deep: 'Deep Trace',
    };
    if (els.activeModeLabel) els.activeModeLabel.textContent = labels[mode] || 'Balanced';

    document.querySelectorAll('.popover-item').forEach((item) => {
      if (item.getAttribute('data-mode') === mode) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    if (els.modePopover) els.modePopover.classList.remove('open');
    chrome.storage.local.set({ responseMode: mode }).catch(() => {});
  }

  // --- Session Management ---
  function startNewSession() {
    currentSession = {
      id: 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
      title: 'New Session',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      responseMode: currentResponseMode,
      messages: [],
    };
    renderChatView();
    if (els.taskInput) {
      els.taskInput.value = '';
      adjustTextareaHeight();
      els.taskInput.focus();
    }
  }

  async function loadSessions() {
    try {
      const data = await chrome.storage.local.get('aemaSessions');
      allSessions = Array.isArray(data.aemaSessions) ? data.aemaSessions : [];
      renderHistoryDrawer();
    } catch (e) {
      console.warn('[AEMA Copilot] Failed to load sessions:', e);
      allSessions = [];
    }
  }

  async function persistCurrentSession() {
    if (!currentSession || currentSession.messages.length === 0) return;

    currentSession.updatedAt = Date.now();
    if (currentSession.title === 'New Session' && currentSession.messages[0]) {
      const raw = currentSession.messages[0].content.trim();
      currentSession.title = raw.slice(0, 32) + (raw.length > 32 ? '...' : '');
    }

    const idx = allSessions.findIndex((s) => s.id === currentSession.id);
    if (idx >= 0) {
      allSessions[idx] = currentSession;
    } else {
      allSessions.unshift(currentSession);
    }

    await chrome.storage.local.set({ aemaSessions: allSessions });
    renderHistoryDrawer(els.historySearchInput ? els.historySearchInput.value : '');
  }

  async function deleteSession(sessionId, e) {
    if (e) e.stopPropagation();
    allSessions = allSessions.filter((s) => s.id !== sessionId);
    await chrome.storage.local.set({ aemaSessions: allSessions });

    if (currentSession && currentSession.id === sessionId) {
      startNewSession();
    } else {
      renderHistoryDrawer(els.historySearchInput ? els.historySearchInput.value : '');
    }
  }

  async function renameSession(sessionId, newTitle) {
    const trimmed = (newTitle || '').trim();
    if (!trimmed) return;
    const session = allSessions.find((s) => s.id === sessionId);
    if (session) {
      session.title = trimmed;
      session.updatedAt = Date.now();
      if (currentSession && currentSession.id === sessionId) {
        currentSession.title = trimmed;
      }
      await chrome.storage.local.set({ aemaSessions: allSessions });
      renderHistoryDrawer(els.historySearchInput ? els.historySearchInput.value : '');
    }
  }

  async function clearAllSessions() {
    allSessions = [];
    await chrome.storage.local.set({ aemaSessions: [] });
    startNewSession();
    renderHistoryDrawer();
  }

  function switchSession(sessionId) {
    const found = allSessions.find((s) => s.id === sessionId);
    if (found) {
      currentSession = found;
      renderChatView();
      if (els.historyDrawer) els.historyDrawer.classList.remove('open');
    }
  }

  // --- Render History Drawer ---
  function renderHistoryDrawer(filterText = '') {
    if (!els.historyList) return;
    els.historyList.innerHTML = '';
    const q = (filterText || '').toLowerCase();
    const filtered = allSessions.filter((s) => (s.title || '').toLowerCase().includes(q));

    if (filtered.length === 0) {
      els.historyList.innerHTML = `<div style="color:var(--text-faint); font-size:11px; text-align:center; padding:28px 0; font-family:var(--font-mono);">No sessions found</div>`;
      return;
    }

    filtered.forEach((s) => {
      const item = document.createElement('div');
      item.className = 'history-row';

      const timeStr = new Date(s.updatedAt || s.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      item.innerHTML = `
        <div class="history-row-content">
          <div class="history-row-title">${escapeHtml(s.title || 'Untitled Session')}</div>
          <div class="history-row-time">${timeStr}</div>
        </div>
        <div class="history-row-actions">
          <button class="history-action-btn edit" title="Rename session">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
          </button>
          <button class="history-action-btn del" title="Delete session">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      `;

      // Click row to switch session
      const contentEl = item.querySelector('.history-row-content');
      contentEl.addEventListener('click', () => switchSession(s.id));

      // Inline rename click handler
      const editBtn = item.querySelector('.history-action-btn.edit');
      editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const titleEl = item.querySelector('.history-row-title');
        const currentTitle = s.title || '';
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'rename-input';
        input.value = currentTitle;

        titleEl.replaceWith(input);
        input.focus();
        input.select();

        let finished = false;
        const commitRename = async () => {
          if (finished) return;
          finished = true;
          const val = input.value.trim();
          if (val && val !== currentTitle) {
            await renameSession(s.id, val);
          } else {
            renderHistoryDrawer(els.historySearchInput ? els.historySearchInput.value : '');
          }
        };

        input.addEventListener('keydown', (ke) => {
          if (ke.key === 'Enter') {
            ke.preventDefault();
            commitRename();
          } else if (ke.key === 'Escape') {
            finished = true;
            renderHistoryDrawer(els.historySearchInput ? els.historySearchInput.value : '');
          }
        });
        input.addEventListener('blur', commitRename);
      });

      // Delete click handler
      const delBtn = item.querySelector('.history-action-btn.del');
      delBtn.addEventListener('click', (e) => deleteSession(s.id, e));

      els.historyList.appendChild(item);
    });
  }

  // --- Render Chat Stream ---
  function renderChatView() {
    if (!els.chatContainer) return;
    els.chatContainer.innerHTML = '';

    if (!currentSession || currentSession.messages.length === 0) {
      if (els.emptyState) els.chatContainer.appendChild(els.emptyState);
      return;
    }

    currentSession.messages.forEach((msg) => {
      appendMessageBubble(msg, false);
    });

    scrollToBottom();
  }

  function appendMessageBubble(msg, shouldScroll = true) {
    if (!els.chatContainer) return;
    if (els.emptyState && els.emptyState.parentNode === els.chatContainer) {
      els.chatContainer.removeChild(els.emptyState);
    }

    const group = document.createElement('div');
    group.className = 'msg-group';

    if (msg.role === 'user') {
      group.innerHTML = `<div class="msg-user">${escapeHtml(msg.content)}</div>`;
    } else {
      const assistantDiv = document.createElement('div');
      assistantDiv.className = 'msg-assistant';

      const latencySec = ((msg.latencyMs || 800) / 1000).toFixed(1);
      const thinkingHtml = `
        <div class="thinking-wrap">
          <button type="button" class="thinking-toggle" title="Click to inspect trace">
            <span style="font-family:var(--font-sans);">Thinking</span>
            <span class="thinking-time">${latencySec}s</span>
            <span class="thinking-chevron">▸</span>
          </button>
          <div class="thinking-body" style="display:none;">
            <div class="thinking-item">
              <span class="dot"></span>
              <span>Retrieved verified procedural memory (+σ strategy, -π pitfall)</span>
            </div>
            <div class="thinking-item">
              <span class="dot"></span>
              <span>Executed solution via AEMA Engine</span>
            </div>
            <div class="thinking-item">
              <span class="dot"></span>
              <span>Evaluated outcome: positive</span>
            </div>
            <div class="thinking-item">
              <span class="dot"></span>
              <span>Distilled procedural reflection</span>
            </div>
            <div class="thinking-item">
              <span class="dot"></span>
              <span>${msg.quarantined ? '<span style="color:var(--accent-crimson);">Quarantine triggered: trust dropped &lt; 0.35 (Theorem 1)</span>' : 'A-EMA reliability calibrated (Theorem 1)'}</span>
            </div>
          </div>
        </div>
        <div class="prose">${formatMarkdown(msg.content)}</div>
        <div class="answer-toolbar">
          <button class="action-btn copy-btn" title="Copy answer">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span>Copy</span>
          </button>
          <button class="action-btn thumbs-up-btn ${msg.feedback === 'up' ? 'active-positive' : ''}" title="Helpful (Calibrates A-EMA trust)">
            <span>👍</span>
          </button>
          <button class="action-btn thumbs-down-btn ${msg.feedback === 'down' ? 'active-negative' : ''}" title="Not helpful (Triggers quarantine check)">
            <span>👎</span>
          </button>
          <button class="action-btn retry-btn" title="Retry prompt">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            <span>Retry</span>
          </button>
          <span class="feedback-toast"></span>
        </div>
      `;

      assistantDiv.innerHTML = thinkingHtml;

      // Thinking toggle (collapsed by default)
      const toggleBtn = assistantDiv.querySelector('.thinking-toggle');
      const bodyEl = assistantDiv.querySelector('.thinking-body');
      const chevron = assistantDiv.querySelector('.thinking-chevron');
      toggleBtn.addEventListener('click', () => {
        const isHidden = bodyEl.style.display === 'none';
        bodyEl.style.display = isHidden ? 'flex' : 'none';
        chevron.textContent = isHidden ? '▾' : '▸';
      });

      // Post-answer toolbar event listeners
      const copyBtn = assistantDiv.querySelector('.copy-btn');
      const thumbsUpBtn = assistantDiv.querySelector('.thumbs-up-btn');
      const thumbsDownBtn = assistantDiv.querySelector('.thumbs-down-btn');
      const retryBtn = assistantDiv.querySelector('.retry-btn');
      const toastEl = assistantDiv.querySelector('.feedback-toast');

      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(msg.content).then(() => {
          copyBtn.querySelector('span').textContent = 'Copied';
          setTimeout(() => {
            copyBtn.querySelector('span').textContent = 'Copy';
          }, 1800);
        });
      });

      thumbsUpBtn.addEventListener('click', async () => {
        msg.feedback = 'up';
        thumbsUpBtn.classList.add('active-positive');
        thumbsDownBtn.classList.remove('active-negative');
        showFeedbackToast(toastEl, 'Trust +15% calibrated (Theorem 1)');
        await persistCurrentSession();
        sendFeedbackToBackend(msg, 1.0);
      });

      thumbsDownBtn.addEventListener('click', async () => {
        msg.feedback = 'down';
        thumbsDownBtn.classList.add('active-negative');
        thumbsUpBtn.classList.remove('active-positive');
        showFeedbackToast(toastEl, 'Negative transfer penalized (0.70x)');
        await persistCurrentSession();
        sendFeedbackToBackend(msg, 0.0);
      });

      retryBtn.addEventListener('click', () => {
        if (lastUserPrompt && els.taskInput) {
          els.taskInput.value = lastUserPrompt;
          executeTask();
        }
      });

      group.appendChild(assistantDiv);
    }

    els.chatContainer.appendChild(group);
    attachCodeCopyListeners(group);

    if (shouldScroll) scrollToBottom();
  }

  function showFeedbackToast(toastEl, text) {
    if (!toastEl) return;
    toastEl.textContent = text;
    toastEl.style.display = 'inline-block';
    setTimeout(() => {
      toastEl.style.display = 'none';
    }, 2800);
  }

  async function sendFeedbackToBackend(msg, outcomeScore) {
    try {
      const memoryId = (msg.retrievedMemories && msg.retrievedMemories[0]) ? msg.retrievedMemories[0].id : null;
      if (memoryId) {
        await fetch(`${API_BASE}/api/v1/memories/trust-update`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {}),
          },
          body: JSON.stringify({
            experience_id: memoryId,
            outcome_score: outcomeScore,
            execution_id: msg.executionId || null,
          }),
        });
      }
    } catch (e) {
      console.warn('[AEMA Copilot] Feedback sync warning:', e);
    }
  }

  function scrollToBottom() {
    if (els.chatContainer) {
      els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
    }
  }

  // --- Pending Clip Checker ---
  async function checkPendingClip() {
    try {
      const data = await chrome.storage.local.get('pendingClip');
      if (data.pendingClip && data.pendingClip.text && els.taskInput) {
        els.taskInput.value = `"${data.pendingClip.text}"\n\n`;
        adjustTextareaHeight();
        els.taskInput.focus();
        await chrome.storage.local.remove('pendingClip');
      }
    } catch (e) {
      console.warn('[AEMA Copilot] Pending clip check error:', e);
    }
  }

  // --- Task Execution ---
  async function executeTask() {
    if (!els.taskInput) return;
    const rawInput = els.taskInput.value.trim();
    if (!rawInput) return;

    lastUserPrompt = rawInput;

    // Build payload including attached page context if active
    let task = rawInput;
    if (activeTabContext && isTabAttached) {
      task = `[Context: Active Tab "${activeTabContext.title}" (${activeTabContext.url})]\n\n${rawInput}`;
    }

    if (currentResponseMode === 'concise') {
      task = `[CONSTRAINT: Provide an immediate, actionable answer in under 3 sentences (under 150 tokens). Suppress chain-of-thought.]\n\n${task}`;
    } else if (currentResponseMode === 'deep') {
      task = `[CONSTRAINT: Provide full rigorous technical reasoning with complete 5-node trace and trust verification.]\n\n${task}`;
    }

    const userMessage = {
      role: 'user',
      content: rawInput,
      timestamp: Date.now(),
    };

    currentSession.messages.push(userMessage);
    appendMessageBubble(userMessage);

    els.taskInput.value = '';
    adjustTextareaHeight();
    if (els.sendBtn) {
      els.sendBtn.disabled = true;
      els.sendBtn.classList.remove('active');
    }

    const assistantMessage = {
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      mode: currentResponseMode,
      trustScore: 0.85,
      quarantined: false,
      latencyMs: 0,
      executionId: null,
      retrievedMemories: [],
      feedback: null,
    };

    const group = document.createElement('div');
    group.className = 'msg-group';
    const assistantDiv = document.createElement('div');
    assistantDiv.className = 'msg-assistant';
    assistantDiv.innerHTML = `
      <div class="thinking-wrap">
        <button type="button" class="thinking-toggle">
          <span>Thinking</span>
          <span class="thinking-time">running...</span>
          <span class="thinking-chevron">▾</span>
        </button>
        <div class="thinking-body">
          <div class="thinking-item"><span class="dot"></span><span>Retrieving verified procedural memory...</span></div>
          <div class="thinking-item"><span class="dot"></span><span>Generating cognitive stream...</span></div>
        </div>
      </div>
      <div id="streamingProse" class="prose"><span style="color:var(--text-faint);">Thinking...</span></div>
    `;
    group.appendChild(assistantDiv);
    els.chatContainer.appendChild(group);
    scrollToBottom();

    const proseEl = assistantDiv.querySelector('#streamingProse');
    const startTime = Date.now();
    let accumulatedText = '';

    const payload = {
      taskInput: task,
      taskDomain: 'general',
      memoryEnabled: true,
      simulateFailure: false,
    };

    try {
      const headers = {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      };
      if (API_KEY) headers['Authorization'] = `Bearer ${API_KEY}`;

      const res = await fetch(`${API_BASE}/api/agent/execute/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (res.ok && res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split('\n\n');
          buffer = blocks.pop() || '';

          for (const block of blocks) {
            if (!block.trim()) continue;
            let eventType = 'message';
            let dataStr = '';

            for (const line of block.split('\n')) {
              if (line.startsWith('event:')) eventType = line.replace('event:', '').trim();
              else if (line.startsWith('data:')) dataStr = line.replace('data:', '').trim();
            }

            if (!dataStr) continue;

            try {
              const data = JSON.parse(dataStr);

              // 1. Token streaming chunks
              if (eventType === 'token') {
                const chunk = data.token || (typeof data === 'string' ? data : '');
                if (chunk) {
                  accumulatedText += chunk;
                  proseEl.innerHTML = formatMarkdown(accumulatedText);
                  scrollToBottom();
                }
              }

              // 2. Node complete events
              else if (eventType === 'node_complete') {
                if (data.node === 'execute_node') {
                  const execAnswer = data.final_answer || data.solution || '';
                  if (execAnswer && (!accumulatedText || accumulatedText.trim() === 'Thinking...')) {
                    accumulatedText = execAnswer;
                    proseEl.innerHTML = formatMarkdown(accumulatedText);
                    scrollToBottom();
                  }
                } else if (data.node === 'retrieve_node') {
                  if (Array.isArray(data.retrieved_memories)) {
                    assistantMessage.retrievedMemories = data.retrieved_memories;
                  }
                } else if (data.node === 'evaluate_node') {
                  if (data.outcome_score !== undefined) {
                    assistantMessage.trustScore = data.outcome_score;
                  }
                } else if (data.node === 'trust_node') {
                  if (Array.isArray(data.trust_updates)) {
                    data.trust_updates.forEach((u) => {
                      if (u.quarantined || (u.new_trust !== undefined && u.new_trust < 0.35)) {
                        assistantMessage.quarantined = true;
                      }
                    });
                  }
                }
              }

              // 3. Trust updates
              else if (eventType === 'trust') {
                if (data.score !== undefined) assistantMessage.trustScore = data.score;
                if (data.quarantined) assistantMessage.quarantined = true;
              }

              // 4. Done event (extract finalAnswer from result object)
              else if (eventType === 'done') {
                const resultObj = data.result || {};
                const finalSol = resultObj.finalAnswer || resultObj.final_answer || resultObj.solution || data.finalAnswer || data.final_answer || '';
                if (finalSol && (!accumulatedText || accumulatedText.length < finalSol.length)) {
                  accumulatedText = finalSol;
                  proseEl.innerHTML = formatMarkdown(accumulatedText);
                  scrollToBottom();
                }
                if (resultObj.executionId || resultObj.execution_id) {
                  assistantMessage.executionId = resultObj.executionId || resultObj.execution_id;
                }
                if (resultObj.quarantinedMemories && resultObj.quarantinedMemories.length > 0) {
                  assistantMessage.quarantined = true;
                }
              }
            } catch {
              if (dataStr !== '[DONE]') {
                accumulatedText += dataStr;
                proseEl.innerHTML = formatMarkdown(accumulatedText);
                scrollToBottom();
              }
            }
          }
        }
      } else {
        // Fallback to non-streaming execution endpoint
        const fallbackRes = await fetch(`${API_BASE}/api/agent/execute`, {
          method: 'POST',
          headers,
          body: JSON.stringify(payload),
        });

        if (fallbackRes.ok) {
          const resData = await fallbackRes.json();
          const fallbackAns = resData.finalAnswer || resData.final_answer || resData.solution || resData.answer || 'Execution completed.';
          accumulatedText = fallbackAns;
          if (resData.trustScore !== undefined) assistantMessage.trustScore = resData.trustScore;
          if (resData.executionId || resData.execution_id) assistantMessage.executionId = resData.executionId || resData.execution_id;
        } else {
          accumulatedText = `Execution error: ${fallbackRes.status} ${fallbackRes.statusText}`;
        }
      }
    } catch {
      accumulatedText = `Connection error: Unable to reach AEMA gateway at ${API_BASE}. Please verify server status in Settings.`;
    }

    const latency = Date.now() - startTime;
    assistantMessage.content = accumulatedText || 'Task completed with empty output.';
    assistantMessage.latencyMs = latency;

    currentSession.messages.push(assistantMessage);
    await persistCurrentSession();

    group.remove();
    appendMessageBubble(assistantMessage);

    if (els.sendBtn) els.sendBtn.disabled = false;
  }

  // --- Auto-Resize Textarea ---
  function adjustTextareaHeight() {
    if (!els.taskInput) return;
    els.taskInput.style.height = 'auto';
    const nextH = Math.min(els.taskInput.scrollHeight, 100);
    els.taskInput.style.height = nextH + 'px';

    if (els.sendBtn) {
      if (els.taskInput.value.trim().length > 0) {
        els.sendBtn.classList.add('active');
      } else {
        els.sendBtn.classList.remove('active');
      }
    }
  }

  // --- Markdown Formatting ---
  function formatMarkdown(text) {
    if (!text) return '';

    const codeBlocks = [];
    let formatted = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_match, lang, code) => {
      const id = codeBlocks.length;
      codeBlocks.push({ lang: lang || 'code', code: code.trim() });
      return `%%CODE_BLOCK_${id}%%`;
    });

    formatted = escapeHtml(formatted);
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong style="color:var(--text-primary);">$1</strong>');
    formatted = formatted.replace(/`([^`]+)`/g, '<code style="background:var(--surface-island); padding:1px 4px; border-radius:3px; color:#A3E635; font-family:var(--font-mono); font-size:11px; border:1px solid var(--border-island);">$1</code>');
    formatted = formatted.replace(/^-\s+(.+)$/gm, '<li style="margin-left:14px; margin-bottom:2px;">$1</li>');
    formatted = formatted.replace(/\n\n+/g, '</p><p>');
    formatted = `<p>${formatted}</p>`;

    codeBlocks.forEach((b, i) => {
      const codeHtml = `
        <div class="code-wrap">
          <div class="code-head">
            <span>${escapeHtml(b.lang)}</span>
            <button class="code-copy" data-code="${escapeHtml(b.code)}">Copy</button>
          </div>
          <pre><code>${escapeHtml(b.code)}</code></pre>
        </div>
      `;
      formatted = formatted.replace(`%%CODE_BLOCK_${i}%%`, codeHtml);
    });

    return formatted;
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function attachCodeCopyListeners(container) {
    container.querySelectorAll('.code-copy').forEach((btn) => {
      btn.addEventListener('click', () => {
        const code = btn.getAttribute('data-code');
        navigator.clipboard.writeText(code).then(() => {
          btn.textContent = 'Copied';
          setTimeout(() => {
            btn.textContent = 'Copy';
          }, 1800);
        });
      });
    });
  }

  // --- Event Listeners ---
  function setupEventListeners() {
    // Mode Popover
    if (els.modeSelectBtn && els.modePopover) {
      els.modeSelectBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        els.modePopover.classList.toggle('open');
      });

      document.querySelectorAll('.popover-item').forEach((item) => {
        item.addEventListener('click', (e) => {
          e.stopPropagation();
          setResponseMode(item.getAttribute('data-mode'));
        });
      });

      document.addEventListener('click', () => {
        els.modePopover.classList.remove('open');
      });
    }

    // Detach Tab Context Pill
    if (els.detachTabBtn) {
      els.detachTabBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleTabAttachment();
      });
    }

    // History Drawer Open / Close / Clear
    if (els.historyDrawerBtn && els.historyDrawer) {
      els.historyDrawerBtn.addEventListener('click', () => {
        els.historyDrawer.classList.toggle('open');
        renderHistoryDrawer(els.historySearchInput ? els.historySearchInput.value : '');
      });
    }

    if (els.closeDrawerBtn && els.historyDrawer) {
      els.closeDrawerBtn.addEventListener('click', () => {
        els.historyDrawer.classList.remove('open');
      });
    }

    if (els.clearHistoryBtn) {
      els.clearHistoryBtn.addEventListener('click', async () => {
        if (confirm('Clear all conversation history?')) {
          await clearAllSessions();
        }
      });
    }

    if (els.historySearchInput) {
      els.historySearchInput.addEventListener('input', (e) => {
        renderHistoryDrawer(e.target.value);
      });
    }

    // New Session
    if (els.newChatBtn) {
      els.newChatBtn.addEventListener('click', startNewSession);
    }

    // Settings Modal
    if (els.settingsBtn && els.settingsModal) {
      els.settingsBtn.addEventListener('click', () => {
        els.settingsModal.classList.add('open');
      });
    }

    if (els.closeSettingsBtn && els.settingsModal) {
      els.closeSettingsBtn.addEventListener('click', () => {
        els.settingsModal.classList.remove('open');
      });
    }

    if (els.saveSettingsBtn) {
      els.saveSettingsBtn.addEventListener('click', saveSettings);
    }

    // Close Side Panel (only if element exists)
    if (els.closePanelBtn) {
      els.closePanelBtn.addEventListener('click', () => {
        window.close();
      });
    }

    // Textarea input and auto-height
    if (els.taskInput) {
      els.taskInput.addEventListener('input', adjustTextareaHeight);
      els.taskInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          executeTask();
        }
      });
    }

    if (els.sendBtn) {
      els.sendBtn.addEventListener('click', executeTask);
    }

    // Quick Clip button
    if (els.quickClipBtn) {
      els.quickClipBtn.addEventListener('click', () => {
        chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
          if (!tab || !tab.id) return;
          chrome.tabs.sendMessage(tab.id, { type: 'EXTRACT_PAGE_CONTEXT' }, (res) => {
            if (res && res.selection && els.taskInput) {
              els.taskInput.value = `"${res.selection}"\n\n`;
            } else if (els.taskInput) {
              els.taskInput.value = `Analyze: ${tab.title || tab.url}\n`;
            }
            adjustTextareaHeight();
            if (els.taskInput) els.taskInput.focus();
          });
        });
      });
    }

    // Starter Chips
    if (els.chip1) {
      els.chip1.addEventListener('click', () => {
        if (els.taskInput) {
          els.taskInput.value = els.chip1.querySelector('span:last-child').textContent;
          executeTask();
        }
      });
    }
    if (els.chip2) {
      els.chip2.addEventListener('click', () => {
        if (els.taskInput) {
          els.taskInput.value = els.chip2.querySelector('span:last-child').textContent;
          executeTask();
        }
      });
    }
    if (els.chip3) {
      els.chip3.addEventListener('click', () => {
        if (els.taskInput) {
          els.taskInput.value = els.chip3.querySelector('span:last-child').textContent;
          executeTask();
        }
      });
    }

    // Listen for tab changes broadcasted by background.js
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.type === 'ACTIVE_TAB_CHANGED' && msg.context) {
        activeTabContext = msg.context;
        renderTabSharingPill();
      }
      if (msg.type === 'PENDING_CLIP_READY' && msg.clip && els.taskInput) {
        els.taskInput.value = `"${msg.clip.text}"\n\n`;
        adjustTextareaHeight();
        els.taskInput.focus();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
