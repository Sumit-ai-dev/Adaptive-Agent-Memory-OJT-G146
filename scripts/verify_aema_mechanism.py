"""
A-EMA Mechanism Verification Script.
Executes the 6 controlled mechanism tests + run isolation check
under the existing engineering baseline.
"""

import asyncio
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root is on path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ai_service.config import settings
from ai_service.experiment.evidence import ExposureRecord
from ai_service.experiment.memory_bank import MemoryBank, MemoryRecord
from ai_service.experiment.retrieval import PolicyBackedRetriever, SimilarityOnlyRanker
from ai_service.experiment.run_context import RunContext
from ai_service.graph import execute_task
from ai_service.llm_client import llm_gateway
from ai_service.nodes.trust_node import QUARANTINE_THRESHOLD, compute_next_trust
from ai_service.trust.aema import AEMAPolicy, StaticTrustPolicy
from ai_service.trust.base import Observation, PolicyContext, PolicyState
from models.domain import MemoryMode, TaskDomain
from models.provider import ModelProvider, ProviderConfig
from models.task import DEFAULT_OUTCOME_THRESHOLD, EvaluatorName, TaskExecuteRequest

# Common test strings
TRIGGER_FN = "Deterministic synthetic task solving function solve()"
PROMPT_FN = "Deterministic synthetic task solving function solve(). Write python function solve() returning integer."
TEST_CODE_CORRECT = (
    "from solution import solve\n"
    "def test_solve():\n"
    "    assert solve() == 42\n"
)
GOOD_STRATEGY = "```python\ndef solve():\n    return 42\n```"
BAD_STRATEGY = "```python\ndef solve():\n    return -999\n```"


class DeterministicMockLLM:
    """
    Synthetic agent LLM mock that deterministicallly follows bilateral constraints:
    - If positive_strategy is provided in system prompt, it extracts and returns that code.
    - If no strategy is provided, it returns a default baseline answer (solve() -> 0).
    - If reflection request, returns valid JSON reflection tuple.
    """

    def __init__(self):
        self.original_generate = llm_gateway.generate
        self.call_count = 0
        self.history = []

    async def mock_generate(
        self,
        messages: List[Dict[str, str]],
        config: Optional[ProviderConfig] = None,
        json_mode: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> Tuple[str, int]:
        self.call_count += 1
        self.history.append({"messages": messages, "config": config})

        sys_msg = next((m["content"] for m in messages if m.get("role") == "system"), "")
        user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")

        # Reflection generation
        if json_mode or "Extract a structured experience tuple" in sys_msg or "Extract a structured experience tuple" in user_msg:
            mock_reflection = {
                "trigger_condition": "Synthetic task execution",
                "strategy_lesson": "Synthesized strategy",
                "pitfall": "Synthetic pitfall",
                "confidence": 0.90,
            }
            return json.dumps(mock_reflection), 80

        # Check for injected positive strategy
        if "[VERIFIED OPERATIONAL STRATEGY (+sigma)]:" in sys_msg:
            strategy_part = sys_msg.split("[VERIFIED OPERATIONAL STRATEGY (+sigma)]:")[1]
            if "[CRITICAL NEGATIVE CONSTRAINT" in strategy_part:
                strategy_part = strategy_part.split("[CRITICAL NEGATIVE CONSTRAINT")[0]
            strategy_part = strategy_part.strip()
            # If strategy contains python code block, return it
            match = re.search(r"```python(.*?)```", strategy_part, re.DOTALL)
            if match:
                return f"```python{match.group(1)}```", 60
            return strategy_part, 60

        # Baseline default when no memory is injected / quarantined
        return "```python\ndef solve():\n    return 0\n```", 50


async def run_verification():
    mock_llm = DeterministicMockLLM()
    llm_gateway.generate = mock_llm.mock_generate

    results = {}

    print("==================================================")
    print("STARTING A-EMA MECHANISM VERIFICATION")
    print("==================================================")

    # ----------------------------------------------------
    # TEST 1: GOOD MEMORY
    # ----------------------------------------------------
    print("\n--- Running TEST 1: Good Memory ---")
    rec_good = MemoryRecord(
        memory_id="mem_good_001",
        domain=TaskDomain.CODING,
        trigger=TRIGGER_FN,
        strategy=GOOD_STRATEGY,
        pitfall="Do not return negative numbers.",
        initial_trust=0.75,
    )
    bank1 = MemoryBank([rec_good], bank_id="bank_test1").ensure_embeddings()
    policy1 = AEMAPolicy(initial_trust=0.75)
    run1 = RunContext(bank=bank1, policy=policy1, top_k=1, evaluator_name=EvaluatorName.PYTEST_EXECUTION.value)

    req1 = TaskExecuteRequest(
        task_input=PROMPT_FN,
        task_domain=TaskDomain.CODING,
        memory_enabled=True,
        memory_mode=MemoryMode.ADAPTIVE,
        provider=ModelProvider.MOCK,
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        evaluator_config={"test_code": TEST_CODE_CORRECT, "timeout_s": 15},
    )

    exec1 = await execute_task(req1, run_context=run1)
    state1_after = run1.trust_state.get("mem_good_001")
    exposures1 = run1.exposures.records

    t1_pass = (
        len(exec1.retrieved_memories) == 1
        and exec1.retrieved_memories[0]["experience"]["id"] == "mem_good_001"
        and len(exposures1) == 1
        and exposures1[0].binary_outcome == 1
        and exposures1[0].reward >= 0.80
        and state1_after.extra["trust_score"] == 0.7875
        and state1_after.uses == 1
        and state1_after.successes == 1
        and state1_after.failures == 0
        and policy1.admissible(state1_after, run1.policy_context()).admissible is True
    )

    results["TEST 1"] = {
        "pass": t1_pass,
        "initial_trust": 0.75,
        "outcome_reward": exec1.outcome_score,
        "binary_outcome": exec1.binary_outcome,
        "updated_trust": state1_after.extra["trust_score"],
        "uses": state1_after.uses,
        "successes": state1_after.successes,
        "failures": state1_after.failures,
        "exposure_id": exposures1[0].exposure_id if exposures1 else None,
        "admitted": len(exec1.retrieved_memories) > 0,
        "remains_admissible": policy1.admissible(state1_after, run1.policy_context()).admissible,
        "n_attempts": exec1.n_attempts,
    }
    print(f"TEST 1 result: {'PASS' if t1_pass else 'FAIL'}")
    print(f"Details: {results['TEST 1']}")

    # ----------------------------------------------------
    # TEST 2: SINGLE BAD MEMORY FAILURE
    # ----------------------------------------------------
    print("\n--- Running TEST 2: Single Bad Memory Failure ---")
    rec_bad = MemoryRecord(
        memory_id="mem_bad_001",
        domain=TaskDomain.CODING,
        trigger=TRIGGER_FN,
        strategy=BAD_STRATEGY,
        pitfall="Do not return 42.",
        initial_trust=0.75,
    )
    bank2 = MemoryBank([rec_bad], bank_id="bank_test2").ensure_embeddings()
    policy2 = AEMAPolicy(initial_trust=0.75)
    run2 = RunContext(bank=bank2, policy=policy2, top_k=1, evaluator_name=EvaluatorName.PYTEST_EXECUTION.value)

    # For Test 2 single failure check, set settings.MAX_CYCLICAL_LOOPS = 1 temporarily to observe 1 attempt
    orig_max_loops = settings.MAX_CYCLICAL_LOOPS
    settings.MAX_CYCLICAL_LOOPS = 1
    try:
        req2 = TaskExecuteRequest(
            task_input=PROMPT_FN,
            task_domain=TaskDomain.CODING,
            memory_enabled=True,
            memory_mode=MemoryMode.ADAPTIVE,
            provider=ModelProvider.MOCK,
            evaluator=EvaluatorName.PYTEST_EXECUTION,
            evaluator_config={"test_code": TEST_CODE_CORRECT, "timeout_s": 15},
        )
        exec2 = await execute_task(req2, run_context=run2)
    finally:
        settings.MAX_CYCLICAL_LOOPS = orig_max_loops

    state2_after = run2.trust_state.get("mem_bad_001")
    exposures2 = run2.exposures.records

    t2_pass = (
        len(exec2.retrieved_memories) == 1
        and exec2.retrieved_memories[0]["experience"]["id"] == "mem_bad_001"
        and len(exposures2) == 1
        and exposures2[0].binary_outcome == 0
        and exposures2[0].reward <= 0.30
        and state2_after.extra["trust_score"] == 0.5250
        and state2_after.uses == 1
        and state2_after.successes == 0
        and state2_after.failures == 1
    )

    results["TEST 2"] = {
        "pass": t2_pass,
        "initial_trust": 0.75,
        "outcome_reward": exec2.outcome_score,
        "binary_outcome": exec2.binary_outcome,
        "updated_trust": state2_after.extra["trust_score"],
        "uses": state2_after.uses,
        "successes": state2_after.successes,
        "failures": state2_after.failures,
        "exposure_id": exposures2[0].exposure_id if exposures2 else None,
        "admitted": len(exec2.retrieved_memories) > 0,
        "n_attempts": exec2.n_attempts,
    }
    print(f"TEST 2 result: {'PASS' if t2_pass else 'FAIL'}")
    print(f"Details: {results['TEST 2']}")

    # ----------------------------------------------------
    # TEST 3: REPEATED BAD MEMORY -> QUARANTINE
    # ----------------------------------------------------
    print("\n--- Running TEST 3: Repeated Bad Memory -> Quarantine ---")
    bank3 = MemoryBank([rec_bad], bank_id="bank_test3").ensure_embeddings()
    policy3 = AEMAPolicy(initial_trust=0.75)
    run3 = RunContext(bank=bank3, policy=policy3, top_k=1, evaluator_name=EvaluatorName.PYTEST_EXECUTION.value)

    trajectory = [0.7500]
    states_history = []

    # Run 3 consecutive failing tasks in the SAME RunContext
    settings.MAX_CYCLICAL_LOOPS = 1
    try:
        for trial_idx in range(1, 4):
            req = TaskExecuteRequest(
                task_input=PROMPT_FN,
                task_domain=TaskDomain.CODING,
                memory_enabled=True,
                memory_mode=MemoryMode.ADAPTIVE,
                provider=ModelProvider.MOCK,
                evaluator=EvaluatorName.PYTEST_EXECUTION,
                evaluator_config={"test_code": TEST_CODE_CORRECT, "timeout_s": 15},
            )
            res = await execute_task(req, run_context=run3)
            cur_state = run3.trust_state.get("mem_bad_001")
            score = cur_state.extra["trust_score"]
            trajectory.append(score)
            dec = policy3.admissible(cur_state, run3.policy_context())
            states_history.append({
                "trial": trial_idx,
                "reward": res.outcome_score,
                "binary": res.binary_outcome,
                "trust_score": score,
                "uses": cur_state.uses,
                "failures": cur_state.failures,
                "admissible": dec.admissible,
                "reason": dec.reason,
            })
    finally:
        settings.MAX_CYCLICAL_LOOPS = orig_max_loops

    # Expected trajectory: 0.7500 -> 0.5250 -> 0.3675 -> 0.2572 (rounded to 4 decimals by compute_next_trust)
    expected_traj = [0.7500, 0.5250, 0.3675, 0.2572]
    final_dec = policy3.admissible(run3.trust_state.get("mem_bad_001"), run3.policy_context())

    t3_pass = (
        trajectory == expected_traj
        and states_history[0]["admissible"] is True
        and states_history[1]["admissible"] is True
        and states_history[2]["admissible"] is False
        and final_dec.admissible is False
        and "quarantined" in final_dec.reason
    )

    results["TEST 3"] = {
        "pass": t3_pass,
        "observed_trajectory": trajectory,
        "expected_trajectory": expected_traj,
        "exact_math_product": 0.25725,
        "implementation_rounded_product": 0.2572,
        "threshold_comparison": f"{trajectory[-1]} < {QUARANTINE_THRESHOLD}",
        "final_status": "quarantined",
        "trials": states_history,
    }
    print(f"TEST 3 result: {'PASS' if t3_pass else 'FAIL'}")
    print(f"Details: {results['TEST 3']}")

    # ----------------------------------------------------
    # TEST 4: QUARANTINED MEMORY MUST NOT BE ADMITTED
    # (STORED != ADMISSIBLE != EXPOSED)
    # ----------------------------------------------------
    print("\n--- Running TEST 4: Quarantined Memory Must Not Be Admitted ---")
    # Issue a 4th query in the SAME RunContext run3 where mem_bad_001 is now quarantined
    req4 = TaskExecuteRequest(
        task_input=PROMPT_FN,
        task_domain=TaskDomain.CODING,
        memory_enabled=True,
        memory_mode=MemoryMode.ADAPTIVE,
        provider=ModelProvider.MOCK,
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        evaluator_config={"test_code": TEST_CODE_CORRECT, "timeout_s": 15},
    )
    exec4 = await execute_task(req4, run_context=run3)

    is_stored = run3.bank.get("mem_bad_001") is not None
    curr_state4 = run3.trust_state.get("mem_bad_001")
    dec4 = policy3.admissible(curr_state4, run3.policy_context())
    is_admissible = dec4.admissible
    is_exposed = any(m["experience"]["id"] == "mem_bad_001" for m in exec4.retrieved_memories)

    t4_pass = (
        is_stored is True
        and is_admissible is False
        and is_exposed is False
        and len(exec4.retrieved_memories) == 0
    )

    results["TEST 4"] = {
        "pass": t4_pass,
        "STORED": is_stored,
        "ADMISSIBLE": is_admissible,
        "EXPOSED": is_exposed,
        "admissibility_reason": dec4.reason,
        "retrieved_count": len(exec4.retrieved_memories),
        "task_id": exec4.task_id,
    }
    print(f"TEST 4 result: {'PASS' if t4_pass else 'FAIL'}")
    print(f"Details: {results['TEST 4']}")

    # ----------------------------------------------------
    # TEST 5: RETRIEVAL WITHOUT OUTCOME
    # ----------------------------------------------------
    print("\n--- Running TEST 5: Retrieval Without Outcome ---")
    bank5 = MemoryBank([rec_good], bank_id="bank_test5").ensure_embeddings()
    policy5 = AEMAPolicy(initial_trust=0.75)
    run5 = RunContext(bank=bank5, policy=policy5, top_k=1)

    # Perform retrieval directly using policy retriever
    retriever5 = PolicyBackedRetriever(run=run5, ranker=run5.ranker)
    candidates5, diag5 = retriever5.retrieve(query=PROMPT_FN, domain=TaskDomain.CODING, top_k=1)

    state5_before_outcome = run5.trust_state.get("mem_good_001")

    t5_pass = (
        len(candidates5) == 1
        and candidates5[0].record.memory_id == "mem_good_001"
        and state5_before_outcome.extra["trust_score"] == 0.7500
        and state5_before_outcome.uses == 0
        and state5_before_outcome.successes == 0
        and state5_before_outcome.failures == 0
        and len(run5.exposures) == 0
    )

    results["TEST 5"] = {
        "pass": t5_pass,
        "retrieved_candidate": candidates5[0].record.memory_id if candidates5 else None,
        "trust_score": state5_before_outcome.extra["trust_score"],
        "uses": state5_before_outcome.uses,
        "successes": state5_before_outcome.successes,
        "failures": state5_before_outcome.failures,
        "exposures_count": len(run5.exposures),
    }
    print(f"TEST 5 result: {'PASS' if t5_pass else 'FAIL'}")
    print(f"Details: {results['TEST 5']}")

    # ----------------------------------------------------
    # TEST 6: RETRY DEDUPLICATION
    # ----------------------------------------------------
    print("\n--- Running TEST 6: Retry Deduplication ---")
    bank6 = MemoryBank([rec_bad], bank_id="bank_test6").ensure_embeddings()
    policy6 = AEMAPolicy(initial_trust=0.75)
    run6 = RunContext(bank=bank6, policy=policy6, top_k=1, evaluator_name=EvaluatorName.PYTEST_EXECUTION.value)

    # MAX_CYCLICAL_LOOPS is 3: task will retry 3 times and fail on each attempt
    req6 = TaskExecuteRequest(
        task_input=PROMPT_FN,
        task_domain=TaskDomain.CODING,
        memory_enabled=True,
        memory_mode=MemoryMode.ADAPTIVE,
        provider=ModelProvider.MOCK,
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        evaluator_config={"test_code": TEST_CODE_CORRECT, "timeout_s": 15},
    )

    exec6 = await execute_task(req6, run_context=run6)
    state6_after = run6.trust_state.get("mem_bad_001")
    exposures6 = run6.exposures.records

    terminal_attempts = [a for a in exec6.attempts if a.is_terminal]

    t6_pass = (
        exec6.n_attempts == 3
        and len(exec6.attempts) == 3
        and len(terminal_attempts) == 1
        and terminal_attempts[0].attempt_index == 3
        and len(exposures6) == 1
        and len(exposures6[0].attempts) == 3
        and state6_after.extra["trust_score"] == 0.5250  # exactly 1 failure update: 0.75 * 0.70 = 0.5250
        and state6_after.uses == 1
        and state6_after.successes == 0
        and state6_after.failures == 1
        and state6_after.successes + state6_after.failures == state6_after.uses
    )

    results["TEST 6"] = {
        "pass": t6_pass,
        "n_attempts": exec6.n_attempts,
        "attempts_recorded": [
            {"attempt_index": a.attempt_index, "reward": a.reward, "binary": a.binary_outcome, "is_terminal": a.is_terminal}
            for a in exec6.attempts
        ],
        "terminal_attempt_index": terminal_attempts[0].attempt_index if terminal_attempts else None,
        "exposures_count": len(exposures6),
        "task_level_observations": 1 if len(exposures6) == 1 else len(exposures6),
        "initial_trust": 0.75,
        "updated_trust": state6_after.extra["trust_score"],
        "uses": state6_after.uses,
        "successes": state6_after.successes,
        "failures": state6_after.failures,
        "exposure_id": exposures6[0].exposure_id if exposures6 else None,
    }
    print(f"TEST 6 result: {'PASS' if t6_pass else 'FAIL'}")
    print(f"Details: {results['TEST 6']}")

    # ----------------------------------------------------
    # ADDITIONAL CHECK: RUN ISOLATION
    # ----------------------------------------------------
    print("\n--- Running ADDITIONAL CHECK: Run Isolation ---")
    bank_shared = MemoryBank([rec_bad], bank_id="bank_shared").ensure_embeddings()
    initial_bank_hash = bank_shared.bank_hash

    # Run A drives memory to quarantine
    run_a = RunContext(bank=bank_shared, policy=AEMAPolicy(initial_trust=0.75), top_k=1)
    # Apply 3 failure observations directly or via task
    for i in range(1, 4):
        obs = Observation(
            memory_id="mem_bad_001",
            task_id=f"task_a_{i}",
            run_id=run_a.run_id,
            task_index=i,
            reward=0.0,
            binary_outcome=0,
            outcome_threshold=0.80,
        )
        run_a.trust_state.apply(obs)

    state_a = run_a.trust_state.get("mem_bad_001")
    dec_a = run_a.policy.admissible(state_a, run_a.policy_context())

    # Run B starts fresh with the SAME shared bank
    run_b = RunContext(bank=bank_shared, policy=AEMAPolicy(initial_trust=0.75), top_k=1)
    state_b = run_b.trust_state.get("mem_bad_001")
    dec_b = run_b.policy.admissible(state_b, run_b.policy_context())

    isolation_pass = (
        state_a.extra["trust_score"] == 0.2572
        and state_a.uses == 3
        and state_a.failures == 3
        and dec_a.admissible is False
        and state_b.extra["trust_score"] == 0.7500
        and state_b.uses == 0
        and state_b.failures == 0
        and dec_b.admissible is True
        and bank_shared.bank_hash == initial_bank_hash
        and bank_shared.get("mem_bad_001").initial_trust == 0.75
    )

    results["ADDITIONAL CHECK"] = {
        "pass": isolation_pass,
        "run_a_id": run_a.run_id,
        "run_a_trust": state_a.extra["trust_score"],
        "run_a_uses": state_a.uses,
        "run_a_admissible": dec_a.admissible,
        "run_b_id": run_b.run_id,
        "run_b_trust": state_b.extra["trust_score"],
        "run_b_uses": state_b.uses,
        "run_b_admissible": dec_b.admissible,
        "bank_hash_unchanged": bank_shared.bank_hash == initial_bank_hash,
    }
    print(f"ADDITIONAL CHECK result: {'PASS' if isolation_pass else 'FAIL'}")
    print(f"Details: {results['ADDITIONAL CHECK']}")

    # Restore original llm gateway generate
    llm_gateway.generate = mock_llm.original_generate

    # Summary
    print("\n==================================================")
    print("FINAL TEST SUMMARY")
    print("==================================================")
    all_tests = [
        ("TEST 1 — GOOD MEMORY", results["TEST 1"]["pass"]),
        ("TEST 2 — SINGLE BAD MEMORY FAILURE", results["TEST 2"]["pass"]),
        ("TEST 3 — REPEATED BAD MEMORY -> QUARANTINE", results["TEST 3"]["pass"]),
        ("TEST 4 — QUARANTINED MEMORY MUST NOT BE ADMITTED", results["TEST 4"]["pass"]),
        ("TEST 5 — RETRIEVAL WITHOUT OUTCOME", results["TEST 5"]["pass"]),
        ("TEST 6 — RETRY DEDUPLICATION", results["TEST 6"]["pass"]),
        ("ADDITIONAL CHECK — RUN ISOLATION", results["ADDITIONAL CHECK"]["pass"]),
    ]

    pass_count = sum(1 for _, p in all_tests if p)
    fail_count = sum(1 for _, p in all_tests if not p)
    blocked_count = 0

    for name, passed in all_tests:
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print(f"\nPASS: {pass_count}")
    print(f"FAIL: {fail_count}")
    print(f"BLOCKED: {blocked_count}")

    with open("/tmp/aema_verification_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    asyncio.run(run_verification())
