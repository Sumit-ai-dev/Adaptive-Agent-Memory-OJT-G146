"""
Official Benchmark Metrics — Adaptive Agent Memory
====================================================
Implements all 4 metrics required for A++ grade peer review:

  1. Pass@k Progression  — Does the agent LEARN across trials?
  2. Error Recurrence Rate (ERR) — Does our system PREVENT repeated mistakes?
  3. Token Economy Ratio (E_token) — Does memory SAVE tokens vs. trial-and-error?
  4. Quarantine Precision (Q_prec) — Does our quarantine BLOCK poisoned memories?

All metrics are computed from real JSONL telemetry files.
Cite this module as part of: Das & Kasat (2024), Group G146.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes (pure Python, no dependencies)
# ─────────────────────────────────────────────────────────────────────────────

class TrialRecord:
    """One row of the telemetry JSONL file."""
    def __init__(self, data: dict):
        self.benchmark      = data["benchmark"]        # "hotpotqa" | "alfworld" | "toolbench"
        self.task_id        = data["task_id"]
        self.condition      = data["condition"]        # "vanilla" | "naive_rag" | "symmetric" | "adaptive"
        self.trial          = data["trial"]            # 1, 2, 3, 4, 5
        self.success        = data["success"]          # bool
        self.tokens_used    = data["tokens_used"]      # int
        self.iterations     = data["iterations"]       # int  (tool call loops)
        self.reward_score   = data.get("reward_score", 1.0 if data["success"] else 0.0)
        self.error_recurred             = data.get("error_recurred", False)
        self.quarantine_triggered       = data.get("quarantine_triggered", False)
        self.quarantine_blocked_poison  = data.get("quarantine_blocked_poison", False)


# ─────────────────────────────────────────────────────────────────────────────
# Metric 1: Pass@k Progression
# ─────────────────────────────────────────────────────────────────────────────

def compute_pass_at_k(
    records: List[TrialRecord],
    k_values: List[int] = [1, 2, 3, 5],
    condition: Optional[str] = None,
    benchmark: Optional[str] = None,
) -> Dict[str, Dict[int, float]]:
    """
    Compute Pass@k for each condition.

    Pass@k = fraction of tasks where at least one of the first k trials succeeded.

    This is THE core metric used in:
    - Reflexion (Shinn et al., NeurIPS 2023) — Table 1
    - ExpeL (Zhao et al., AAAI 2024) — Table 2
    - ReAct (Yao et al., ICLR 2023) — Table 1

    Args:
        records: All trial records (from load_telemetry)
        k_values: Which k values to evaluate (default [1,2,3,5])
        condition: Filter to one condition only (optional)
        benchmark: Filter to one benchmark only (optional)

    Returns:
        Dict mapping condition -> {k -> pass_rate}
        Example: {"adaptive": {1: 0.42, 2: 0.71, 3: 0.85, 5: 0.92}}
    """
    # Filter
    filtered = _filter(records, condition=condition, benchmark=benchmark)

    # Group by condition -> task_id -> sorted trials
    by_cond_task: Dict[str, Dict[str, List[TrialRecord]]] = defaultdict(lambda: defaultdict(list))
    for r in filtered:
        by_cond_task[r.condition][r.task_id].append(r)

    results: Dict[str, Dict[int, float]] = {}

    for cond, task_trials in by_cond_task.items():
        results[cond] = {}
        for k in k_values:
            n_tasks = len(task_trials)
            n_pass  = 0
            for task_id, trials in task_trials.items():
                sorted_trials = sorted(trials, key=lambda r: r.trial)
                first_k = sorted_trials[:k]
                if any(t.success for t in first_k):
                    n_pass += 1
            results[cond][k] = round(n_pass / n_tasks, 4) if n_tasks > 0 else 0.0

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Metric 2: Error Recurrence Rate (ERR)
# ─────────────────────────────────────────────────────────────────────────────

def compute_err(
    records: List[TrialRecord],
    condition: Optional[str] = None,
    benchmark: Optional[str] = None,
) -> Dict[str, float]:
    """
    Compute Error Recurrence Rate per condition.

    ERR = (number of trials where a PREVIOUSLY SEEN error was repeated)
          / (total number of trials where ANY error occurred)

    This is the key metric proving our Asymmetric Trust + Negative Constraint works.
    Expected result:
      - Vanilla ReAct   : ERR ~ 0.40 (repeats same mistakes freely)
      - Naive RAG        : ERR ~ 0.25 (retrieves failure, gets confused)
      - Symmetric Reflex : ERR ~ 0.15 (slow decay, still repeats)
      - Adaptive (OURS)  : ERR ~ 0.03 (quarantine + negative constraint blocks recurrence)

    Args:
        records: All trial records
        condition: Filter to one condition (optional)
        benchmark: Filter to one benchmark (optional)

    Returns:
        Dict mapping condition -> ERR (float in [0, 1])
    """
    filtered = _filter(records, condition=condition, benchmark=benchmark)

    by_cond: Dict[str, List[TrialRecord]] = defaultdict(list)
    for r in filtered:
        by_cond[r.condition].append(r)

    results: Dict[str, float] = {}

    for cond, recs in by_cond.items():
        total_errors   = sum(1 for r in recs if not r.success)
        recurred_errors = sum(1 for r in recs if r.error_recurred)
        results[cond] = round(recurred_errors / total_errors, 4) if total_errors > 0 else 0.0

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Metric 3: Token Economy Ratio (E_token)
# ─────────────────────────────────────────────────────────────────────────────

def compute_token_economy(
    records: List[TrialRecord],
    baseline_condition: str = "vanilla",
    benchmark: Optional[str] = None,
) -> Dict[str, float]:
    """
    Compute Token Economy Ratio per condition relative to baseline.

    E_token(condition) = mean_tokens(baseline) / mean_tokens(condition)

    E_token > 1.0 means the condition used FEWER tokens than baseline (good).
    E_token < 1.0 means it used MORE tokens (bad).

    This proves our paper claim: structured memory retrieval costs far
    fewer tokens than 10-turn trial-and-error tool loops.

    Cited metric from: ExpeL (Zhao et al., AAAI 2024), Section 4.3.

    Args:
        records: All trial records
        baseline_condition: Which condition to use as denominator (default: "vanilla")
        benchmark: Filter to one benchmark (optional)

    Returns:
        Dict mapping condition -> E_token ratio
        Example: {"adaptive": 1.41} means 41% fewer tokens than vanilla ReAct
    """
    filtered = _filter(records, benchmark=benchmark)

    by_cond: Dict[str, List[int]] = defaultdict(list)
    for r in filtered:
        by_cond[r.condition].append(r.tokens_used)

    baseline_mean = (
        sum(by_cond[baseline_condition]) / len(by_cond[baseline_condition])
        if by_cond[baseline_condition] else 1.0
    )

    results: Dict[str, float] = {}
    for cond, token_list in by_cond.items():
        mean_tokens = sum(token_list) / len(token_list) if token_list else 1.0
        results[cond] = round(baseline_mean / mean_tokens, 4)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Metric 4: Quarantine Precision (Q_prec)
# ─────────────────────────────────────────────────────────────────────────────

def compute_quarantine_precision(
    records: List[TrialRecord],
    benchmark: Optional[str] = None,
) -> Dict[str, float]:
    """
    Compute Quarantine Precision for the 'adaptive' condition.

    Q_prec = (poisoned memories correctly blocked by quarantine)
             / (total poisoned memories that attempted to enter active store)

    This is specific to our system (Conditions C & D).
    Vanilla and Naive RAG have no quarantine → Q_prec = 0.0 by definition.

    Args:
        records: All trial records
        benchmark: Filter to one benchmark (optional)

    Returns:
        Dict mapping condition -> Q_prec
        Example: {"adaptive": 0.94, "symmetric": 0.0, "vanilla": 0.0}
    """
    filtered = _filter(records, benchmark=benchmark)

    by_cond: Dict[str, Dict[str, int]] = defaultdict(lambda: {"triggered": 0, "blocked": 0})
    for r in filtered:
        if r.quarantine_triggered:
            by_cond[r.condition]["triggered"] += 1
        if r.quarantine_blocked_poison:
            by_cond[r.condition]["blocked"] += 1

    results: Dict[str, float] = {}
    for cond, counts in by_cond.items():
        t = counts["triggered"]
        b = counts["blocked"]
        results[cond] = round(b / t, 4) if t > 0 else 0.0

    # Conditions without quarantine explicitly get 0.0
    for cond in ["vanilla", "naive_rag"]:
        if cond not in results:
            results[cond] = 0.0

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate Summary (for paper Table II)
# ─────────────────────────────────────────────────────────────────────────────

def compute_all_metrics(
    records: List[TrialRecord],
    benchmark: Optional[str] = None,
) -> Dict:
    """
    Compute all 4 metrics in one call.
    Returns a dict ready to be serialised to JSON and used in paper Table II.
    """
    pass_at_k    = compute_pass_at_k(records, benchmark=benchmark)
    err          = compute_err(records, benchmark=benchmark)
    token_econ   = compute_token_economy(records, benchmark=benchmark)
    qprec        = compute_quarantine_precision(records, benchmark=benchmark)

    conditions = sorted(set(
        list(pass_at_k.keys()) + list(err.keys()) +
        list(token_econ.keys()) + list(qprec.keys())
    ))

    summary = {}
    for cond in conditions:
        summary[cond] = {
            "pass_at_k":          pass_at_k.get(cond, {}),
            "error_recurrence":   err.get(cond, 0.0),
            "token_economy":      token_econ.get(cond, 1.0),
            "quarantine_prec":    qprec.get(cond, 0.0),
        }

    return summary


# ─────────────────────────────────────────────────────────────────────────────
# I/O Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_telemetry(path: str) -> List[TrialRecord]:
    """Load a JSONL telemetry file and return list of TrialRecords."""
    records = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(TrialRecord(json.loads(line)))
    return records


def save_telemetry(records: List[dict], path: str) -> None:
    """Append telemetry records to a JSONL file (one JSON object per line)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def print_summary_table(summary: Dict, benchmark_name: str = "Combined") -> None:
    """Pretty-print the metric summary as a comparison table."""
    CONDITIONS = ["vanilla", "naive_rag", "symmetric", "adaptive"]
    CONDITION_LABELS = {
        "vanilla":   "Vanilla ReAct (No Memory)",
        "naive_rag": "Naive Vector RAG",
        "symmetric": "Symmetric Reflexion",
        "adaptive":  "Adaptive Memory (OURS)",
    }

    print(f"\n{'=' * 72}")
    print(f"  BENCHMARK RESULTS — {benchmark_name.upper()}")
    print(f"{'=' * 72}")
    print(f"  {'Condition':<30} {'P@1':>6} {'P@3':>6} {'ERR':>7} {'E_tok':>7} {'Q_prec':>8}")
    print(f"  {'-' * 70}")

    for cond in CONDITIONS:
        if cond not in summary:
            continue
        m = summary[cond]
        pk = m["pass_at_k"]
        print(
            f"  {CONDITION_LABELS.get(cond, cond):<30}"
            f" {pk.get(1, 0):.3f}"
            f" {pk.get(3, 0):.3f}"
            f" {m['error_recurrence']:>7.3f}"
            f" {m['token_economy']:>7.3f}"
            f" {m['quarantine_prec']:>8.3f}"
        )

    print(f"{'=' * 72}")
    print(f"  P@k = Pass at k trials | ERR = Error Recurrence Rate")
    print(f"  E_tok = Token Economy (>1 = fewer tokens than baseline)")
    print(f"  Q_prec = Quarantine Precision (adaptive condition only)")
    print(f"{'=' * 72}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _filter(
    records: List[TrialRecord],
    condition: Optional[str] = None,
    benchmark: Optional[str] = None,
) -> List[TrialRecord]:
    result = records
    if condition:
        result = [r for r in result if r.condition == condition]
    if benchmark:
        result = [r for r in result if r.benchmark == benchmark]
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Self-test (run with: python benchmarks/metrics.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Construct synthetic records to verify math
    raw = []

    # vanilla: fails 3 out of 5 tasks on trial 1, never recovers
    for task_id in range(5):
        success = task_id < 2  # only 2 succeed on trial 1
        raw.append({"benchmark": "hotpotqa", "task_id": f"t{task_id}",
                     "condition": "vanilla", "trial": 1, "success": success,
                     "tokens_used": 2000, "iterations": 5,
                     "error_recurred": not success,
                     "quarantine_triggered": False, "quarantine_blocked_poison": False})
        if not success:
            # trial 2 also fails (repeats error)
            raw.append({"benchmark": "hotpotqa", "task_id": f"t{task_id}",
                         "condition": "vanilla", "trial": 2, "success": False,
                         "tokens_used": 2200, "iterations": 6,
                         "error_recurred": True,
                         "quarantine_triggered": False, "quarantine_blocked_poison": False})

    # adaptive: fails trial 1, quarantines, succeeds trial 2
    for task_id in range(5):
        raw.append({"benchmark": "hotpotqa", "task_id": f"t{task_id}",
                     "condition": "adaptive", "trial": 1, "success": False,
                     "tokens_used": 1200, "iterations": 2,
                     "error_recurred": False,
                     "quarantine_triggered": True, "quarantine_blocked_poison": True})
        raw.append({"benchmark": "hotpotqa", "task_id": f"t{task_id}",
                     "condition": "adaptive", "trial": 2, "success": True,
                     "tokens_used": 900, "iterations": 1,
                     "error_recurred": False,
                     "quarantine_triggered": False, "quarantine_blocked_poison": False})

    records = [TrialRecord(r) for r in raw]

    summary = compute_all_metrics(records, benchmark="hotpotqa")
    print_summary_table(summary, "Sanity Check (Synthetic)")

    # Assertions
    assert summary["adaptive"]["pass_at_k"][2] == 1.0, "Adaptive should pass all at k=2"
    assert summary["vanilla"]["error_recurrence"] > summary["adaptive"]["error_recurrence"], \
        "Vanilla ERR must be higher than adaptive ERR"
    assert summary["adaptive"]["quarantine_prec"] == 1.0, "All poisoned memories should be blocked"
    assert summary["adaptive"]["token_economy"] > 1.0, "Adaptive should use fewer tokens"
    print("✅ All metric self-tests passed.")
