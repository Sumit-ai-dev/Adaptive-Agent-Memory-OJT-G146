# AEMA Research-Grade Benchmark Execution Runs

**Policy:** Strict Verification & Reproducibility Standard  
**Mandate:** Zero Hardcoded Conditions • Real Telemetry • Decoupled Evaluators  

---

### Directory Organization
- **`exploratory/`**: Pilot experiments, sensitivity sweeps, hyperparameter explorations.
- **`confirmatory/`**: Preregistered, frozen multi-seed benchmark evaluations for scientific reporting and publications.
- **`smoke/`**: Quick regression smoke tests ($N \le 2$ tasks) to verify pipeline execution before large runs.

### Research Standards
Every execution logged here must adhere to:
1. **Zero Condition Favoritism:** Evaluators cannot access condition names or trial counts.
2. **Ground Truth Isolation:** Task prompts cannot contain answers or hidden evaluation criteria.
3. **Real Telemetry:** All token counts and latency metrics must be recorded from actual runtime invocations.
