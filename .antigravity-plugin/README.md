# AEMA — Google Antigravity Plugin

In-repository packaging for integrating **AEMA (Reliability-Aware Experiential Memory)** directly into **Google Antigravity IDE**.

## Layout

```
.antigravity-plugin/
├── plugin.json                 # Manifest
├── mcp_config.json             # Registers aema-mcp stdio server
├── skills/
│   └── aema/
│       └── SKILL.md            # Skill: query, store, trust decay, quarantine, audit
├── rules/
│   └── aema-reliability.md    # Agent behavioral guideline rule
└── README.md                   # This documentation
```

## How It Works in Antigravity

1. **Automatic MCP Tool Exposure**:
   By including `mcp_config.json`, Antigravity automatically registers `aema-mcp`. The agent gains native access to all 7 AEMA tools (`aema_retrieve`, `aema_store`, `aema_feedback`, `aema_audit`, `aema_dedup`, `aema_wal`, `aema_status`).

2. **Skill Invocation**:
   Antigravity agents can invoke `@skill:aema` to understand the exact mathematical invariants, parameters ($\alpha = 0.85, \beta = 0.70, \theta = 0.35$), and workflow protocols for negative transfer isolation.

3. **Workspace Installation**:
   To install globally into your Antigravity user config:
   ```bash
   cp -r .antigravity-plugin ~/.gemini/config/plugins/aema
   ```
