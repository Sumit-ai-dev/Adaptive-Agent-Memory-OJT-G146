# AEMA (Adaptive Experience Memory Agent)

[![npm version](https://img.shields.io/npm/v/aema.svg?color=blue)](https://www.npmjs.com/package/aema)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Ready](https://img.shields.io/badge/MCP-Standard%20v1.0-purple)](https://modelcontextprotocol.io)
[![Docker Pulls](https://img.shields.io/docker/pulls/aema/mcp.svg?color=brightgreen)](https://hub.docker.com/r/aema/mcp)

> **Reliability-Aware Experiential Memory for Autonomous AI Agents**  
> *Isolating Negative Transfer via Asymmetric Exponential Moving Average (A-EMA) and Theorem 1 Quarantine Bounds.*

---

## What is AEMA?

Standard retrieval-augmented generation (RAG) and agent memory architectures retrieve past experiences based solely on **semantic similarity**. When an agent recalls a flawed, poisoned, or contextually invalid solution, it blindly repeats past mistakes—a catastrophic failure mode known as **negative transfer**.

**AEMA** introduces a robust reliability and memory lifecycle layer:
1. **Asymmetric EMA Trust Tracking**: Fast penalty on failure ($\beta = 0.70$), cautious reinforcement on success ($\alpha = 0.85$).
2. **Theorem 1 Deterministic Quarantine**: Automatically isolates degraded memories into an inactive state when trust drops below the threshold ($\theta = 0.35$).
3. **Write-Ahead Logging (WAL)**: Immutable append-only audit trail logging every memory mutation, decay step, and quarantine event.
4. **Offline Memory Deduplication**: Token-level clustering and deduplication sweeps to merge redundant memories while preserving the highest-trust experience.
5. **System Health & Risk Audit**: Automated diagnostic reporting calculating average trust, quarantine ratios, and the Negative Transfer Risk Index.
6. **MCP Native Protocol**: Plug directly into **Claude Desktop**, **Cursor**, **Windsurf**, or custom LangChain/LangGraph pipelines.

---

## 🚀 Quick Start

### 1. Installation

```bash
npm install aema
```

Or run directly with `npx`:

```bash
# Start MCP server over stdio
npx aema-mcp

# Or inspect system status via CLI
npx aema status

# Run full memory bank health audit
npx aema audit

# Deduplicate redundant memory traces
npx aema dedup --dry-run
```

---

## 🤖 Multi-LLM Ecosystem Integration

AEMA provides first-class support for **Claude**, **Cursor**, **OpenAI**, **Grok**, and **Google Gemini**:

### 1. Claude Desktop & Claude Code (via MCP)
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "aema-memory": {
      "command": "npx",
      "args": ["-y", "aema-mcp"]
    }
  }
}
```

### 2. Cursor IDE (via MCP or `.cursor-plugin`)
Add to `.cursor/mcp.json` or enable the included `.cursor-plugin`:
```json
{
  "mcpServers": {
    "aema-memory": {
      "command": "npx",
      "args": ["-y", "aema-mcp"]
    }
  }
}
```

### 3. OpenAI (GPT-4o, o1, o3-mini)
```typescript
import OpenAI from 'openai';
import { openAITools, handleOpenAIToolCall } from 'aema';

const openai = new OpenAI();

const response = await openai.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'How do I handle React SSR hydration error?' }],
  tools: openAITools,
});

// Dispatch tool call directly
for (const call of response.choices[0].message.tool_calls || []) {
  const result = await handleOpenAIToolCall(call.function.name, JSON.parse(call.function.arguments));
  console.log('AEMA Memory Output:', result);
}
```

### 4. Grok / xAI (Grok-2, Grok-3)
xAI uses OpenAI-compatible schemas. Simply point the OpenAI SDK to `https://api.x.ai/v1`:
```typescript
import OpenAI from 'openai';
import { grokTools, handleOpenAIToolCall } from 'aema';

const grok = new OpenAI({
  baseURL: 'https://api.x.ai/v1',
  apiKey: process.env.XAI_API_KEY,
});

const response = await grok.chat.completions.create({
  model: 'grok-2-latest',
  messages: [{ role: 'user', content: 'Debug memory leaks in Python asyncio.' }],
  tools: grokTools,
});
```

### 5. Google Gemini (Gemini 1.5 Pro, 2.0 Flash)
```typescript
import { GoogleGenerativeAI } from '@google/generative-ai';
import { geminiTools, handleGeminiToolCall } from 'aema';

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
const model = genAI.getGenerativeModel({
  model: 'gemini-2.0-flash',
  tools: geminiTools,
});

const chat = model.startChat();
const result = await chat.sendMessage('Find reliable past solutions for PostgreSQL indexing.');
// Handle function calls via handleGeminiToolCall(name, args)
```

---

## 🛠️ MCP Tools Overview

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `aema_retrieve` | `query`, `topK`, `minTrust`, `domain` | Retrieves non-quarantined, verified experiences ranked by reliability |
| `aema_store` | `task`, `solution`, `initialTrust`, `domain` | Records execution traces with initial trust score and logs to WAL |
| `aema_feedback` | `experienceId`, `outcome` (`success`/`failure`) | Updates trust via A-EMA; activates Theorem 1 quarantine if score decays below 0.35 |
| `aema_audit` | *(none)* | Comprehensive health diagnostics and Negative Transfer Risk Index |
| `aema_dedup` | `threshold`, `dryRun`, `domain` | Offline deduplication sweep merging redundant memories |
| `aema_wal` | `limit` | Inspects recent immutable Write-Ahead Log audit entries |
| `aema_status` | *(none)* | Displays active trust parameters, quarantined count, and system health |

---

## 💻 TypeScript / JavaScript SDK

```typescript
import { AEMAClient, calculateAsymmetricEMA, isQuarantined } from 'aema';

// 1. Initialize client
const memory = new AEMAClient();

// 2. Store an experiential memory
const exp = await memory.store({
  task: 'Fix React hydration mismatch in Next.js SSR',
  solution: 'Use useEffect or dynamic import with ssr: false for browser-only APIs.',
  initialTrust: 1.0,
  metadata: { domain: 'coding' },
});

// 3. Retrieve verified, non-quarantined memories
const results = await memory.retrieve({ query: 'React hydration bug', domain: 'coding' });
for (const match of results) {
  console.log(`[Rank: ${match.effectiveScore}] ${match.experience.task}`);
}

// 4. Record execution outcome (updates trust via A-EMA & logs to WAL)
const feedback = await memory.recordFeedback(exp.id, 'failure');
if (feedback.isQuarantined) {
  console.warn('Memory quarantined to prevent negative transfer!');
}

// 5. Run health audit
const report = memory.audit();
console.log(`Memory Health: ${report.healthStatus}, Risk: ${report.negativeTransferRiskScore}`);
```

---

## 📐 Mathematical Formulation

### Asymmetric Exponential Moving Average (A-EMA)
For trial $t$ with outcome $y_t \in \{0, 1\}$:

$$
S_{t+1} = 
\begin{cases} 
\alpha S_t + (1 - \alpha) & \text{if } y_t = 1 \text{ (Success)} \\
\beta S_t & \text{if } y_t = 0 \text{ (Failure)}
\end{cases}
$$

Where default parameters are calibrated to:
* $\alpha = 0.85$ (conservative trust recovery)
* $\beta = 0.70$ (strict failure penalty)
* $\theta = 0.35$ (quarantine cutoff)

### Theorem 1 (Quarantine Guarantee)
Any experiential memory starting at initial score $S_0$ that experiences $k$ consecutive execution failures enters deterministic quarantine ($S_k < \theta$) in exactly:

$$
k^* = \left\lceil \frac{\ln(\theta / S_0)}{\ln \beta} \right\rceil \text{ steps}
$$

For default parameters ($S_0 = 1.0, \theta = 0.35, \beta = 0.70$):
$$
k^* = \lceil -1.0498 / -0.3567 \rceil = 3 \text{ consecutive failures}
$$

---

## 📦 Multi-Language Ecosystem

| Registry | Package | Command |
| :--- | :--- | :--- |
| **npm** | `aema` | `npm install aema` |
| **PyPI** | `aema` | `pip install aema` |
| **Docker Hub** | `aema/mcp` | `docker run -i --rm aema/mcp` |

---

## 📄 Academic Citation

If you use AEMA in your research or production agents, please cite our conference paper:

```bibtex
@inproceedings{das2026aema,
  title={Mitigating Negative Transfer in Autonomous Language Agents via Reliability-Aware Experiential Memory},
  author={Das, Sumit and Kasat, Sakshi Dattaprasad},
  booktitle={IEEE Conference Proceedings},
  year={2026}
}
```

## ⚖️ License
MIT License © 2026 Sumit Das and Kasat Sakshi Dattaprasad.
