# 🚀 Dual Global Release: `aema` v0.1.0 (PyPI) & `aema-memory` v0.1.0 (npm & MCP)

We are thrilled to announce the official open-source release of **AEMA (Reliability-Aware Experiential Memory for Autonomous AI Agents)** across both the Python and Node.js/MCP ecosystems!

Created and developed by **Sumit Das** ([@Sumit-ai-dev](https://github.com/Sumit-ai-dev)) and **Kasat Sakshi Dattaprasad** ([@SakshiKasat18](https://github.com/SakshiKasat18)).

---

## 🎯 What is AEMA?

Standard experiential memory systems in autonomous LLM agents (such as MemGPT, Reflexion, Generative Agents) rank past experiences solely by semantic similarity. When agents encounter deceptive, poisoned, or context-mismatched past trajectories, this naive retrieval triggers **negative transfer**—collapsing agent task accuracy from 100% down to 0%.

**AEMA** solves this by separating **semantic relevance** from **empirical reliability**:
- **Asymmetric Exponential Moving Average (AEMA)**: Updates experiential trust asymmetrically ($S_{t+1} = \alpha S_t + (1-\alpha)$ on verified success, $\beta S_t$ on failure with $\beta < \alpha$).
- **Theorem 1 Deterministic Quarantine**: Automatically isolates persistently harmful memories after $k^* = \lceil \frac{\ln \theta - \ln S_0}{\ln \beta} \rceil$ consecutive failures (3 failures under default hyperparameters $\beta=0.7, \theta=0.35$).
- **Confirmatory Empirical Proof (Phase 8 v2)**: $N=30$ protocol-frozen confirmatory trials demonstrated complete recovery (100% task accuracy at Trial 4, McNemar's exact test $p = 1.192 \times 10^{-7}$) where naive memory collapsed to 0%.

---

## 📦 How to Install and Use

### 1. 🐍 Python SDK (`pip install aema`)
Live on PyPI: [https://pypi.org/project/aema/0.1.0/](https://pypi.org/project/aema/0.1.0/)

```bash
pip install aema
```

```python
from aema import AEMAMemoryManager

# Initialize reliability-aware memory
manager = AEMAMemoryManager(alpha=0.85, beta=0.7, theta=0.35)

# Record experiential outcome
manager.record_outcome(memory_id="mem_42", success=False)

# Query reliable memories (quarantined memories are automatically excluded)
safe_memories = manager.get_active_memories()
```

---

### 2. ⚡ TypeScript SDK & MCP Server (`npm install aema-memory`)
Live on npm: [https://www.npmjs.com/package/aema-memory](https://www.npmjs.com/package/aema-memory)

```bash
npm install aema-memory
```

#### Run CLI directly via npx:
```bash
npx -y -p aema-memory aema status
```

#### Plug into Claude Desktop, Cursor, or Any MCP Client:
Add to your `claude_desktop_config.json` or `cursor/mcp.json`:
```json
{
  "mcpServers": {
    "aema": {
      "command": "npx",
      "args": ["-y", "-p", "aema-memory", "aema-mcp"]
    }
  }
}
```

---

## 🌐 Community & Research Links

- 📄 **Research Paper**: *"Mitigating Negative Transfer in Autonomous Language Agents via Reliability-Aware Experiential Memory"* (IEEE conference format, pre-registration protocol frozen)
- 🤗 **Hugging Face Live Demo**: [https://huggingface.co/spaces/sumitaidev/adaptive-agent-memory](https://huggingface.co/spaces/sumitaidev/adaptive-agent-memory)
- 📊 **Kaggle Benchmark Dataset**: [https://www.kaggle.com/datasets/sumitaidev/agent-memory-confirmatory-benchmark](https://www.kaggle.com/datasets/sumitaidev/agent-memory-confirmatory-benchmark)
- 🐙 **GitHub Repository**: [https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146](https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146)

---

### Acknowledgments & Collaboration
Co-developed and researched by:
- **Sumit Das** ([@Sumit-ai-dev](https://github.com/Sumit-ai-dev)) 
- **Kasat Sakshi Dattaprasad** ([@SakshiKasat18](https://github.com/SakshiKasat18)) 
