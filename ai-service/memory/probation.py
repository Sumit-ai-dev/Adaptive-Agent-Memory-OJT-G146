"""
Isolated Probationary Validation Probe Pipeline for AEMA Quarantined Memories.

Architecture & Measurement Invariants:
1. Targeted Probe: Explicitly targets exactly one experience in CANDIDATE probation.
2. Direct Execution: Bypasses ordinary semantic retrieval and does NOT invoke the cyclical agent graph.
3. No Reflected Experiences: Does NOT invoke reflect_node; zero new candidate experiences are generated.
4. Real Evaluator: Executes real PytestExecutionEvaluator with executable assertions in an isolated subprocess.
5. Task Fingerprint Idempotency: Deduplicates task inputs and test assertions via SHA-256 fingerprinting.
   NOTE ON EVIDENCE DEDUPLICATION:
   Exact SHA-256 fingerprint deduplication prevents pseudo-replication from identical or repeated test assertions,
   but it does NOT establish statistical independence between semantically equivalent or paraphrased tests.
   This protocol does not claim to resolve the full i.i.d. assumption, but enforces strict determinism and prevents
   artificial quota inflation.
6. Target Exclusivity: Updates only the targeted experience's probation state and append-only audit ledger.
"""

import hashlib
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from ai_service.llm_client import llm_gateway, resolve_provider_config
from ai_service.memory.store import BaseMemoryStore
from ai_service.tools.evaluator import EvaluationOutcome, pytest_execution_evaluator
from ai_service.trust_math import calculate_probation_quota
from models.experience import Experience, ExperienceStatus, TrustHistoryRecord

logger = logging.getLogger("ai_service.memory.probation")


def normalize_for_fingerprint(text: str) -> str:
    """Normalizes input text by trimming lines and removing blank lines for consistent SHA-256 hashing."""
    if not text:
        return ""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return "\n".join(lines)


def compute_task_fingerprint(task_input: str, test_code: str) -> str:
    """Computes deterministic SHA-256 fingerprint over normalized task prompt and test assertions."""
    norm_input = normalize_for_fingerprint(task_input)
    norm_test = normalize_for_fingerprint(test_code)
    canonical = f"{norm_input}||{norm_test}".encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


async def execute_probationary_probe(
    experience_id: str,
    task_input: str,
    test_code: str,
    store: BaseMemoryStore,
    actor_id: str = "system:admin_api_key",
    client_ref: Optional[str] = None,
    execution_state: Optional[Dict[str, Any]] = None,
) -> Tuple[Experience, EvaluationOutcome, TrustHistoryRecord]:
    """
    Executes an isolated, administrative validation probe on a CANDIDATE experience.
    
    Guarantees:
    - Bypasses semantic vector retrieval.
    - Prompts the LLM with the target's bilateral constraints.
    - Evaluates using real pytest_execution_evaluator.
    - Atomically updates target memory in the store.
    - Does NOT mutate any other memory or generate reflections.
    """
    if not task_input or not task_input.strip():
        raise ValueError("Validation probe requires non-empty task_input.")
    if not test_code or not test_code.strip():
        raise ValueError("Validation probe requires non-empty test_code.")

    # 1. Fetch and assert isolated target memory
    exp = await store.get_experience(experience_id)
    if not exp:
        raise LookupError(f"Experience '{experience_id}' not found.")
    if exp.status != ExperienceStatus.CANDIDATE:
        raise ValueError(
            f"Experience '{experience_id}' is in status '{exp.status.value}'. "
            f"Only CANDIDATE memories can undergo probationary validation."
        )

    # 2. Formulate system prompt strictly incorporating the target's bilateral constraints
    system_prompt = (
        "You are an elite, proactive autonomous language agent with persistent experiential memory.\n"
        "Solve the user's task rigorously, providing accurate, verifiable, and structured Python code.\n\n"
        f"[VERIFIED OPERATIONAL STRATEGY (+sigma)]:\n{exp.strategy_lesson}\n"
    )
    if exp.pitfall:
        system_prompt += (
            f"\n[CRITICAL NEGATIVE CONSTRAINT - AVOID (-pi)]:\n"
            f"Under NO circumstances should you commit the following known pitfall: {exp.pitfall}\n"
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_input},
    ]

    # 3. Dispatch to LLM provider (bypassing retry loops and cyclical graphs)
    state_ctx = execution_state or {}
    provider_config, requested_temperature = resolve_provider_config(state_ctx)
    final_answer, tokens = await llm_gateway.generate(
        messages,
        config=provider_config,
        temperature=requested_temperature,
    )

    # 4. Real evaluator execution in isolated subprocess
    outcome = pytest_execution_evaluator.evaluate(
        final_answer=final_answer,
        test_code=test_code,
    )

    # 5. Deterministic fingerprinting and unique execution ID
    task_fingerprint = compute_task_fingerprint(task_input, test_code)
    probe_execution_id = f"probe_{uuid.uuid4().hex}"

    # 6. Atomic isolated update targeting strictly this experience
    updated_exp, record = await store.record_probationary_probe(
        experience_id=experience_id,
        outcome=outcome,
        execution_id=probe_execution_id,
        task_fingerprint=task_fingerprint,
        actor_id=actor_id,
        client_ref=client_ref,
    )

    logger.info(
        "Completed probationary probe for '%s': reward=%.2f, status=%s -> %s",
        experience_id,
        outcome.reward,
        exp.status.value,
        updated_exp.status.value,
    )

    return updated_exp, outcome, record
