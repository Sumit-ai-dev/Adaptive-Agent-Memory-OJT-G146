"""
Real-provider instrument smoke test.

PURPOSE: verify that the experimental harness actually distinguishes E0 (no memory)
from E1 (memory) when driven by a real LLM rather than the deterministic mock. Under
the mock, the model ignores injected memory entirely, so E0 and E1 are observationally
identical and the instrument is never exercised.

THIS IS NOT A RESEARCH RESULT. The task is deliberately constructed so the answer is
obtainable ONLY from the memory. A difference in outcome therefore demonstrates that
the wiring works -- that injected content reaches the model and affects generation. It
says nothing whatsoever about whether memory improves agent performance in general,
and must never be cited as if it did.

Skipped automatically unless Ollama is running with the pinned model available.
"""

import asyncio
import importlib
import json

import pytest

from ai_service.experiment import (
    ExperimentHarness,
    MemoryBank,
    MemoryRecord,
    ModelSpec,
    TaskSpec,
)
from ai_service.experiment.harness import make_e0, make_e1, new_pair_id
from ai_service.trust import AEMAPolicy
from models.domain import TaskDomain
from models.task import EvaluatorName

SMOKE_MODEL = "qwen2.5:1.5b"
OLLAMA_URL = "http://localhost:11434"

SECRET = 37
TRIGGER = "ingest pipeline maximum retry limit configuration"
STRATEGY = f"The ingest pipeline's configured maximum retry limit is {SECRET}."
PITFALL = "Do not assume the framework default of 3."
PROMPT = (
    "Write a Python function get_retry_limit() that returns the ingest pipeline "
    "maximum retry limit. Return only a Python code block."
)
TESTS = (
    "from solution import get_retry_limit\n"
    f"def test_limit():\n    assert get_retry_limit() == {SECRET}\n"
)


def _ollama_ready() -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as resp:
            names = {m["name"] for m in json.loads(resp.read()).get("models", [])}
        return SMOKE_MODEL in names
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _ollama_ready(),
    reason=f"requires Ollama at {OLLAMA_URL} with model {SMOKE_MODEL}",
)


def _bank() -> MemoryBank:
    return MemoryBank(
        [
            MemoryRecord(
                memory_id="mem_retry", domain=TaskDomain.CODING, trigger=TRIGGER,
                strategy=STRATEGY, pitfall=PITFALL, provenance="authored",
                initial_trust=0.75,
            )
        ],
        bank_id="smoke",
    ).ensure_embeddings()


def _task() -> TaskSpec:
    return TaskSpec(
        task_id="smoke_retry", prompt=PROMPT, domain=TaskDomain.CODING,
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        evaluator_config={"test_code": TESTS, "timeout_s": 40},
    )


def test_instrument_distinguishes_e0_from_e1_with_a_real_model():
    async def _go():
        execute_node_mod = importlib.import_module("ai_service.nodes.execute_node")
        captured = {}
        original = execute_node_mod.llm_gateway.generate

        async def spy(messages, **kwargs):
            captured.setdefault(spy.tag, []).append(messages)
            return await original(messages, **kwargs)

        spy.tag = "?"
        execute_node_mod.llm_gateway.generate = spy
        try:
            bank, task = _bank(), _task()
            bank_hash_before = bank.bank_hash
            harness = ExperimentHarness(
                bank=bank,
                model_spec=ModelSpec(
                    provider="ollama", model=SMOKE_MODEL,
                    model_version=SMOKE_MODEL, temperature=0.0,
                ),
            )
            pair_id = new_pair_id()
            spy.tag = "E0"
            e0 = await harness.run_condition(task, make_e0(), pair_id=pair_id)
            spy.tag = "E1"
            e1 = await harness.run_condition(
                task, make_e1(AEMAPolicy()), pair_id=pair_id, baseline=e0
            )
        finally:
            execute_node_mod.llm_gateway.generate = original

        e0_system, e0_user = captured["E0"][0][0]["content"], captured["E0"][0][1]["content"]
        e1_system, e1_user = captured["E1"][0][0]["content"], captured["E1"][0][1]["content"]

        # --- prompts ---
        assert STRATEGY not in e0_system
        assert PITFALL not in e0_system
        assert str(SECRET) not in (e0_system + e0_user), "E0 must not see the hidden fact"
        assert STRATEGY in e1_system
        assert PITFALL in e1_system
        assert e0_user == e1_user, "the task text must be identical across conditions"

        # --- retrieval ---
        assert e0.memory_ids_exposed == []
        assert e1.memory_ids_exposed == ["mem_retry"]

        # --- held fixed ---
        assert e0.task_hash == e1.task_hash
        assert (e0.evaluator_name, e0.evaluator_version) == (e1.evaluator_name, e1.evaluator_version)
        assert e0.model == e1.model == SMOKE_MODEL
        assert e0.pair_id == e1.pair_id == pair_id
        assert e0.run_id != e1.run_id

        # --- evidence ---
        exposure = [r for r in e1.exposures if r["memory_id"]][0]
        assert exposure["injected"] is True
        assert exposure["similarity"] > 0.60
        assert exposure["policy_state_before"]["uses"] == 0
        assert exposure["policy_state_after"]["uses"] == 1
        assert exposure["stateless_reward"] == e0.terminal_reward
        assert exposure["stateless_binary"] == e0.binary_outcome
        assert e0.exposures[0]["memory_id"] is None
        assert e0.exposures[0]["fallback_occurred"] is True

        # --- fixed bank ---
        assert e0.bank_unchanged and e1.bank_unchanged
        assert bank.bank_hash == bank_hash_before
        assert len(bank) == 1, "no candidate memory may be written"

        # --- instrument sensitivity ---
        # Recorded, not interpreted. The task is answerable only via memory, so this
        # shows injected content reaches the model -- NOT that memory helps in general.
        assert e1.terminal_reward != e0.terminal_reward, (
            "instrument did not distinguish the conditions; "
            f"E0={e0.terminal_reward} E1={e1.terminal_reward}"
        )

    asyncio.run(_go())
