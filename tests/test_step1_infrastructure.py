"""
Step 1 Infrastructure Test Suite.

Covers the separation of immutable memory content, run-scoped evidence, mutable trust
state and the pluggable policy layer -- plus the single most important criterion:

    For an identical workload and identical initial memory state, Step 1 must not
    materially change A-EMA behaviour.

These tests assert infrastructure correctness. They assert nothing about which trust
mechanism is appropriate.
"""

import asyncio
import os
import tempfile

import pytest

from ai_service.experiment import (
    ExposureLog,
    ExposureRecord,
    LegacyModeRanker,
    MemoryBank,
    MemoryRecord,
    PolicyBackedRetriever,
    RunContext,
    SimilarityOnlyRanker,
    compare_policies,
    new_run_id,
    replay_log,
    replay_observations,
)
from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.trust_node import compute_next_trust
from ai_service.trust import (
    AEMAPolicy,
    Observation,
    PolicyContext,
    PolicyState,
    StaticTrustPolicy,
    available_policies,
    build_policy,
)
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus
from models.provider import ModelProvider
from models.task import EvaluatorName, TaskExecuteRequest

TRIGGER = "Fixing RecursionError in deep binary tree traversal"
TASK = "Fix the RecursionError raised by my recursive binary tree traversal function"
TEST_SUITE = "from solution import add\ndef test_a():\n    assert add(2, 3) == 5\n"


def _record(mid="m1", trust=0.75, domain=TaskDomain.CODING) -> MemoryRecord:
    return MemoryRecord(
        memory_id=mid, domain=domain, trigger=TRIGGER,
        strategy="Convert the recursion to an iterative traversal using collections.deque.",
        pitfall="Do not raise sys.setrecursionlimit.",
        provenance="authored", initial_trust=trust,
    )


def _bank(*records) -> MemoryBank:
    return MemoryBank(records or (_record(),), bank_id="test_bank").ensure_embeddings()


def _run(bank=None, policy=None, **kw) -> RunContext:
    return RunContext(
        bank=bank or _bank(),
        policy=policy or AEMAPolicy(),
        **kw,
    )


def _obs(mid="m1", idx=1, reward=0.0, binary=0, run_id="r") -> Observation:
    return Observation(
        memory_id=mid, task_id=f"t{idx}", run_id=run_id, task_index=idx,
        reward=reward, binary_outcome=binary, outcome_threshold=0.80,
    )


def _fresh_store() -> SQLiteMemoryStore:
    fd, path = tempfile.mkstemp(suffix=".db", prefix="s1_")
    os.close(fd)
    os.remove(path)
    return SQLiteMemoryStore(db_path=path)


# ==============================================================================
# 1. Memory content immutability
# ==============================================================================

def test_memory_record_carries_no_trust_evidence():
    rec = _record()
    for forbidden in ("trust_score", "uses_count", "successes_count", "failures_count", "status"):
        assert not hasattr(rec, forbidden), f"MemoryRecord must not carry {forbidden}"


def test_memory_record_is_frozen():
    rec = _record()
    with pytest.raises(Exception):
        rec.trigger = "mutated"
    with pytest.raises(Exception):
        rec.labels["x"] = 1


def test_content_hash_is_stable_and_content_sensitive():
    a, b = _record(), _record()
    assert a.content_hash == b.content_hash
    # Trust is NOT content -- changing it must not change the content hash.
    assert _record(trust=0.1).content_hash == a.content_hash
    different = MemoryRecord(
        memory_id="m1", domain=TaskDomain.CODING, trigger="other",
        strategy=a.strategy, pitfall=a.pitfall,
    )
    assert different.content_hash != a.content_hash


def test_bank_is_read_only_and_rejects_duplicates():
    bank = _bank()
    assert not hasattr(bank, "add")
    assert not hasattr(bank, "update")
    with pytest.raises(ValueError):
        MemoryBank([_record("m1"), _record("m1")])


def test_to_experience_view_cannot_affect_the_bank():
    bank = _bank()
    rec = bank.get("m1")
    view = rec.to_experience(trust_score=0.01)
    view.trust_score = 0.0
    view.strategy_lesson = "mutated"
    assert bank.get("m1").strategy == rec.strategy
    assert bank.get("m1").initial_trust == 0.75


# ==============================================================================
# 2. Trust-state isolation / run isolation / reset
# ==============================================================================

def test_two_runs_over_one_bank_do_not_share_trust_state():
    bank = _bank()
    run_a, run_b = _run(bank), _run(bank)
    assert run_a.run_id != run_b.run_id

    for i in range(1, 4):
        run_a.trust_state.apply(_obs(idx=i, reward=0.0, binary=0, run_id=run_a.run_id))

    a_trust = run_a.trust_state.get("m1").extra["trust_score"]
    b_trust = run_b.trust_state.get("m1").extra["trust_score"]
    assert a_trust < 0.75, "run A must have decayed"
    assert b_trust == 0.75, "run B must be untouched by run A"


def test_run_isolation_of_exposure_logs():
    bank = _bank()
    run_a, run_b = _run(bank), _run(bank)
    run_a.exposures.append(ExposureRecord(
        run_id=run_a.run_id, task_id="t1", task_index=1,
        memory_id="m1", exposure_id="e1",
    ))
    assert len(run_a.exposures) == 1
    assert len(run_b.exposures) == 0

    with pytest.raises(ValueError, match="run isolation violated"):
        run_b.exposures.append(ExposureRecord(
            run_id=run_a.run_id, task_id="t1", task_index=1,
            memory_id="m1", exposure_id="e1",
        ))


def test_state_reset_returns_run_to_initial_condition():
    run = _run()
    for i in range(1, 4):
        run.trust_state.apply(_obs(idx=i, run_id=run.run_id))
    run.exposures.append(ExposureRecord(
        run_id=run.run_id, task_id="t1", task_index=1, memory_id="m1", exposure_id="e1",
    ))
    assert run.trust_state.get("m1").uses == 3

    run.reset()
    assert run.trust_state.get("m1").uses == 0
    assert run.trust_state.get("m1").extra["trust_score"] == 0.75
    assert len(run.exposures) == 0


def test_trust_state_seeds_from_bank_initial_trust():
    bank = _bank(_record("m1", trust=0.42), _record("m2", trust=0.91))
    run = _run(bank)
    assert run.trust_state.get("m1").extra["trust_score"] == 0.42
    assert run.trust_state.get("m2").extra["trust_score"] == 0.91


def test_no_global_singleton_in_experiment_or_trust_packages():
    """Global stores were the previous contamination vector."""
    import ai_service.experiment.memory_bank as mb
    import ai_service.experiment.run_context as rc
    import ai_service.experiment.retrieval as rt
    import ai_service.trust.base as tb

    for module in (mb, rc, rt, tb):
        for name, val in vars(module).items():
            if name.startswith("_"):
                continue
            assert not isinstance(val, (MemoryBank, RunContext)), \
                f"module-level mutable singleton {name} in {module.__name__}"


def test_fixed_bank_is_unchanged_after_a_run():
    bank = _bank()
    before = bank.bank_hash
    run = _run(bank)
    for i in range(1, 6):
        run.trust_state.apply(_obs(idx=i, run_id=run.run_id))
    assert bank.bank_hash == before
    assert run.verify_bank_unchanged()


# ==============================================================================
# 3. Policy abstraction: swapping, purity, determinism
# ==============================================================================

def test_policy_registry_builds_known_policies():
    assert "aema" in available_policies()
    assert isinstance(build_policy("aema"), AEMAPolicy)
    assert isinstance(build_policy("static"), StaticTrustPolicy)
    with pytest.raises(KeyError):
        build_policy("does_not_exist")


def test_policy_swap_changes_behaviour_without_touching_other_layers():
    bank = _bank()
    obs = [_obs(idx=i, reward=0.0, binary=0) for i in range(1, 5)]

    aema = replay_observations(obs, AEMAPolicy())
    static = replay_observations(obs, StaticTrustPolicy())

    assert aema.final_states["m1"]["extra"]["trust_score"] < 0.35
    assert static.final_states["m1"]["extra"]["trust_score"] == 0.75
    # Counters are mechanism-independent and must agree.
    assert aema.final_states["m1"]["failures"] == static.final_states["m1"]["failures"] == 4


def test_policy_update_is_pure():
    policy = AEMAPolicy()
    state = policy.initial_state("m1")
    obs = _obs(reward=0.1, binary=0)

    a = policy.update(state, obs)
    b = policy.update(state, obs)
    assert a == b, "update must be deterministic"
    assert state.uses == 0, "update must not mutate its input"
    assert state.extra["trust_score"] == 0.75


def test_policy_state_is_immutable():
    state = AEMAPolicy().initial_state("m1")
    with pytest.raises(Exception):
        state.uses = 5
    with pytest.raises(Exception):
        state.extra["trust_score"] = 0.1


def test_policy_counter_invariant_is_enforced():
    with pytest.raises(ValueError):
        PolicyState(memory_id="m1", uses=3, successes=1, failures=1)


def test_policy_counters_follow_binary_outcome_not_trust_delta():
    """F3 carried into the policy layer."""
    policy = AEMAPolicy()
    state = policy.initial_state("m1", trust_score=0.30)
    # reward 0.60 RAISES trust from 0.30, yet the evaluator says failure.
    after = policy.update(state, _obs(reward=0.60, binary=0))
    assert after.extra["trust_score"] > 0.30
    assert after.failures == 1 and after.successes == 0


def test_static_policy_expresses_no_ranking_opinion_change():
    policy = StaticTrustPolicy()
    s = policy.initial_state("m1")
    after = policy.update(s, _obs(reward=0.0, binary=0))
    assert after.extra["trust_score"] == s.extra["trust_score"]
    assert after.uses == 1


# ==============================================================================
# 4. A-EMA behaviour preservation (the critical criterion)
# ==============================================================================

@pytest.mark.parametrize("rewards", [
    [0.0, 0.0, 0.0],
    [0.95, 0.95, 0.95],
    [0.6, 0.6, 0.6],
    [0.95, 0.1, 0.6, 0.95, 0.1],
    [0.1, 0.9, 0.1, 0.9],
])
def test_aema_policy_matches_reference_recursion_exactly(rewards):
    """The ported policy must reproduce compute_next_trust step for step."""
    policy = AEMAPolicy()
    state = policy.initial_state("m1")

    reference = 0.75
    for i, r in enumerate(rewards, start=1):
        reference, _ = compute_next_trust(reference, r)
        state = policy.update(state, _obs(idx=i, reward=r, binary=1 if r >= 0.80 else 0))
        assert state.extra["trust_score"] == pytest.approx(reference, abs=1e-9)


def test_aema_quarantine_horizon_is_unchanged():
    """Three consecutive failures from 0.75 still cross theta = 0.35."""
    policy = AEMAPolicy()
    ctx = PolicyContext(run_id="r")
    state = policy.initial_state("m1")

    admissibility = []
    for i in range(1, 4):
        state = policy.update(state, _obs(idx=i, reward=0.0, binary=0))
        admissibility.append(policy.admissible(state, ctx).admissible)

    assert admissibility == [True, True, False]
    assert state.extra["trust_score"] == pytest.approx(0.2573, abs=1e-4)


def test_aema_params_are_the_frozen_constants():
    p = AEMAPolicy().params
    assert p["alpha_success"] == 0.85
    assert p["beta_failure"] == 0.70
    assert p["gamma_neutral"] == 0.80
    assert p["quarantine_threshold"] == 0.35
    assert p["initial_trust"] == 0.75


def test_end_to_end_aema_equivalence_legacy_vs_step1():
    """
    THE acceptance criterion: identical workload + identical initial memory state must
    produce the same A-EMA trust trajectory on the legacy store path and the new
    run-scoped path.
    """
    async def _run_both():
        seed_kwargs = dict(
            id="m1", task_domain=TaskDomain.CODING, trigger_condition=TRIGGER,
            strategy_lesson="Convert the recursion to an iterative traversal using collections.deque.",
            pitfall="Do not raise sys.setrecursionlimit.",
            trust_score=0.75, status=ExperienceStatus.ACTIVE,
        )
        request_kwargs = dict(
            task_input=TASK, task_domain=TaskDomain.CODING,
            memory_enabled=True, memory_mode=MemoryMode.ADAPTIVE,
            provider=ModelProvider.MOCK, evaluator=EvaluatorName.PYTEST_EXECUTION,
            evaluator_config={"test_code": TEST_SUITE, "timeout_s": 30},
        )

        # --- legacy path ---
        legacy_store = _fresh_store()
        await legacy_store.add_experience(Experience(**seed_kwargs))
        legacy_trust = []
        for _ in range(3):
            await execute_task(TaskExecuteRequest(**request_kwargs), memory_store=legacy_store)
            legacy_trust.append((await legacy_store.get_experience("m1")).trust_score)

        # --- Step 1 path, same initial state ---
        bank = _bank(_record("m1", trust=0.75))
        run = RunContext(bank=bank, policy=AEMAPolicy(), condition_id="equivalence")
        step1_trust = []
        for _ in range(3):
            await execute_task(TaskExecuteRequest(**request_kwargs), run_context=run)
            step1_trust.append(run.trust_state.get("m1").extra["trust_score"])

        assert legacy_trust == pytest.approx(step1_trust, abs=1e-9), (
            f"A-EMA trajectory diverged: legacy={legacy_trust} step1={step1_trust}"
        )

        legacy_exp = await legacy_store.get_experience("m1")
        step1_state = run.trust_state.get("m1")
        assert legacy_exp.uses_count == step1_state.uses
        assert legacy_exp.successes_count == step1_state.successes
        assert legacy_exp.failures_count == step1_state.failures

    asyncio.run(_run_both())


# ==============================================================================
# 5. Retrieval through injected interfaces
# ==============================================================================

def test_policy_backed_retrieval_finds_a_matching_memory():
    run = _run()
    retriever = PolicyBackedRetriever(run=run, ranker=LegacyModeRanker(MemoryMode.ADAPTIVE))
    results, diag = retriever.retrieve(query=TASK, domain=TaskDomain.CODING, top_k=2)
    assert len(results) == 1
    assert results[0].record.memory_id == "m1"
    assert 0.60 < results[0].similarity <= 1.0
    assert diag["candidate_count"] == 1
    assert diag["admissible_count"] == 1


def test_retrieval_honours_the_injected_policy_gate():
    run = _run()
    for i in range(1, 4):
        run.trust_state.apply(_obs(idx=i, reward=0.0, binary=0, run_id=run.run_id))

    retriever = PolicyBackedRetriever(run=run, ranker=LegacyModeRanker(MemoryMode.ADAPTIVE))
    results, diag = retriever.retrieve(query=TASK, domain=TaskDomain.CODING)
    assert results == []
    assert "quarantined" in diag["gate_reasons"]["m1"]


def test_retrieval_ranker_is_injectable():
    run = _run()
    legacy, _ = PolicyBackedRetriever(run, LegacyModeRanker(MemoryMode.SYMMETRIC)).retrieve(
        query=TASK, domain=TaskDomain.CODING)
    simple, _ = PolicyBackedRetriever(run, SimilarityOnlyRanker()).retrieve(
        query=TASK, domain=TaskDomain.CODING)

    assert len(legacy) == len(simple) == 1
    # similarity-only carries no trust term; the legacy composite does
    assert simple[0].composite_score == pytest.approx(simple[0].similarity, abs=1e-9)
    assert legacy[0].composite_score != pytest.approx(legacy[0].similarity, abs=1e-9)


def test_retrieval_excludes_other_domains():
    bank = _bank(_record("m1", domain=TaskDomain.CODING))
    run = _run(bank)
    results, diag = PolicyBackedRetriever(run, LegacyModeRanker(MemoryMode.ADAPTIVE)).retrieve(
        query=TASK, domain=TaskDomain.RESEARCH)
    assert results == []
    assert diag["candidate_count"] == 0


def test_retrieval_does_not_mutate_trust_state():
    run = _run()
    before = run.trust_state.get("m1")
    PolicyBackedRetriever(run, LegacyModeRanker(MemoryMode.ADAPTIVE)).retrieve(
        query=TASK, domain=TaskDomain.CODING)
    assert run.trust_state.get("m1") == before


# ==============================================================================
# 6. Exposure completeness, raw outcome preservation, manifest
# ==============================================================================

def test_exposure_log_is_append_only():
    log = ExposureLog("r1")
    assert not hasattr(log, "update")
    assert not hasattr(log, "delete")
    assert not hasattr(log, "pop")


def test_run_records_one_exposure_per_task_with_raw_outcome():
    async def _go():
        bank = _bank()
        run = RunContext(bank=bank, policy=AEMAPolicy())
        result = await execute_task(
            TaskExecuteRequest(
                task_input=TASK, task_domain=TaskDomain.CODING, memory_enabled=True,
                memory_mode=MemoryMode.ADAPTIVE, provider=ModelProvider.MOCK,
                evaluator=EvaluatorName.PYTEST_EXECUTION,
                evaluator_config={"test_code": TEST_SUITE, "timeout_s": 30},
            ),
            run_context=run,
        )
        assert len(run.exposures) == 1
        rec = run.exposures.records[0]
        assert rec.memory_id == "m1"
        assert rec.run_id == run.run_id
        assert rec.task_index == 1
        assert rec.injected is True
        # raw outcome preserved, not reduced to a trust number
        assert rec.reward == result.outcome_score
        assert rec.binary_outcome == result.binary_outcome
        assert rec.outcome_threshold == result.outcome_threshold
        # attempt detail retained
        assert rec.n_attempts == result.n_attempts
        assert sum(1 for a in rec.attempts if a.is_terminal) == 1
        # state transition captured
        assert rec.policy_state_before["extra"]["trust_score"] == 0.75
        assert rec.policy_state_after["uses"] == 1
        assert rec.memory_content_hash == bank.get("m1").content_hash

    asyncio.run(_go())


def test_task_with_no_memory_is_still_logged():
    async def _go():
        run = RunContext(bank=_bank(), policy=AEMAPolicy())
        await execute_task(
            TaskExecuteRequest(
                task_input=TASK, task_domain=TaskDomain.CODING,
                memory_enabled=False, memory_mode=MemoryMode.OFF,
                provider=ModelProvider.MOCK, evaluator=EvaluatorName.HEURISTIC,
            ),
            run_context=run,
        )
        assert len(run.exposures) == 1
        rec = run.exposures.records[0]
        assert rec.memory_id is None
        assert rec.fallback_occurred is True
        assert rec.injected is False
        assert run.trust_state.get("m1").uses == 0

    asyncio.run(_go())


def test_manifest_captures_reproducibility_metadata():
    # S8: `temperature` is an EXECUTABLE run parameter and must be supplied to the
    # constructor. A manifest override for it is deliberately discarded so the
    # manifest can never assert a value that execution did not use.
    # S8/S9: temperature, seed and provider are EXECUTABLE run parameters supplied to
    # the constructor. Manifest overrides for them are discarded so the manifest can
    # never assert a configuration that execution did not use.
    run = RunContext(bank=_bank(), policy=AEMAPolicy(), condition_id="E1",
                     temperature=0.0, seed=7, provider="ollama",
                     manifest_overrides={"model": "mock-v1"})
    m = run.manifest
    assert m.run_id == run.run_id
    assert m.condition_id == "E1"
    assert m.policy_name == "aema"
    assert m.policy_params["alpha_success"] == 0.85
    assert m.policy_params_hash
    assert m.bank_hash == run.bank.bank_hash
    assert m.bank_size == 1
    assert m.memory_write_enabled is False
    assert m.python_version and m.platform
    assert m.model == "mock-v1" and m.temperature == 0.0 and m.seed == 7
    import json
    assert json.loads(m.to_json())["run_id"] == run.run_id


def test_exposure_log_round_trips_through_jsonl():
    run = _run()
    run.exposures.append(ExposureRecord(
        run_id=run.run_id, task_id="t1", task_index=1, memory_id="m1",
        exposure_id="e1", reward=0.5, binary_outcome=0,
    ))
    lines = run.exposures.to_jsonl().splitlines()
    assert len(lines) == 1
    import json
    assert json.loads(lines[0])["memory_id"] == "m1"


# ==============================================================================
# 7. memory_write_enabled
# ==============================================================================

def test_fixed_bank_run_does_not_write_candidate_memories():
    async def _go():
        bank = _bank()
        store = _fresh_store()
        run = RunContext(bank=bank, policy=AEMAPolicy(), memory_write_enabled=False)
        before_hash = bank.bank_hash

        await execute_task(
            TaskExecuteRequest(
                task_input=TASK, task_domain=TaskDomain.CODING, memory_enabled=True,
                memory_mode=MemoryMode.ADAPTIVE, provider=ModelProvider.MOCK,
                evaluator=EvaluatorName.HEURISTIC,
            ),
            memory_store=store, run_context=run,
        )
        assert bank.bank_hash == before_hash
        assert run.verify_bank_unchanged()
        assert len(await store.list_experiences()) == 0, "no candidate may be written"

    asyncio.run(_go())


def test_memory_write_enabled_is_off_by_default():
    assert RunContext(bank=_bank(), policy=AEMAPolicy()).memory_write_enabled is False


# ==============================================================================
# 8. Replay fidelity and legitimate scope
# ==============================================================================

def test_replay_reproduces_the_live_policy_trajectory_exactly():
    """
    The decisive test: replaying a run's own log through its own policy must
    reproduce the live state trajectory bit for bit.
    """
    async def _go():
        bank = _bank()
        run = RunContext(bank=bank, policy=AEMAPolicy())
        for _ in range(3):
            await execute_task(
                TaskExecuteRequest(
                    task_input=TASK, task_domain=TaskDomain.CODING, memory_enabled=True,
                    memory_mode=MemoryMode.ADAPTIVE, provider=ModelProvider.MOCK,
                    evaluator=EvaluatorName.PYTEST_EXECUTION,
                    evaluator_config={"test_code": TEST_SUITE, "timeout_s": 30},
                ),
                run_context=run,
            )

        live_state = run.trust_state.get("m1").to_dict()
        result = replay_log(
            run.exposures, AEMAPolicy(),
            initial_trust_by_memory={"m1": bank.get("m1").initial_trust},
        )
        assert result.final_states["m1"] == live_state

        # Per-step transitions must match the ones recorded live.
        live_steps = [
            (r.policy_state_before, r.policy_state_after)
            for r in run.exposures.records if r.memory_id == "m1"
        ]
        replay_steps = [(s.state_before, s.state_after) for s in result.steps]
        assert replay_steps == live_steps

    asyncio.run(_go())


def test_replay_is_deterministic():
    obs = [_obs(idx=i, reward=0.1, binary=0) for i in range(1, 5)]
    a = replay_observations(obs, AEMAPolicy())
    b = replay_observations(obs, AEMAPolicy())
    assert a.final_states == b.final_states
    assert a.decision_signature() == b.decision_signature()


def test_replay_compares_policies_over_identical_evidence():
    log = ExposureLog("r1")
    for i in range(1, 5):
        log.append(ExposureRecord(
            run_id="r1", task_id=f"t{i}", task_index=i, memory_id="m1",
            exposure_id=f"e{i}", reward=0.0, binary_outcome=0, outcome_threshold=0.80,
        ))
    results = compare_policies(log, [AEMAPolicy(), StaticTrustPolicy()])

    assert results["aema"].first_suppression_index("m1") == 3
    assert results["static"].first_suppression_index("m1") is None
    # Same evidence consumed by both.
    assert len(results["aema"].steps) == len(results["static"].steps) == 4


def test_replay_does_not_expose_counterfactual_outcomes():
    """Replay must not claim to reconstruct outcomes that were never observed."""
    result = replay_observations([_obs()], AEMAPolicy())
    for forbidden in ("counterfactual_outcomes", "counterfactual_rewards", "predicted_outcomes"):
        assert not hasattr(result, forbidden)

    import ai_service.experiment.replay as rp
    assert not hasattr(rp, "simulate_outcomes")
    assert not hasattr(rp, "counterfactual_replay")


def test_replay_skips_non_observation_rows():
    log = ExposureLog("r1")
    log.append(ExposureRecord(run_id="r1", task_id="t1", task_index=1,
                              memory_id=None, exposure_id="e1"))
    log.append(ExposureRecord(run_id="r1", task_id="t2", task_index=2,
                              memory_id="m1", exposure_id="e2",
                              reward=0.0, binary_outcome=0))
    assert len(log) == 2
    assert len(log.observations()) == 1
    assert len(replay_log(log, AEMAPolicy()).steps) == 1
