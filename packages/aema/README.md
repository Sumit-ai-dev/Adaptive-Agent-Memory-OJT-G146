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

**AEMA** introduces a reliability layer:
1. **Asymmetric EMA Trust Tracking**: Fast penalty on failure ($\beta = 0.70$), cautious reinforcement on success ($\alpha = 0.85$).
2. **Theorem 1 Deterministic Quarantine**: Automatically isolates degraded memories into an inactive state when trust drops below the threshold ($\theta = 0.35$).
3. **MCP Native Protocol**: Plug directly into **Claude Desktop**, **Cursor**, **Windsurf**, or custom LangChain/LangGraph pipelines.

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
```

---

## 🤖 Use with Claude Desktop & Cursor (MCP)

AEMA implements the official [Model Context Protocol (MCP)](https://modelcontextprotocol.io) specification.

### Claude Desktop Configuration
Add the following to your `claude_desktop_config.json`:

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

### Cursor IDE Configuration
Add to `.cursor/mcp.json`:

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

### Docker Execution
Run the isolated container without local Node.js:

```bash
docker run -i --rm aema/mcp
```

---

## 💻 TypeScript / JavaScript SDK

```typescript
import { AEMAClient, calculateAsymmetricEMA, isQuarantined } from 'aema';

// 1. Initialize client
const memory = new AEMAClient();

// 2. Store an experiential memory
const exp = await memory.store({
  task: 'Fix React hydratation mismatch in Next.js SSR',
  solution: 'Use useEffect or dynamic import with ssr: false for browser-only APIs.',
  initialTrust: 1.0,
});

// 3. Retrieve verified, non-quarantined memories
const results = await memory.retrieve('React hydration bug');
for (const match of results) {
  console.log(`[Rank: ${match.effectiveScore}] ${match.experience.task}`);
}

// 4. Record execution outcome (updates trust via A-EMA)
const feedback = await memory.recordFeedback(exp.id, 'failure');
if (feedback.isQuarantined) {
  console.warn('Memory quarantined to prevent negative transfer!');
}
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
