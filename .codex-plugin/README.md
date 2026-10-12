# AEMA — Codex CLI Plugin

Integrate **AEMA (Reliability-Aware Experiential Memory)** directly into OpenAI Codex and Codex CLI.

## Prerequisites

- Node.js 18+ (or npx)
- Codex CLI configured

## Installation

Add the plugin to Codex:

```bash
codex plugin add aema@Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146
```

Or configure manually in your Codex CLI configuration (`~/.codex/config.json`):

```json
{
  "mcpServers": {
    "aema": {
      "command": "npx",
      "args": ["-y", "aema-mcp"]
    }
  }
}
```

## Available Tools

* `aema_retrieve`: Query verified reliable experiences before writing code.
* `aema_store`: Persist new execution traces and verified bug fixes.
* `aema_feedback`: Record success/failure to trigger A-EMA trust updates.
* `aema_audit`: Diagnostic health report and negative transfer risk score.
* `aema_dedup`: Merge redundant memories.
* `aema_wal`: Inspect immutable Write-Ahead Log audit records.
* `aema_status`: Display mathematical parameters and quarantine count.
