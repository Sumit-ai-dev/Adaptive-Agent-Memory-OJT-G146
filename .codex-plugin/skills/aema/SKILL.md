---
name: aema
description: Reliability-Aware Experiential Memory for Codex. Query verified past execution traces, record new experiences, update trust via Asymmetric Exponential Moving Average (A-EMA), and isolate negative transfer using Theorem 1 deterministic quarantine.
---

# AEMA for Codex: Reliability-Aware Memory Protocol

When Codex agents perform recurring programming or multi-step tasks, recalling flawed past solutions creates **negative transfer** (compounding errors). AEMA solves this by filtering candidates through empirical reliability scoring.

## Codex Workflow Protocol

1. **Recall Before Coding (`aema_retrieve`)**:
   Query experiential memory for verified solutions matching the current objective. Quarantined solutions are omitted automatically.

2. **Execute and Validate Solution**:
   Apply the approach in the codebase. Run tests or compiler validation.

3. **Provide Outcome Feedback (`aema_feedback`)**:
   - If successful, reinforce memory trust: $S_{t+1} = 0.85 S_t + 0.15$.
   - If failed, decay memory trust: $S_{t+1} = 0.70 S_t$.
   - Three consecutive failures triggers deterministic quarantine under Theorem 1.

4. **Persist New Discoveries (`aema_store`)**:
   Store verified working implementations with domain metadata.
