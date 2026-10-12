---
name: aema
description: Reliability-Aware Experiential Memory for AI Agents. Query verified past execution traces, record new experiences, update trust via Asymmetric Exponential Moving Average (A-EMA), and isolate negative transfer using Theorem 1 deterministic quarantine.
---

# AEMA Skill: Reliability-Aware Experiential Memory

When an AI agent repeatedly tackles complex programming, debugging, research, or multi-step execution tasks, standard RAG retrieves past solutions based purely on semantic similarity. If a previous solution was faulty or poisoned, the agent falls into **negative transfer**, repeating identical errors.

The **AEMA Skill** instructs you on how to interact with AEMA to ensure guaranteed reliability.

---

## Core Principles

1. **Search Before Execution (`aema_retrieve`)**:
   - Before implementing complex solutions, query AEMA experiential memory to check if a reliable, verified approach already exists.
   - Quarantined memories ($S < 0.35$) are automatically omitted by the engine to protect you from negative transfer.

2. **Store Verified Successes (`aema_store`)**:
   - Once a task or bug fix has been confirmed working, store the problem description and verified code solution.
   - Initial trust begins at $S_0 = 1.0$ and is tracked in the Write-Ahead Log (WAL).

3. **Report Execution Feedback (`aema_feedback`)**:
   - If a retrieved memory worked, send `outcome: "success"` (A-EMA reinforces trust: $S_{t+1} = 0.85 S_t + 0.15$).
   - If a retrieved memory caused an error or failed, send `outcome: "failure"` (A-EMA decays trust: $S_{t+1} = 0.70 S_t$).
   - After exactly 3 consecutive failures, Theorem 1 guarantees deterministic quarantine ($S < 0.35$).

4. **Health Audit & Deduplication (`aema_audit`, `aema_dedup`)**:
   - Periodically run `aema_audit` to monitor the Negative Transfer Risk Index.
   - Run `aema_dedup` to prune redundant memory clutter and retain the highest-trust experience.

---

## Available MCP Tools

* `aema_retrieve`: Search reliable memories by task query and domain.
* `aema_store`: Persist new verified execution traces.
* `aema_feedback`: Record success/failure and update A-EMA trust score.
* `aema_audit`: Diagnostic health report and negative transfer risk score.
* `aema_dedup`: Merge redundant memories.
* `aema_wal`: Inspect immutable Write-Ahead Log audit records.
* `aema_status`: Display mathematical hyperparameters and quarantine count.

---

## Usage in Agent Turns

```markdown
Turn 1: User asks: "Fix Next.js SSR hydration error."
Agent Action: Call `aema_retrieve(query="Next.js SSR hydration error", domain="coding")`

Turn 2: Agent evaluates retrieved memory:
- If retrieved memory succeeds: Call `aema_feedback(experienceId=exp_1, outcome="success")`
- If retrieved memory fails: Call `aema_feedback(experienceId=exp_1, outcome="failure")`
```
