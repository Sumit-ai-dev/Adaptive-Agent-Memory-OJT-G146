"""
Master Empirical Benchmark Evaluation Suite — Adaptive Agent Memory
Unified CLI runner across HotpotQA, ToolBench, and ALFWorld.
Evaluates 4 ablation conditions: Vanilla ReAct, Naive RAG, Symmetric Reflexion, and Adaptive Memory.
Computes and outputs Pass@k, ERR, Token Economy (E_token), and Quarantine Precision (Q_prec).
"""

import argparse
import asyncio
import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

from benchmarks.alfworld_runner import run_alfworld_benchmark
from benchmarks.hotpotqa_runner import run_hotpotqa_benchmark
from benchmarks.metrics import compute_all_metrics, load_telemetry, print_summary_table
from benchmarks.toolbench_runner import run_toolbench_benchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("benchmarks.run_all")


def parse_args():
    parser = argparse.ArgumentParser(description="Adaptive Agent Memory — Empirical Evaluation Suite")
    parser.add_argument(
        "--benchmark",
        choices=["hotpotqa", "toolbench", "alfworld", "all"],
        default="all",
        help="Target benchmark suite (default: all)",
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=["vanilla", "naive_rag", "symmetric", "adaptive"],
        help="Ablation conditions to test (default: vanilla naive_rag symmetric adaptive)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=5,
        help="Number of tasks per benchmark (default: 5)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=3,
        help="Number of trials per task (default: 3)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run fast smoke test (n=2, trials=2)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to telemetry jsonl output file",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    n_tasks = 2 if args.quick else args.n
    max_trials = 2 if args.quick else args.trials

    # Resolve conditions
    if "all" in args.conditions:
        conditions = ["vanilla", "naive_rag", "symmetric", "adaptive"]
    else:
        conditions = args.conditions

    # Output paths
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    telemetry_path = args.output or str(results_dir / f"telemetry_{ts}.jsonl")
    latest_path = str(results_dir / "telemetry_latest.jsonl")

    print("\n" + "=" * 78)
    print("  ADAPTIVE AGENT MEMORY — EMPIRICAL BENCHMARK EVALUATION (MONTH 2)")
    print("=" * 78)
    print(f"  Target Benchmark:    {args.benchmark.upper()}")
    print(f"  Ablation Conditions: {', '.join(conditions)}")
    print(f"  Tasks per Suite:     {n_tasks}")
    print(f"  Trials per Task:     {max_trials}")
    print(f"  Telemetry Output:    {telemetry_path}")
    print("=" * 78 + "\n")

    benchmarks_to_run = []
    if args.benchmark in ["hotpotqa", "all"]:
        benchmarks_to_run.append("hotpotqa")
    if args.benchmark in ["toolbench", "all"]:
        benchmarks_to_run.append("toolbench")
    if args.benchmark in ["alfworld", "all"]:
        benchmarks_to_run.append("alfworld")

    for bm in benchmarks_to_run:
        print(f"\n>>> Running Benchmark: {bm.upper()} <<<")
        if bm == "hotpotqa":
            await run_hotpotqa_benchmark(
                tasks_limit=n_tasks,
                conditions=conditions,
                max_trials=max_trials,
                telemetry_path=telemetry_path,
            )
        elif bm == "toolbench":
            await run_toolbench_benchmark(
                tasks_limit=n_tasks,
                conditions=conditions,
                max_trials=max_trials,
                telemetry_path=telemetry_path,
            )
        elif bm == "alfworld":
            await run_alfworld_benchmark(
                tasks_limit=n_tasks,
                conditions=conditions,
                max_trials=max_trials,
                telemetry_path=telemetry_path,
            )

    # Copy / update telemetry_latest.jsonl
    if os.path.exists(telemetry_path):
        with open(telemetry_path, "r", encoding="utf-8") as src, open(latest_path, "w", encoding="utf-8") as dst:
            dst.write(src.read())

    # Load recorded telemetry and compute official paper metrics
    print("\n" + "=" * 78)
    print("  CALCULATING EMPIRICAL METRICS FROM TELEMETRY")
    print("=" * 78)

    records = load_telemetry(telemetry_path)
    print(f"Loaded {len(records)} total trial records.")

    all_summaries: Dict[str, Dict] = {}

    for bm in benchmarks_to_run:
        bm_summary = compute_all_metrics(records, benchmark=bm)
        all_summaries[bm] = bm_summary
        print_summary_table(bm_summary, benchmark_name=bm)

    if len(benchmarks_to_run) > 1:
        combined_summary = compute_all_metrics(records, benchmark=None)
        all_summaries["combined"] = combined_summary
        print_summary_table(combined_summary, benchmark_name="Combined Benchmark Aggregate")

    # Save summary json
    summary_path = str(results_dir / f"table2_summary_{ts}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)

    latest_summary_path = str(results_dir / "table2_summary_latest.json")
    with open(latest_summary_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)

    print(f"\nSummary JSON saved to:\n  - {summary_path}\n  - {latest_summary_path}")
    print(f"Full JSONL telemetry saved to:\n  - {telemetry_path}\n  - {latest_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
