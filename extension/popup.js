/**
 * AEMA Chrome Extension - Popup Controller
 * Connects to AEMA FastAPI gateway with real-time SSE streaming,
 * updates the 5-node cognitive stepper, and handles page clip queries.
 */

const API_BASE = 'https://aema.live';

const els = {
  statusDot: document.getElementById('statusDot'),
  statusText: document.getElementById('statusText'),
  domainSelect: document.getElementById('domainSelect'),
  memoryToggle: document.getElementById('memoryToggle'),
  trapToggle: document.getElementById('trapToggle'),
  clipBanner: document.getElementById('clipBanner'),
  clipSourceLabel: document.getElementById('clipSourceLabel'),
  dismissClipBtn: document.getElementById('dismissClipBtn'),
  taskInput: document.getElementById('taskInput'),
  executeBtn: document.getElementById('executeBtn'),
  metricsLabel: document.getElementById('metricsLabel'),
  cycleStatus: document.getElementById('cycleStatus'),
  outputContent: document.getElementById('outputContent'),
  copyBtn: document.getElementById('copyBtn'),
  clearBtn: document.getElementById('clearBtn'),
  // Stepper nodes
  nodeRetrieve: document.getElementById('nodeRetrieve'),
  nodeRetrieveVal: document.getElementById('nodeRetrieveVal'),
  nodeExecute: document.getElementById('nodeExecute'),
  nodeExecuteVal: document.getElementById('nodeExecuteVal'),
  nodeEvaluate: document.getElementById('nodeEvaluate'),
  nodeEvaluateVal: document.getElementById('nodeEvaluateVal'),
  nodeReflect: document.getElementById('nodeReflect'),
  nodeReflectVal: document.getElementById('nodeReflectVal'),
  nodeTrust: document.getElementById('nodeTrust'),
  nodeTrustVal: document.getElementById('nodeTrustVal'),
};

// Check backend connectivity on mount
async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
    if (res.ok) {
      els.statusDot.classList.remove('offline');
      els.statusText.textContent = 'Online';
      return true;
    }
  } catch {
    // try fallback route
    try {
      const res2 = await fetch(`${API_BASE}/api/v1/health`, { method: 'GET' });
      if (res2.ok) {
        els.statusDot.classList.remove('offline');
        els.statusText.textContent = 'Online';
        return true;
      }
    } catch {}
  }
  els.statusDot.classList.add('offline');
  els.statusText.textContent = 'Offline';
  return false;
}

// Reset stepper nodes
function resetStepper() {
  const nodes = [els.nodeRetrieve, els.nodeExecute, els.nodeEvaluate, els.nodeReflect, els.nodeTrust];
  nodes.forEach((n) => {
    n.className = 'stepper-node';
  });
  els.nodeRetrieveVal.textContent = '-';
  els.nodeExecuteVal.textContent = '-';
  els.nodeEvaluateVal.textContent = '-';
  els.nodeReflectVal.textContent = '-';
  els.nodeTrustVal.textContent = '-';
  els.cycleStatus.textContent = 'Idle';
}

// Load pending clipped text from background storage
async function loadPendingClip() {
  try {
    const data = await chrome.storage.local.get('pendingClip');
    if (data.pendingClip && data.pendingClip.text) {
      els.taskInput.value = data.pendingClip.text;
      els.clipBanner.style.display = 'flex';
      els.clipSourceLabel.textContent = `Clipped: ${data.pendingClip.pageTitle || 'Selection'}`;
      await chrome.storage.local.remove('pendingClip');
      chrome.runtime.sendMessage({ type: 'CLEAR_BADGE' });
    }
  } catch (err) {
    console.warn('[AEMA Popup] Could not load pending clip:', err);
  }
}

// Stream task execution via Server-Sent Events
async function executeTask() {
  const task = els.taskInput.value.trim();
  if (!task) {
    els.taskInput.focus();
    return;
  }

  resetStepper();
  els.outputContent.innerHTML = '';
  els.executeBtn.disabled = true;
  els.cycleStatus.textContent = 'Running...';
  els.metricsLabel.textContent = 'Executing cycle...';

  els.nodeRetrieve.classList.add('active');
  els.nodeRetrieveVal.textContent = 'Querying...';

  const payload = {
    taskInput: task,
    taskDomain: els.domainSelect.value,
    memoryEnabled: els.memoryToggle.checked,
    simulateFailure: els.trapToggle.checked,
  };

  const startTime = Date.now();
  let fullOutput = '';
  let streamWorked = false;

  try {
    const res = await fetch(`${API_BASE}/api/agent/execute/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(payload),
    });

    if (res.ok && res.body) {
      streamWorked = true;
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
            if (line.startsWith('event: ')) eventType = line.slice(7).trim();
            else if (line.startsWith('data: ')) dataStr = line.slice(6).trim();
          }

          if (!dataStr) continue;

          try {
            const parsed = JSON.parse(dataStr);

            if (eventType === 'token' && parsed.chunk) {
              fullOutput += parsed.chunk;
              els.outputContent.textContent = fullOutput;
              els.outputContent.scrollTop = els.outputContent.scrollHeight;
            } else if (eventType === 'node_complete') {
              handleNodeComplete(parsed);
            } else if (eventType === 'done' && parsed.result) {
              handleExecutionComplete(parsed.result, startTime);
            } else if (eventType === 'error') {
              els.cycleStatus.textContent = 'Error';
              els.outputContent.textContent = `Error: ${parsed.error || 'Execution failed'}`;
            }
          } catch {
            // Raw text line
          }
        }
      }
    }
  } catch (err) {
    console.warn('[AEMA Popup] Streaming error, falling back to blocking endpoint:', err);
  }

  // Fallback if SSE streaming failed or produced no output
  if (!streamWorked || !fullOutput) {
    try {
      els.nodeExecute.classList.add('active');
      const res = await fetch(`${API_BASE}/api/agent/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      handleExecutionComplete(data, startTime);
    } catch (fallbackErr) {
      els.cycleStatus.textContent = 'Failed';
      els.outputContent.textContent = `Execution failed: ${fallbackErr.message}`;
    }
  }

  els.executeBtn.disabled = false;
}

function handleNodeComplete(parsed) {
  const node = parsed.node;
  if (node === 'retrieve_node') {
    els.nodeRetrieve.className = 'stepper-node complete';
    const count = parsed.retrieved_count ?? (parsed.retrieved_memories ? parsed.retrieved_memories.length : 0);
    els.nodeRetrieveVal.textContent = `${count} hit${count === 1 ? '' : 's'}`;
    els.nodeExecute.className = 'stepper-node active';
    els.nodeExecuteVal.textContent = 'Solving...';
  } else if (node === 'execute_node') {
    els.nodeExecute.className = 'stepper-node complete';
    els.nodeExecuteVal.textContent = `${parsed.latency_ms || 250}ms`;
    els.nodeEvaluate.className = 'stepper-node active';
    els.nodeEvaluateVal.textContent = 'Verifying...';
  } else if (node === 'evaluate_node') {
    const isSuccess = parsed.outcome === 'success' || parsed.outcome_score > 0.5;
    els.nodeEvaluate.className = `stepper-node ${isSuccess ? 'complete' : 'failed'}`;
    els.nodeEvaluateVal.textContent = isSuccess ? 'PASS' : 'FAIL';
    els.nodeReflect.className = 'stepper-node active';
    els.nodeReflectVal.textContent = 'Distilling...';
  } else if (node === 'reflect_node') {
    els.nodeReflect.className = 'stepper-node complete';
    els.nodeReflectVal.textContent = parsed.has_lesson ? 'Lesson' : 'Skipped';
    els.nodeTrust.className = 'stepper-node active';
    els.nodeTrustVal.textContent = 'Calibrating...';
  } else if (node === 'trust_node' || node === 'trust_update_node') {
    els.nodeTrust.className = 'stepper-node complete';
    els.nodeTrustVal.textContent = 'Updated';
  }
}

function handleExecutionComplete(result, startTime) {
  const elapsed = Date.now() - startTime;
  els.cycleStatus.textContent = 'Completed';
  els.metricsLabel.textContent = `${elapsed}ms | ${result.tokens_used || result.tokensUsed || 0} tokens`;

  // Ensure all stepper nodes show complete state
  [els.nodeRetrieve, els.nodeExecute, els.nodeEvaluate, els.nodeReflect, els.nodeTrust].forEach((n) => {
    if (!n.classList.contains('failed')) {
      n.className = 'stepper-node complete';
    }
  });

  const finalAnswer = result.final_output || result.finalOutput || result.solution || '';
  if (finalAnswer && !els.outputContent.textContent) {
    els.outputContent.textContent = finalAnswer;
  }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  checkBackendHealth();
  loadPendingClip();

  els.executeBtn.addEventListener('click', executeTask);

  els.taskInput.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      executeTask();
    }
  });

  els.dismissClipBtn.addEventListener('click', () => {
    els.clipBanner.style.display = 'none';
  });

  els.clearBtn.addEventListener('click', () => {
    els.taskInput.value = '';
    els.outputContent.innerHTML = '<span class="output-placeholder">Agent outputs and streaming tokens appear here...</span>';
    resetStepper();
    els.metricsLabel.textContent = 'Ctrl+Enter to run';
  });

  els.copyBtn.addEventListener('click', async () => {
    const text = els.outputContent.textContent;
    if (text && !text.includes('appear here...')) {
      await navigator.clipboard.writeText(text);
      const prev = els.copyBtn.textContent;
      els.copyBtn.textContent = 'Copied!';
      setTimeout(() => {
        els.copyBtn.textContent = prev;
      }, 1500);
    }
  });
});
