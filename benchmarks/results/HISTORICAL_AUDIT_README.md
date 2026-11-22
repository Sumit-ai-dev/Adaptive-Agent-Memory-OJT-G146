# Historical Benchmark Results (Pre-Audit Archive)

**Status:** `PRE-AUDIT / UNVERIFIED / SCIENTIFICALLY INVALID FOR PAPER CITATIONS`  
**Audit Date:** November 22, 2026  
**Auditor:** Senior ML Evaluation Engineer & Independent AI Research Auditor  

---

### Critical Notice
All experimental data, telemetry JSONL files, and summary tables stored in this directory (`benchmarks/results/`) were generated prior to the formal scientific audit on November 22, 2026.

These historical artifacts are **strictly preserved for scientific auditability, provenance tracking, and post-mortem analysis**. They must **NOT** be cited or reported in any academic publication or technical specification as valid empirical proof of AEMA performance due to the following audit findings:

1. **ToolBench Condition Bias:** Historical ToolBench runners contained hardcoded condition overrides (`success = (trial >= 2)` for adaptive; forced failure for `naive_rag` at `trial <= 2`).
2. **ALFWorld Simulation:** Historical ALFWorld runners executed without the TextWorld environment, using condition/trial index branches and synthetic token multipliers (`0.72x` for adaptive, `1.35x` for vanilla).
3. **HotpotQA Prompt Leakage:** Historical HotpotQA prompts leaked the ground-truth reference directly to the agent (`[Ground Truth Reference: ...]`).
4. **Synthetic Telemetry:** Token counts and millisecond latencies in certain historical runs were computed via arithmetic formulas rather than measured from actual API and system calls.

---

### New Research Directory
All new, verified, research-grade experimental runs following the Phase 2/3 remediation are stored separately under:
- `benchmarks/research_runs/exploratory/`
- `benchmarks/research_runs/confirmatory/`
- `benchmarks/research_runs/smoke/`

Never overwrite or modify any file in this historical archive directory.
