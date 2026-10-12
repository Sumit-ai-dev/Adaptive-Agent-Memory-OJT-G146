# AEMA Plugin for Cursor IDE

Equip Cursor with **Reliability-Aware Experiential Memory**.

## Features
- **Negative Transfer Isolation**: Automatically detects and quarantines degraded or flawed experiences using Theorem 1 cutoff ($\theta = 0.35$).
- **Write-Ahead Log (WAL)**: Immutable audit logging of memory operations.
- **Offline Deduplication**: Keeps memories clean, dense, and fast.
- **Instant Setup**: Zero configuration needed.

## Available MCP Tools
- `aema_retrieve`: Query verified reliable solutions for your current task.
- `aema_store`: Record successful execution traces.
- `aema_feedback`: Record success or failure to trigger A-EMA trust updates.
- `aema_audit`: Diagnostic health and negative transfer risk report.
- `aema_dedup`: Merge redundant memories.
- `aema_wal`: Inspect immutable audit records.
- `aema_status`: Check system parameters and quarantine counts.
