# AEMA MCP Integration Guide

This guide explains how to connect **AEMA (Reliability-Aware Experiential Memory)** directly into **Claude Desktop**, **Cursor IDE**, and **Windsurf** via the Model Context Protocol (MCP).

---

## 1. Claude Desktop Setup

1. Open your Claude Desktop configuration file:
   * **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   * **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   * **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. Add `aema-memory` to the `mcpServers` object:

```json
{
  "mcpServers": {
    "aema-memory": {
      "command": "npx",
      "args": ["-y", "aema-mcp"],
      "env": {
        "AEMA_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

3. Restart Claude Desktop. You will see the **AEMA tools** (`aema_retrieve`, `aema_store`, `aema_feedback`, `aema_status`) available in the tool list.

---

## 2. Cursor IDE Setup

1. In your project workspace, create `.cursor/mcp.json`:

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

2. Open **Cursor Settings -> Features -> MCP**, verify that `aema-memory` is enabled.
3. In Cursor Composer or Chat, you can now prompt:
   > *"Retrieve any reliable experiences for handling Next.js SSR hydration bugs using AEMA."*

---

## 3. Docker MCP Setup

If you prefer running inside an isolated Docker container without local Node.js:

```bash
docker run -i --rm -e AEMA_API_URL=http://host.docker.internal:8000 aema/mcp
```

Or configure Claude Desktop using Docker:

```json
{
  "mcpServers": {
    "aema-memory": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "aema/mcp"]
    }
  }
}
```

---

## 4. Exposed MCP Tools

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `aema_retrieve` | `query`, `topK`, `minTrust` | Retrieves non-quarantined, verified experiences ranked by reliability |
| `aema_store` | `task`, `solution`, `initialTrust`, `domain` | Records execution traces with initial trust score |
| `aema_feedback` | `experienceId`, `outcome` (`success`/`failure`) | Updates trust via A-EMA; activates Theorem 1 quarantine if score decays below 0.35 |
| `aema_status` | *(none)* | Displays active trust parameters, quarantined count, and system health |
