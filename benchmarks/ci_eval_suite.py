"""
Automated LLM Regression Benchmarking Suite for CI/CD Pipelines (Issue #37).
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)

Executes 10 representative frozen tasks across Coding, Reasoning, and Tool Execution
to detect prompt drift, regression anomalies, and Pass@1 degradation before PR merges.

Enforces an automated baseline quality gate (default: >= 80% pass rate).
Exports structured JSON metrics and formatted GitHub PR markdown summaries.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path for direct invocations and CI runners
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ai_service.graph import execute_task
from models.domain import MemoryMode, TaskDomain
from models.task import EvaluatorName, TaskExecuteRequest, TaskExecution

logger = logging.getLogger("benchmarks.ci_eval_suite")

# 10 Representative frozen regression tasks
FROZEN_REGRESSION_TASKS: List[Dict[str, Any]] = [
    # ─── 5 Coding Tasks (Evaluated with PytestExecutionEvaluator) ───────────────
    {
        "id": "code_01_fibonacci",
        "name": "Fibonacci Sequence",
        "category": "coding",
        "domain": TaskDomain.CODING,
        "evaluator": EvaluatorName.PYTEST_EXECUTION,
        "input": "Write a python function `fibonacci(n)` that returns the n-th Fibonacci number (0-indexed: fibonacci(0)=0, fibonacci(1)=1, fibonacci(6)=8).",
        "evaluator_config": {
            "test_code": (
                "def test_fib():\n"
                "    assert fibonacci(0) == 0\n"
                "    assert fibonacci(1) == 1\n"
                "    assert fibonacci(6) == 8\n"
                "    assert fibonacci(10) == 55\n"
            ),
        },
    },
    {
        "id": "code_02_is_palindrome",
        "name": "Alphanumeric Palindrome",
        "category": "coding",
        "domain": TaskDomain.CODING,
        "evaluator": EvaluatorName.PYTEST_EXECUTION,
        "input": (
            "Write a python function `is_palindrome(s)` that returns True if string s is a palindrome, "
            "ignoring non-alphanumeric characters and case."
        ),
        "evaluator_config": {
            "test_code": (
                "def test_pal():\n"
                "    assert is_palindrome('A man, a plan, a canal: Panama') is True\n"
                "    assert is_palindrome('RaceCar') is True\n"
                "def test_not_pal():\n"
                "    assert is_palindrome('hello') is False\n"
            ),
        },
    },
    {
        "id": "code_03_binary_search",
        "name": "Binary Search",
        "category": "coding",
        "domain": TaskDomain.CODING,
        "evaluator": EvaluatorName.PYTEST_EXECUTION,
        "input": "Write a python function `binary_search(arr, target)` returning the index of target in sorted arr, or -1 if not found.",
        "evaluator_config": {
            "test_code": (
                "def test_bs_found():\n"
                "    assert binary_search([1, 2, 4, 7, 9], 7) == 3\n"
                "    assert binary_search([10, 20, 30], 10) == 0\n"
                "def test_bs_not_found():\n"
                "    assert binary_search([1, 2, 4, 7, 9], 5) == -1\n"
            ),
        },
    },
    {
        "id": "code_04_two_sum",
        "name": "Two Sum Indices",
        "category": "coding",
        "domain": TaskDomain.CODING,
        "evaluator": EvaluatorName.PYTEST_EXECUTION,
        "input": "Write a python function `two_sum(nums, target)` returning the indices of two numbers that sum to target.",
        "evaluator_config": {
            "test_code": (
                "def test_two_sum():\n"
                "    assert sorted(two_sum([2, 7, 11, 15], 9)) == [0, 1]\n"
                "    assert sorted(two_sum([3, 2, 4], 6)) == [1, 2]\n"
            ),
        },
    },
    {
        "id": "code_05_merge_intervals",
        "name": "Interval Consolidation",
        "category": "coding",
        "domain": TaskDomain.CODING,
        "evaluator": EvaluatorName.PYTEST_EXECUTION,
        "input": "Write a python function `merge_intervals(intervals)` that merges all overlapping intervals.",
        "evaluator_config": {
            "test_code": (
                "def test_merge_intervals():\n"
                "    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]\n"
                "    assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]\n"
            ),
        },
    },
    # ─── 3 Reasoning Tasks (Evaluated with Exact Match / Token F1) ─────────────
    {
        "id": "reason_06_prime_number",
        "name": "Prime Number Proof",
        "category": "reasoning",
        "domain": TaskDomain.ANALYSIS,
        "evaluator": EvaluatorName.EXACT_MATCH_F1,
        "input": "Explain whether 17 is a prime number and state the reason clearly.",
        "evaluator_config": {
            "ground_truth": "17 is a prime number because it is divisible only by 1 and itself.",
        },
    },
    {
        "id": "reason_07_syllogism_logic",
        "name": "Deductive Syllogism",
        "category": "reasoning",
        "domain": TaskDomain.ANALYSIS,
        "evaluator": EvaluatorName.EXACT_MATCH_F1,
        "input": "Given premises: All humans are mortal. Socrates is a human. Is Socrates mortal? Provide logical conclusion.",
        "evaluator_config": {
            "ground_truth": "Socrates is mortal because all humans are mortal and Socrates is a human.",
        },
    },
    {
        "id": "reason_08_causal_diagnosis",
        "name": "System Outage Diagnosis",
        "category": "reasoning",
        "domain": TaskDomain.ANALYSIS,
        "evaluator": EvaluatorName.EXACT_MATCH_F1,
        "input": "Diagnose why the upstream service is returning HTTP 503 under high concurrent load.",
        "evaluator_config": {
            "ground_truth": "Gateway connection pool exhaustion under high concurrent load.",
        },
    },
    # ─── 2 Tool Execution Tasks (Evaluated with Structured Criteria) ───────────
    {
        "id": "tool_09_weather_query",
        "name": "Tool Dispatch - Weather",
        "category": "tool_execution",
        "domain": TaskDomain.GENERAL,
        "evaluator": EvaluatorName.EXACT_MATCH_F1,
        "input": "Query the weather tool for weather in Tokyo and state current temperature and condition.",
        "evaluator_config": {
            "ground_truth": "The current weather in Tokyo is sunny, 22°C with 45% humidity.",
            "expected_tool": "weather_api",
        },
    },
    {
        "id": "tool_10_database_search",
        "name": "Tool Dispatch - DB Filter",
        "category": "tool_execution",
        "domain": TaskDomain.GENERAL,
        "evaluator": EvaluatorName.EXACT_MATCH_F1,
        "input": "Search the database: find customer by id CUST-1042.",
        "evaluator_config": {
            "ground_truth": "Customer record found: ID=CUST-1042, Status=ACTIVE, Tier=PLATINUM.",
            "expected_tool": "database_search",
        },
    },
]


async def run_ci_eval_suite(
    provider: str = "mock",
    model: Optional[str] = "mock",
    min_pass_rate: float = 0.80,
    memory_mode: MemoryMode = MemoryMode.ADAPTIVE,
) -> Dict[str, Any]:
    """
    Executes the 10 frozen regression tasks through execute_task and computes KPIs.
    """
    start_suite_ts = time.time()
    results: List[Dict[str, Any]] = []

    passed_count = 0
    total_tokens = 0
    prompt_tokens = 0
    completion_tokens = 0
    total_cost_usd = 0.0

    print(f"\n{'='*75}")
    print(f"  RUNNING CI LLM REGRESSION BENCHMARK SUITE (10 Frozen Tasks)")
    print(f"  Provider: {provider} | Model: {model} | Baseline Gate: {min_pass_rate * 100:.1f}%")
    print(f"{'='*75}\n")

    for idx, task_spec in enumerate(FROZEN_REGRESSION_TASKS, start=1):
        task_start = time.time()
        req = TaskExecuteRequest(
            task_input=task_spec["input"],
            task_domain=task_spec["domain"],
            memory_mode=memory_mode,
            provider=provider,
            model=model,
            evaluator=task_spec["evaluator"],
            evaluator_config=task_spec.get("evaluator_config", {}),
        )

        try:
            execution: TaskExecution = await execute_task(req, memory_store=None)
            duration_ms = int((time.time() - task_start) * 1000)
            score = float(execution.outcome_score or 0.0)
            is_success = execution.binary_outcome == 1 or score >= float(execution.outcome_threshold or 0.80)

            # For tool execution tasks, verify both ground truth alignment and structured tool call dispatch
            expected_tool = task_spec.get("evaluator_config", {}).get("expected_tool")
            if task_spec.get("category") == "tool_execution" and expected_tool:
                tool_calls = execution.tool_calls or []
                has_tool_call = any(
                    expected_tool.lower() in str(tc.get("name", "")).lower()
                    for tc in tool_calls
                    if isinstance(tc, dict)
                )
                if not has_tool_call:
                    is_success = False
                    score = min(score, 0.40)

            if is_success:
                passed_count += 1

            total_tokens += execution.tokens_used
            prompt_tokens += execution.prompt_tokens
            completion_tokens += execution.completion_tokens
            total_cost_usd += execution.total_cost_usd

            status_str = "PASS" if is_success else "FAIL"
            print(
                f"[{idx:02d}/10] {task_spec['name']:<28} | {task_spec['category']:<14} | "
                f"Score: {score:.2f} | Status: {status_str:<4} | Latency: {duration_ms}ms"
            )

            results.append({
                "taskId": task_spec["id"],
                "name": task_spec["name"],
                "category": task_spec["category"],
                "evaluator": task_spec["evaluator"].value,
                "score": score,
                "passed": is_success,
                "binaryOutcome": 1 if is_success else 0,
                "latencyMs": duration_ms,
                "tokensUsed": execution.tokens_used,
                "promptTokens": execution.prompt_tokens,
                "completionTokens": execution.completion_tokens,
                "costUsd": execution.total_cost_usd,
                "traceId": execution.trace_id,
            })
        except Exception as e:
            duration_ms = int((time.time() - task_start) * 1000)
            logger.error(f"Task '{task_spec['id']}' failed with exception: {e}", exc_info=True)
            print(f"[{idx:02d}/10] {task_spec['name']:<28} | EXCEPTION: {e}")
            results.append({
                "taskId": task_spec["id"],
                "name": task_spec["name"],
                "category": task_spec["category"],
                "evaluator": task_spec["evaluator"].value,
                "score": 0.0,
                "passed": False,
                "binaryOutcome": 0,
                "latencyMs": duration_ms,
                "tokensUsed": 0,
                "promptTokens": 0,
                "completionTokens": 0,
                "costUsd": 0.0,
                "error": str(e),
            })

    total_duration_ms = int((time.time() - start_suite_ts) * 1000)
    total_tasks = len(FROZEN_REGRESSION_TASKS)
    pass_rate = passed_count / total_tasks
    avg_latency_ms = int(sum(r["latencyMs"] for r in results) / total_tasks) if total_tasks else 0
    is_gate_passed = pass_rate >= min_pass_rate

    print(f"\n{'-'*75}")
    print(f"  BENCHMARK SUMMARY:")
    print(f"  Total Tasks:      {total_tasks}")
    print(f"  Passed:           {passed_count}/{total_tasks} ({pass_rate * 100:.1f}%)")
    print(f"  Quality Gate:     {'PASSED (>= ' + str(int(min_pass_rate * 100)) + '%)' if is_gate_passed else 'FAILED (< ' + str(int(min_pass_rate * 100)) + '%)'}")
    print(f"  Average Latency:  {avg_latency_ms} ms")
    print(f"  Total Tokens:     {total_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens})")
    print(f"  Total Cost:       ${total_cost_usd:.5f}")
    print(f"  Total Wall Time:  {total_duration_ms / 1000:.2f} s")
    print(f"{'='*75}\n")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "totalTasks": total_tasks,
        "passedTasks": passed_count,
        "failedTasks": total_tasks - passed_count,
        "passRate": pass_rate,
        "minPassRate": min_pass_rate,
        "isGatePassed": is_gate_passed,
        "avgLatencyMs": avg_latency_ms,
        "totalDurationMs": total_duration_ms,
        "totalTokens": total_tokens,
        "promptTokens": prompt_tokens,
        "completionTokens": completion_tokens,
        "totalCostUsd": round(total_cost_usd, 6),
        "tasks": results,
    }


def format_markdown_report(report_data: Dict[str, Any]) -> str:
    """
    Renders GitHub PR comment summary markdown with clean tabular presentation.
    """
    is_passed = report_data["isGatePassed"]
    status_badge = "PASSED" if is_passed else "FAILED"
    status_icon = "PASS" if is_passed else "FAIL"

    lines = [
        f"## CI LLM Regression Benchmark Report: {status_icon} ({status_badge})",
        "",
        f"**Run Timestamp**: `{report_data['timestamp']}`  ",
        f"**Provider**: `{report_data['provider']}` | **Model**: `{report_data['model']}`  ",
        f"**Pass Rate**: `{report_data['passRate'] * 100:.1f}%` ({report_data['passedTasks']}/{report_data['totalTasks']}) | **Gate Target**: `>= {report_data['minPassRate'] * 100:.1f}%`  ",
        "",
        "### Key Performance Indicators",
        "",
        "| Metric | Result | Target / Baseline | Status |",
        "|:---|:---|:---|:---|",
        f"| **Pass@1 Rate** | **{report_data['passRate'] * 100:.1f}%** | >= {report_data['minPassRate'] * 100:.1f}% | {'PASS' if is_passed else 'FAIL'} |",
        f"| **Average Latency** | **{report_data['avgLatencyMs']} ms** | < 2500 ms | {'PASS' if report_data['avgLatencyMs'] < 2500 else 'WARN'} |",
        f"| **Total Tokens** | **{report_data['totalTokens']:,}** (prompt: {report_data['promptTokens']:,}, completion: {report_data['completionTokens']:,}) | Monitored | PASS |",
        f"| **Total Cost (USD)** | **${report_data['totalCostUsd']:.5f}** | <= $0.05000 | {'PASS' if report_data['totalCostUsd'] <= 0.05 else 'WARN'} |",
        "",
        "### Task Breakdown (10 Frozen Regression Benchmarks)",
        "",
        "| # | Task | Category | Evaluator | Reward | Status | Latency |",
        "|:---|:---|:---|:---|:---|:---|:---|",
    ]

    for idx, t in enumerate(report_data["tasks"], start=1):
        task_status = "PASS" if t["passed"] else "FAIL"
        lines.append(
            f"| {idx:02d} | **{t['name']}** | `{t['category']}` | `{t['evaluator']}` | {t['score']:.2f} | {task_status} | {t['latencyMs']} ms |"
        )

    lines.extend([
        "",
        "---",
        "*Automated regression eval suite generated by `benchmarks/ci_eval_suite.py` on PR workflow.*",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="CI Automated LLM Regression Benchmarking Suite")
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "anthropic", "gemini", "ollama", "openrouter", "deepseek"],
        help="Model provider (default: mock). Quality gate is scoped to evaluated provider.",
    )
    parser.add_argument("--model", default="mock", help="Model identifier (default: mock)")
    parser.add_argument("--min-pass-rate", type=float, default=0.80, help="Minimum pass rate threshold in [0, 1] (default: 0.80)")
    parser.add_argument("--memory-mode", default="adaptive", choices=["off", "naive", "symmetric", "adaptive"], help="Memory mode")
    parser.add_argument("--output-json", type=str, default=None, help="Optional path to output results JSON")
    parser.add_argument("--output-markdown", type=str, default=None, help="Optional path to output PR comment markdown")
    args = parser.parse_args()

    mode_map = {
        "off": MemoryMode.OFF,
        "naive": MemoryMode.NAIVE,
        "symmetric": MemoryMode.SYMMETRIC,
        "adaptive": MemoryMode.ADAPTIVE,
    }
    selected_mode = mode_map.get(args.memory_mode, MemoryMode.ADAPTIVE)

    report_data = asyncio.run(
        run_ci_eval_suite(
            provider=args.provider,
            model=args.model,
            min_pass_rate=args.min_pass_rate,
            memory_mode=selected_mode,
        )
    )

    # Output JSON if requested
    if args.output_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.output_json)), exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"Wrote JSON evaluation report to: {args.output_json}")

    # Output Markdown if requested
    if args.output_markdown:
        os.makedirs(os.path.dirname(os.path.abspath(args.output_markdown)), exist_ok=True)
        md_content = format_markdown_report(report_data)
        with open(args.output_markdown, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"Wrote Markdown evaluation report to: {args.output_markdown}")

    # Enforce quality gate exit code
    if not report_data["isGatePassed"]:
        print(f"\n[CI FAILURE] Pass rate {report_data['passRate'] * 100:.1f}% below minimum baseline {report_data['minPassRate'] * 100:.1f}%.")
        sys.exit(1)
    else:
        print(f"\n[CI SUCCESS] Pass rate {report_data['passRate'] * 100:.1f}% met or exceeded quality gate.")
        sys.exit(0)


if __name__ == "__main__":
    main()
