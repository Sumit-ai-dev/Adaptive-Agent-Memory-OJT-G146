"""
Step 1.5 Experimental Harness Test Suite.

Verifies the measurement instrument, not any experiment:

  R3           exactly one trust decision boundary on the experimental path
  E0/E1        same task, two conditions, differing only in the memory condition
  Pairing      pair_id linkage, identical task hash, isolated run ids
  Baseline     populated only from an ACTUAL E0 execution; never fabricated
  Manifest     persisted BEFORE execution; tamper-evident
  Isolation    runs that actively mutate their own state leave others untouched
  Integrity    the fixed bank cannot change
"""

import asyncio
import json
import os
import tempfile

import pytest

from ai_service.experiment import (
    ConditionSpec,
    ExperimentHarness,
    MemoryBank,
    MemoryRecord,
    ModelSpec,
    PairedObservation,
    RunContext,
    SimilarityOnlyRanker,
    TaskSpec,
    make_e0,
    make_e1,
    new_pair_id,
    replay_log,
)
from ai_service.experiment.retrieval import LegacyModeRanker, PolicyBackedRetriever
from ai_service.trust import AEMAPolicy, Observation, StaticTrustPolicy
from models.domain import MemoryMode, TaskDomain
from models.task import EvaluatorName

TRIGGER = "Fixing RecursionError in deep binary tree traversal"
PROMPT = "Fix the RecursionError raised by my recursive binary tree traversal function"
TEST_SUITE = "from solution import add\ndef test_a():\n    assert add(2, 3) == 5\n"


def _record(mid="m1", trust=0.75, domain=TaskDomain.CODING) -> MemoryRecord:
    return MemoryRecord(
        memory_id=mid, domain=domain, trigger=TRIGGER,
        strategy="Convert the recursion to an iterative traversal using collections.deque.",
        pitfall="Do not raise sys.setrecursionlimit.",
        provenance="authored", initial_trust=trust,
    )


def _bank(*records) -> MemoryBank:
    return MemoryBank(records or (_record(),), bank_id="harness_bank").ensure_embeddings()


def _task(task_id="task_a", prompt=PROMPT, evaluator=EvaluatorName.HEURISTIC, cfg=None) -> TaskSpec:
    return TaskSpec(
        task_id=task_id, prompt=prompt, domain=TaskDomain.CODING,
        evaluator=evaluator, evaluator_config=cfg or {},
    )


def _pytest_task(task_id="task_pytest") -> TaskSpec:
    return TaskSpec(
        task_id=task_id, prompt=PROMPT, domain=TaskDomain.CODING,
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        evaluator_config={"test_code": TEST_SUITE, "timeout_s": 30},
    )


def _harness(bank=None, outdir=None) -> ExperimentHarness:
    return ExperimentHarness(bank=bank or _bank(), model_spec=ModelSpec(), output_dir=outdir)


def _obs(mid="m1", idx=1, reward=0.0, binary=0, run_id="r") -> Observation:
    return Observation(memory_id=mid, task_id=f"t{idx}", run_id=run_id, task_index=idx,
                       reward=reward, binary_outcome=binary, outcome_threshold=0.80)


# ==============================================================================
# R3 -- exactly one trust decision boundary
# ==============================================================================

def test_r3_default_experimental_ranker_is_similarity_only():
    run = RunContext(bank=_bank(), policy=AEMAPolicy())
    assert isinstance(run.ranker, SimilarityOnlyRanker)
    assert run.ranker.name == "similarity_only"


def test_r3_experimental_path_never_calls_legacy_trust_gates(monkeypatch):
    """
    Hard proof: make the legacy Beta/quarantine helpers explode. If the experimental
    retrieval path touches them, this test fails.
    """
    import ai_service.experiment.retrieval as rt

    def boom(*a, **kw):
        raise AssertionError("legacy trust gate called on the experimental path")

    monkeypatch.setattr(rt, "should_quarantine", boom)
    monkeypatch.setattr(rt, "beta_lcb", boom)

    run = RunContext(bank=_bank(), policy=AEMAPolicy())
    retriever = PolicyBackedRetriever(run=run, ranker=SimilarityOnlyRanker())
    results, _ = retriever.retrieve(query=PROMPT, domain=TaskDomain.CODING)
    assert len(results) == 1


def test_r3_legacy_ranker_still_available_and_does_call_them(monkeypatch):
    """The legacy implementation is preserved -- it simply must be opted into."""
    import ai_service.experiment.retrieval as rt

    calls = []
    monkeypatch.setattr(rt, "should_quarantine", lambda *a, **k: calls.append("q") or False)
    monkeypatch.setattr(rt, "beta_lcb", lambda *a, **k: calls.append("l") or 1.0)

    run = RunContext(bank=_bank(), policy=AEMAPolicy(), ranker=LegacyModeRanker(MemoryMode.ADAPTIVE))
    PolicyBackedRetriever(run=run, ranker=run.ranker).retrieve(query=PROMPT, domain=TaskDomain.CODING)
    assert calls, "legacy ranker must still consult the pre-existing filter"


def test_r3_exactly_one_policy_admissibility_call_per_candidate():
    """Counts the trust decision boundaries actually consulted."""
    class CountingPolicy(AEMAPolicy):
        name = "counting"

        def __init__(self):
            super().__init__()
            self.admissible_calls = 0

        def admissible(self, state, ctx):
            self.admissible_calls += 1
            return super().admissible(state, ctx)

    policy = CountingPolicy()
    bank = _bank(_record("m1"), _record("m2"))
    run = RunContext(bank=bank, policy=policy)
    PolicyBackedRetriever(run=run, ranker=SimilarityOnlyRanker()).retrieve(
        query=PROMPT, domain=TaskDomain.CODING)
    assert policy.admissible_calls == 2, "exactly one gate consultation per candidate"


def test_r3_policy_swap_changes_only_the_policy_decision():
    bank = _bank()
    quarantined = RunContext(bank=bank, policy=AEMAPolicy())
    for i in range(1, 4):
        quarantined.trust_state.apply(_obs(idx=i, run_id=quarantined.run_id))

    permissive = RunContext(bank=bank, policy=StaticTrustPolicy())
    for i in range(1, 4):
        permissive.trust_state.apply(_obs(idx=i, run_id=permissive.run_id))

    a, _ = PolicyBackedRetriever(quarantined, SimilarityOnlyRanker()).retrieve(
        PROMPT, TaskDomain.CODING)
    b, _ = PolicyBackedRetriever(permissive, SimilarityOnlyRanker()).retrieve(
        PROMPT, TaskDomain.CODING)

    assert a == []                      # AEMA suppressed it
    assert len(b) == 1                  # static did not
    assert b[0].similarity == pytest.approx(
        PolicyBackedRetriever(permissive, SimilarityOnlyRanker())
        .retrieve(PROMPT, TaskDomain.CODING)[0][0].similarity
    )


def test_r3_e1_condition_defaults_to_similarity_only_ranker():
    cond = make_e1(policy=AEMAPolicy())
    assert isinstance(cond.ranker, SimilarityOnlyRanker)
    assert cond.describe()["ranker_name"] == "similarity_only"


# ==============================================================================
# E0 / E1 execution
# ==============================================================================

def test_same_task_runs_under_both_conditions():
    async def _go():
        obs = await _harness().run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        assert obs.complete
        assert obs.e0.condition_id == "E0"
        assert obs.e1.condition_id == "E1"
        assert obs.task_specification_identical
    asyncio.run(_go())


def test_e0_injects_no_memory_and_touches_no_trust_state():
    async def _go():
        h = _harness()
        result = await h.run_condition(_pytest_task(), make_e0())
        assert result.memory_enabled is False
        assert result.memory_ids_exposed == []
        assert result.policy_name is None
        assert result.ranker_name is None
        # the no-memory task is still logged explicitly
        assert len(result.exposures) == 1
        assert result.exposures[0]["memory_id"] is None
        assert result.exposures[0]["injected"] is False
        assert result.exposures[0]["fallback_occurred"] is True
    asyncio.run(_go())


def test_e1_can_inject_memory():
    async def _go():
        result = await _harness().run_condition(_pytest_task(), make_e1(AEMAPolicy()))
        assert result.memory_enabled is True
        assert result.memory_ids_exposed == ["m1"]
        assert result.policy_name == "aema"
        assert result.ranker_name == "similarity_only"
        assert result.exposures[0]["injected"] is True
    asyncio.run(_go())


def test_evaluator_is_identical_across_conditions():
    async def _go():
        obs = await _harness().run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        assert obs.e0.evaluator_name == obs.e1.evaluator_name == "pytest_execution"
        assert obs.e0.evaluator_version == obs.e1.evaluator_version
        assert obs.e0.outcome_threshold == obs.e1.outcome_threshold
    asyncio.run(_go())


def test_model_configuration_is_identical_across_conditions():
    async def _go():
        obs = await _harness().run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        for attr in ("model", "model_version", "provider", "temperature"):
            assert getattr(obs.e0, attr) == getattr(obs.e1, attr)
    asyncio.run(_go())


def test_conditions_differ_only_in_the_memory_condition():
    async def _go():
        obs = await _harness().run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        same = ("task_id", "task_hash", "evaluator_name", "evaluator_version",
                "outcome_threshold", "model", "model_version", "provider", "temperature")
        for attr in same:
            assert getattr(obs.e0, attr) == getattr(obs.e1, attr), f"{attr} differs"
        assert obs.e0.memory_enabled != obs.e1.memory_enabled
    asyncio.run(_go())


def test_memory_write_is_disabled_and_cannot_be_enabled_for_a_condition():
    with pytest.raises(ValueError, match="memory_write_enabled must be False"):
        ConditionSpec(condition_id="X", memory_enabled=True,
                      policy=AEMAPolicy(), memory_write_enabled=True)


def test_memory_enabled_condition_requires_a_policy():
    with pytest.raises(ValueError, match="requires a policy"):
        ConditionSpec(condition_id="X", memory_enabled=True)


# ==============================================================================
# S6 -- top_k is executed, not merely recorded
# ==============================================================================

def _bank_of(n: int) -> MemoryBank:
    """n near-duplicate memories, all clearing the similarity threshold."""
    return MemoryBank(
        [
            MemoryRecord(
                memory_id=f"m{i}", domain=TaskDomain.CODING,
                trigger=f"{TRIGGER} variant {i}",
                strategy=f"Iterative traversal approach {i}.",
                pitfall="Do not raise sys.setrecursionlimit.",
                initial_trust=0.75,
            )
            for i in range(1, n + 1)
        ],
        bank_id=f"bank{n}",
    ).ensure_embeddings()


@pytest.mark.parametrize("top_k", [1, 2, 3])
def test_s6_top_k_controls_the_number_of_memories_actually_retrieved(top_k):
    run = RunContext(bank=_bank_of(4), policy=AEMAPolicy(), top_k=top_k)
    results, diag = PolicyBackedRetriever(run, SimilarityOnlyRanker()).retrieve(
        query=PROMPT, domain=TaskDomain.CODING, top_k=run.top_k,
    )
    assert diag["admissible_count"] == 4, "all four must be admissible for this to be a real test"
    assert len(results) == top_k


def test_s6_condition_top_k_reaches_actual_execution():
    """End-to-end: ConditionSpec.top_k -> RunContext -> execute_task -> retrieval."""
    async def _go():
        h = _harness(bank=_bank_of(4))
        result = await h.run_condition(
            _pytest_task(), make_e1(AEMAPolicy(), top_k=3),
        )
        assert len(result.memory_ids_exposed) == 3, (
            f"top_k=3 must expose 3 memories, got {result.memory_ids_exposed}"
        )
        assert len([r for r in result.exposures if r["memory_id"]]) == 3
    asyncio.run(_go())


def test_s6_manifest_describes_the_actual_execution():
    """The manifest's top_k must equal the number actually used, for several values."""
    async def _go():
        for k in (1, 2, 3):
            with tempfile.TemporaryDirectory() as tmp:
                h = _harness(bank=_bank_of(4), outdir=tmp)
                result = await h.run_condition(_pytest_task(), make_e1(AEMAPolicy(), top_k=k))
                manifest = json.load(open(result.manifest_path, encoding="utf-8"))
                assert manifest["top_k"] == k
                assert len(result.memory_ids_exposed) == k, (
                    f"manifest says top_k={manifest['top_k']} but "
                    f"{len(result.memory_ids_exposed)} memories were exposed"
                )
    asyncio.run(_go())


def test_s6_manifest_top_k_cannot_be_overridden_away_from_the_executed_value():
    """A stale override must not let the manifest disagree with execution."""
    run = RunContext(
        bank=_bank_of(2), policy=AEMAPolicy(), top_k=3,
        manifest_overrides={"top_k": 99},
    )
    assert run.top_k == 3
    assert run.manifest.top_k == 3


def test_s6_no_hardcoded_experimental_top_k_remains():
    import inspect
    import ai_service.graph as G

    src = inspect.getsource(G.execute_task)
    assert '"top_k": 2' not in src, "hardcoded experimental top_k still present"
    assert "run_context.top_k" in src


# ==============================================================================
# S8 -- temperature is executed, not merely recorded
# ==============================================================================

class _FakeSDK:
    """Captures the exact kwargs handed to the provider SDK."""

    sent = []

    class _Msg:
        content = "```python\ndef add(a, b):\n    return a + b\n```"

    class _Choice:
        message = None

    class _Usage:
        total_tokens = 42

    class _Resp:
        choices = []
        usage = None

    class _Completions:
        async def create(self, **kwargs):
            _FakeSDK.sent.append(kwargs)
            return _FakeSDK._make_response()

    class _Chat:
        completions = None

    def __init__(self, **kwargs):
        _FakeSDK.sent.append({"__client_base_url__": kwargs.get("base_url")})
        self.chat = _FakeSDK._Chat()
        self.chat.completions = _FakeSDK._Completions()

    @staticmethod
    def _make_response():
        resp = _FakeSDK._Resp()
        choice = _FakeSDK._Choice()
        choice.message = _FakeSDK._Msg()
        resp.choices = [choice]
        resp.usage = _FakeSDK._Usage()
        return resp


@pytest.fixture
def fake_sdk(monkeypatch):
    import importlib

    llm = importlib.import_module("ai_service.llm_client")
    _FakeSDK.sent = []
    monkeypatch.setattr(llm, "AsyncOpenAI", _FakeSDK)
    return _FakeSDK


def _sdk_temperatures():
    return sorted({k["temperature"] for k in _FakeSDK.sent if "temperature" in k})


def _sdk_base_urls():
    return {k["__client_base_url__"] for k in _FakeSDK.sent if "__client_base_url__" in k}


@pytest.mark.parametrize("temperature", [0.0, 0.7, 1.3])
def test_s8_requested_temperature_reaches_the_provider_and_matches_manifest(fake_sdk, temperature):
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            h = ExperimentHarness(
                bank=_bank(), output_dir=tmp,
                model_spec=ModelSpec(provider="ollama", model="qwen2.5:1.5b",
                                     model_version="qwen2.5:1.5b", temperature=temperature),
            )
            result = await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
            assert _sdk_temperatures() == [temperature], (
                f"provider received {_sdk_temperatures()}, expected [{temperature}]"
            )
            manifest = json.load(open(result.manifest_path, encoding="utf-8"))
            assert manifest["temperature"] == temperature
    asyncio.run(_go())


def test_s8_every_llm_call_site_uses_the_same_temperature(fake_sdk):
    """execute_node AND reflect_node must both dispatch at the run's temperature."""
    async def _go():
        h = ExperimentHarness(
            bank=_bank(),
            model_spec=ModelSpec(provider="ollama", model="qwen2.5:1.5b", temperature=0.9),
        )
        await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
        calls = [k for k in _FakeSDK.sent if "temperature" in k]
        assert len(calls) >= 2, "expected execution AND reflection calls"
        assert _sdk_temperatures() == [0.9]
    asyncio.run(_go())


def test_s8_every_llm_call_site_uses_the_declared_provider(fake_sdk):
    """
    reflect_node previously called the gateway with no config, falling through to a
    default resolved from ambient environment variables -- a different provider
    entirely from the one the manifest declared.
    """
    async def _go():
        h = ExperimentHarness(
            bank=_bank(),
            model_spec=ModelSpec(provider="ollama", model="qwen2.5:1.5b", temperature=0.0),
        )
        await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
        assert _sdk_base_urls() == {"http://localhost:11434/v1"}, (
            f"calls leaked to another provider: {_sdk_base_urls()}"
        )
        models = {k["model"] for k in _FakeSDK.sent if "model" in k}
        assert models == {"qwen2.5:1.5b"}
    asyncio.run(_go())


def test_s8_unspecified_temperature_preserves_provider_default_without_false_claim(fake_sdk):
    async def _go():
        from ai_service.graph import execute_task
        from models.task import TaskExecuteRequest

        run = RunContext(bank=_bank(), policy=AEMAPolicy())      # temperature unspecified
        assert run.temperature is None
        assert run.manifest.temperature is None, "must not assert a value it did not set"

        task = _pytest_task()
        await execute_task(
            TaskExecuteRequest(
                task_input=task.prompt, task_domain=TaskDomain.CODING, memory_enabled=True,
                provider="ollama", model="qwen2.5:1.5b", evaluator=task.evaluator,
                evaluator_config=dict(task.evaluator_config),
            ),
            run_context=run,
        )
        from models.provider import ModelProvider, ProviderConfig
        assert _sdk_temperatures() == [ProviderConfig.default_for(ModelProvider.OLLAMA).temperature]
    asyncio.run(_go())


def test_s8_stale_manifest_override_cannot_contradict_execution():
    run = RunContext(bank=_bank(), policy=AEMAPolicy(), temperature=0.3,
                     manifest_overrides={"temperature": 99.0})
    assert run.temperature == 0.3
    assert run.manifest.temperature == 0.3


def test_s8_no_llm_call_site_dispatches_without_a_resolved_config():
    """Guards against a future call site reintroducing the unconfigured-gateway bug."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1] / "ai-service"
    offenders = []
    for path in root.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"llm_gateway\.generate\((.{0,160})", text, re.DOTALL):
            if "config=" not in match.group(1):
                offenders.append(f"{path.name}: {match.group(1)[:60]!r}")
    assert not offenders, f"llm_gateway.generate called without config: {offenders}"


# ==============================================================================
# S10 -- no silent ambient provider selection
# ==============================================================================

def test_s10_explicitly_configured_provider_call_works(fake_sdk):
    """An explicitly declared provider must still work, credentials from env included."""
    async def _go():
        from ai_service.llm_client import UniversalLLMClient
        from models.provider import ModelProvider, ProviderConfig

        client = UniversalLLMClient()
        cfg = ProviderConfig(provider=ModelProvider.OLLAMA, model="qwen2.5:1.5b",
                             base_url="http://localhost:11434/v1", api_key="ollama")
        text, tokens = await client.generate(
            [{"role": "user", "content": "hi"}], config=cfg, temperature=0.0,
        )
        assert isinstance(text, str) and tokens > 0
        assert _sdk_base_urls() == {"http://localhost:11434/v1"}
    asyncio.run(_go())


def test_s10_explicit_mock_provider_still_works():
    async def _go():
        from ai_service.llm_client import UniversalLLMClient
        from models.provider import ModelProvider, ProviderConfig

        client = UniversalLLMClient()
        text, tokens = await client.generate(
            [{"role": "user", "content": "hi"}],
            config=ProviderConfig(provider=ModelProvider.MOCK, model="mock-deterministic-v1"),
        )
        assert isinstance(text, str) and tokens > 0
    asyncio.run(_go())


def test_s10_unconfigured_call_fails_loudly():
    async def _go():
        from ai_service.llm_client import ProviderConfigurationError, UniversalLLMClient

        client = UniversalLLMClient()
        assert client.default_config is None, "no implicit provider may be resolved"
        with pytest.raises(ProviderConfigurationError, match="No provider configuration"):
            await client.generate([{"role": "user", "content": "hi"}])
    asyncio.run(_go())


def test_s10_ambient_env_cannot_select_a_provider(monkeypatch):
    """Setting hosted-provider keys must not make an unconfigured call reachable."""
    import importlib

    llm = importlib.import_module("ai_service.llm_client")
    for key in ("GROQ_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "NVIDIA_API_KEY"):
        monkeypatch.setattr(llm.settings, key, "sk-ambient-should-be-ignored", raising=False)

    async def _go():
        client = llm.UniversalLLMClient()
        assert client.default_config is None
        with pytest.raises(llm.ProviderConfigurationError):
            await client.generate([{"role": "user", "content": "hi"}])
    asyncio.run(_go())


def test_s10_ambient_env_cannot_change_an_experimental_runs_provider(fake_sdk, monkeypatch):
    """A run declaring ollama must contact ollama even with hosted keys present."""
    import importlib

    llm = importlib.import_module("ai_service.llm_client")
    monkeypatch.setattr(llm.settings, "OPENAI_API_KEY", "sk-ambient", raising=False)
    monkeypatch.setattr(llm.settings, "GROQ_API_KEY", "gsk-ambient", raising=False)

    async def _go():
        h = ExperimentHarness(
            bank=_bank(),
            model_spec=ModelSpec(provider="ollama", model="qwen2.5:1.5b", temperature=0.0),
        )
        await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
        assert _sdk_base_urls() == {"http://localhost:11434/v1"}, (
            f"ambient credentials redirected the run: {_sdk_base_urls()}"
        )
    asyncio.run(_go())


def test_s10_resolver_declines_rather_than_guessing_when_no_provider_declared():
    from ai_service.llm_client import resolve_provider_config

    cfg, temp = resolve_provider_config({"task_input": "x"})
    assert cfg is None, "resolver must not invent a provider"


def test_s10_ambient_resolution_helper_is_gone():
    from ai_service.llm_client import UniversalLLMClient

    assert not hasattr(UniversalLLMClient, "_resolve_default_config")


# ==============================================================================
# S9 -- a recorded seed must be an executed seed
# ==============================================================================

def test_s9_seed_capability_map_is_explicit():
    from models.provider import ModelProvider, provider_supports_seed

    assert provider_supports_seed(ModelProvider.OLLAMA) is True
    assert provider_supports_seed(ModelProvider.OPENAI) is True
    assert provider_supports_seed(ModelProvider.ANTHROPIC) is False
    assert provider_supports_seed(ModelProvider.MOCK) is False


def test_s9_requested_seed_reaches_the_provider(fake_sdk):
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            h = ExperimentHarness(
                bank=_bank(), output_dir=tmp,
                model_spec=ModelSpec(provider="ollama", model="qwen2.5:1.5b",
                                     temperature=0.0, seed=1234),
            )
            result = await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
            seeds = sorted({k["seed"] for k in _FakeSDK.sent if "seed" in k})
            assert seeds == [1234], f"provider received seeds {seeds}"
            manifest = json.load(open(result.manifest_path, encoding="utf-8"))
            assert manifest["seed"] == 1234
            assert manifest["seed_supported"] is True
    asyncio.run(_go())


def test_s9_seed_is_rejected_for_a_provider_that_cannot_honour_it():
    from models.provider import UnsupportedSeedError

    with pytest.raises(UnsupportedSeedError, match="does not support a seed"):
        ModelSpec(provider="anthropic", model="claude-x", seed=7)
    with pytest.raises(UnsupportedSeedError):
        ModelSpec(provider="mock", model="mock-deterministic-v1", seed=7)


def test_s9_unsupported_provider_records_seed_as_not_applicable(fake_sdk):
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            h = ExperimentHarness(
                bank=_bank(), output_dir=tmp,
                model_spec=ModelSpec(provider="mock", model="mock-deterministic-v1",
                                     temperature=0.0, seed=None),
            )
            result = await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
            manifest = json.load(open(result.manifest_path, encoding="utf-8"))
            assert manifest["seed"] is None
            assert manifest["seed_supported"] is False, "must be recorded as not-applicable"
            assert not any("seed" in k for k in _FakeSDK.sent)
    asyncio.run(_go())


def test_s9_no_seed_in_manifest_without_execution(fake_sdk):
    """The exact defect: a seed may not appear in a manifest it never reached."""
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            h = ExperimentHarness(
                bank=_bank(), output_dir=tmp,
                model_spec=ModelSpec(provider="ollama", model="qwen2.5:1.5b",
                                     temperature=0.0, seed=99),
            )
            result = await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
            manifest = json.load(open(result.manifest_path, encoding="utf-8"))
            sent_seeds = {k["seed"] for k in _FakeSDK.sent if "seed" in k}
            if manifest["seed"] is not None:
                assert sent_seeds == {manifest["seed"]}, (
                    f"manifest records seed={manifest['seed']} but provider saw {sent_seeds}"
                )
    asyncio.run(_go())


def test_s9_stale_seed_override_cannot_contradict_execution():
    run = RunContext(bank=_bank(), policy=AEMAPolicy(), provider="ollama", seed=5,
                     manifest_overrides={"seed": 999, "seed_supported": True})
    assert run.seed == 5
    assert run.manifest.seed == 5


def test_s9_seed_requires_a_declared_provider():
    with pytest.raises(ValueError, match="requires an explicit provider"):
        RunContext(bank=_bank(), policy=AEMAPolicy(), seed=5)


# ==============================================================================
# S11 -- the EFFECTIVE evaluator threshold is what gets recorded
# ==============================================================================

def test_s11_effective_threshold_is_a_single_shared_function():
    from ai_service.tools.evaluator import effective_outcome_threshold

    assert effective_outcome_threshold(EvaluatorName.PYTEST_EXECUTION, 0.8) == 1.0
    assert effective_outcome_threshold(EvaluatorName.HEURISTIC, 0.8) == 0.8
    assert effective_outcome_threshold(EvaluatorName.EXACT_MATCH_F1, 0.65) == 0.65
    assert effective_outcome_threshold(None, 0.8) == 0.8
    # accepts the raw string form used in state/manifests
    assert effective_outcome_threshold("pytest_execution", 0.8) == 1.0


@pytest.mark.parametrize(
    "evaluator,cfg,expected",
    [
        (EvaluatorName.PYTEST_EXECUTION, {"test_code": TEST_SUITE, "timeout_s": 30}, 1.0),
        (EvaluatorName.HEURISTIC, {}, 0.8),
    ],
)
def test_s11_manifest_records_the_executed_threshold(evaluator, cfg, expected):
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            task = TaskSpec(
                task_id="t", prompt=PROMPT, domain=TaskDomain.CODING,
                evaluator=evaluator, evaluator_config=cfg,   # requested stays 0.8
            )
            h = _harness(outdir=tmp)
            result = await h.run_condition(task, make_e1(AEMAPolicy()))
            manifest = json.load(open(result.manifest_path, encoding="utf-8"))

            assert manifest["outcome_threshold"] == expected
            assert manifest["outcome_threshold"] == result.outcome_threshold, (
                "manifest threshold must equal the one execution applied"
            )
            assert manifest["requested_outcome_threshold"] == 0.8
    asyncio.run(_go())


def test_s11_binary_outcome_is_consistent_with_the_effective_threshold():
    async def _go():
        task = TaskSpec(
            task_id="t", prompt=PROMPT, domain=TaskDomain.CODING,
            evaluator=EvaluatorName.PYTEST_EXECUTION,
            evaluator_config={"test_code": TEST_SUITE, "timeout_s": 30},
        )
        result = await _harness().run_condition(task, make_e1(AEMAPolicy()))
        expected = 1 if result.terminal_reward >= result.outcome_threshold else 0
        assert result.binary_outcome == expected
        for attempt in result.attempts:
            assert attempt["outcome_threshold"] == result.outcome_threshold
    asyncio.run(_go())


def test_s11_stale_threshold_override_cannot_contradict_execution():
    run = RunContext(bank=_bank(), policy=AEMAPolicy(),
                     evaluator_name="pytest_execution", outcome_threshold=0.8,
                     manifest_overrides={"outcome_threshold": 0.123})
    assert run.outcome_threshold == 1.0
    assert run.manifest.outcome_threshold == 1.0
    assert run.manifest.requested_outcome_threshold == 0.8


def test_s11_a_new_fixed_threshold_evaluator_only_needs_one_declaration():
    """Guards the single-source-of-truth property the fix is built on."""
    import ai_service.tools.evaluator as ev

    assert hasattr(ev, "_FIXED_EFFECTIVE_THRESHOLDS")
    assert ev._FIXED_EFFECTIVE_THRESHOLDS[EvaluatorName.PYTEST_EXECUTION] == 1.0
    # the evaluator must not hardcode the number anywhere else
    import inspect
    src = inspect.getsource(ev.PytestExecutionEvaluator)
    assert "outcome_threshold=1.0" not in src


# ==============================================================================
# S12 -- max_tokens is executed AND recorded
# ==============================================================================

def test_s12_provider_default_max_tokens_is_recorded_explicitly(fake_sdk):
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            h = ExperimentHarness(
                bank=_bank(), output_dir=tmp,
                model_spec=ModelSpec(provider="ollama", model="qwen2.5:1.5b",
                                     temperature=0.0, max_tokens=None),
            )
            result = await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
            manifest = json.load(open(result.manifest_path, encoding="utf-8"))
            sdk = sorted({k["max_tokens"] for k in _FakeSDK.sent if "max_tokens" in k})

            from models.provider import ModelProvider, ProviderConfig
            provider_default = ProviderConfig.default_for(ModelProvider.OLLAMA).max_tokens

            assert manifest["max_tokens"] == provider_default == 2048, "default preserved"
            assert manifest["max_tokens_source"] == "provider_default"
            assert sdk == [manifest["max_tokens"]], "provider must receive the recorded value"
    asyncio.run(_go())


def test_s12_explicit_max_tokens_reaches_the_provider_and_manifest(fake_sdk):
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            h = ExperimentHarness(
                bank=_bank(), output_dir=tmp,
                model_spec=ModelSpec(provider="ollama", model="qwen2.5:1.5b",
                                     temperature=0.0, max_tokens=512),
            )
            result = await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
            manifest = json.load(open(result.manifest_path, encoding="utf-8"))
            sdk = sorted({k["max_tokens"] for k in _FakeSDK.sent if "max_tokens" in k})

            assert manifest["max_tokens"] == 512
            assert manifest["max_tokens_source"] == "explicit"
            assert sdk == [512]
    asyncio.run(_go())


def test_s12_max_tokens_is_never_invisible():
    """Executed-but-unrecorded was the defect; the manifest must always state it."""
    run = RunContext(bank=_bank(), policy=AEMAPolicy(), provider="ollama")
    assert run.manifest.max_tokens is not None
    assert run.manifest.max_tokens_source == "provider_default"


def test_s12_stale_max_tokens_override_cannot_contradict_execution():
    run = RunContext(bank=_bank(), policy=AEMAPolicy(), provider="ollama", max_tokens=256,
                     manifest_overrides={"max_tokens": 9999, "max_tokens_source": "lies"})
    assert run.max_tokens == 256
    assert run.manifest.max_tokens == 256
    assert run.manifest.max_tokens_source == "explicit"


# ==============================================================================
# Pairing
# ==============================================================================

def test_pair_id_links_both_conditions():
    async def _go():
        obs = await _harness().run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        assert obs.e0.pair_id == obs.e1.pair_id == obs.pair_id
    asyncio.run(_go())


def test_run_ids_remain_distinct_and_isolated():
    async def _go():
        obs = await _harness().run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        assert obs.e0.run_id != obs.e1.run_id
        for rec in obs.e0.exposures:
            assert rec["run_id"] == obs.e0.run_id
        for rec in obs.e1.exposures:
            assert rec["run_id"] == obs.e1.run_id
    asyncio.run(_go())


def test_task_hash_matches_and_is_content_sensitive():
    a, b = _task(), _task()
    assert a.task_hash == b.task_hash
    assert _task(prompt="different").task_hash != a.task_hash
    assert _task(evaluator=EvaluatorName.PYTEST_EXECUTION).task_hash != a.task_hash
    assert _task(cfg={"x": 1}).task_hash != a.task_hash


def test_observed_paired_difference_is_recorded_without_causal_language():
    async def _go():
        obs = await _harness().run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        diff = obs.observed_paired_difference()
        assert set(diff) == {"reward_difference", "binary_difference"}
        assert diff["reward_difference"] == obs.e1.terminal_reward - obs.e0.terminal_reward

        # The harness must not encode a causal claim.
        for banned in ("causal_effect", "treatment_effect", "causal_lift", "net_benefit", "lift"):
            assert not hasattr(obs, banned)
        import ai_service.experiment.harness as hm
        src = open(hm.__file__, encoding="utf-8").read().lower()
        for banned in ("def causal", "treatment_effect", "causal_lift"):
            assert banned not in src
    asyncio.run(_go())


def test_incomplete_pair_yields_no_difference():
    obs = PairedObservation(pair_id="p1", task_id="t", task_hash="h")
    assert obs.complete is False
    assert obs.observed_paired_difference() is None
    assert obs.task_specification_identical is False


# ==============================================================================
# Baseline -- observed only, never fabricated
# ==============================================================================

def test_e0_outcome_populates_the_stateless_baseline_fields():
    async def _go():
        obs = await _harness().run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        e1_rec = obs.e1.exposures[0]
        assert e1_rec["stateless_reward"] == obs.e0.terminal_reward
        assert e1_rec["stateless_binary"] == obs.e0.binary_outcome
    asyncio.run(_go())


def test_e1_alone_does_not_fabricate_a_baseline():
    async def _go():
        result = await _harness().run_condition(_pytest_task(), make_e1(AEMAPolicy()))
        for rec in result.exposures:
            assert rec["stateless_reward"] is None
            assert rec["stateless_binary"] is None
    asyncio.run(_go())


def test_baseline_from_a_different_task_is_rejected():
    async def _go():
        h = _harness()
        other = await h.run_condition(_task(task_id="other", prompt="totally different"), make_e0())
        with pytest.raises(ValueError, match="baseline task_hash does not match"):
            await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()), baseline=other)
    asyncio.run(_go())


def test_set_baseline_rejects_invalid_values():
    run = RunContext(bank=_bank(), policy=AEMAPolicy())
    with pytest.raises(ValueError):
        run.set_baseline(0.5, 2)
    with pytest.raises(ValueError):
        run.set_baseline(1.5, 1)


def test_no_counterfactual_outcome_generation_exists():
    import ai_service.experiment.harness as hm
    import ai_service.experiment.replay as rp

    for module in (hm, rp):
        for banned in ("estimate_baseline", "predict_outcome", "synthesize_baseline",
                       "impute_baseline", "simulate_outcomes", "counterfactual_replay"):
            assert not hasattr(module, banned), f"{banned} found in {module.__name__}"


# ==============================================================================
# Manifest
# ==============================================================================

def test_manifest_is_persisted_before_execution():
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            h = _harness(outdir=tmp)
            task = _pytest_task()

            class Spy(ConditionSpec):
                pass

            # Capture manifest files that exist at the moment execute_task is entered.
            seen = {}
            import ai_service.graph as G
            original = G.execute_task

            async def wrapped(request, memory_store=None, run_context=None):
                seen["files_at_exec"] = sorted(os.listdir(tmp))
                return await original(request, memory_store=memory_store, run_context=run_context)

            G.execute_task = wrapped
            try:
                result = await h.run_condition(task, make_e0())
            finally:
                G.execute_task = original

            assert seen["files_at_exec"], "manifest must exist before execute_task runs"
            assert any(f.startswith("manifest_") for f in seen["files_at_exec"])
            assert result.manifest_path and os.path.exists(result.manifest_path)
    asyncio.run(_go())


def test_manifest_contains_required_reproducibility_metadata():
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            h = _harness(outdir=tmp)
            task = _pytest_task()
            result = await h.run_condition(task, make_e1(AEMAPolicy()), pair_id="pair_x")

            data = json.load(open(result.manifest_path, encoding="utf-8"))
            required = [
                "run_id", "pair_id", "task_id", "task_hash", "bank_hash", "bank_size",
                "policy_name", "policy_params", "policy_params_hash", "ranker_name",
                "top_k", "similarity_threshold", "provider", "model", "temperature",
                "evaluator_name", "outcome_threshold", "code_git_sha", "code_dirty",
                "platform", "python_version", "memory_write_enabled", "condition_id",
            ]
            for key in required:
                assert key in data, f"manifest missing {key}"
            assert data["pair_id"] == "pair_x"
            assert data["task_hash"] == task.task_hash
            assert data["bank_hash"] == h.bank.bank_hash
            assert data["policy_name"] == "aema"
            assert data["ranker_name"] == "similarity_only"
            assert data["memory_write_enabled"] is False
    asyncio.run(_go())


def test_manifest_cannot_silently_change_after_execution():
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            result = await _harness(outdir=tmp).run_condition(_pytest_task(), make_e0())
            assert result.manifest_unchanged
            assert result.manifest_digest_before == result.manifest_digest_after
    asyncio.run(_go())


def test_manifest_refuses_to_overwrite_an_existing_file():
    with tempfile.TemporaryDirectory() as tmp:
        run = RunContext(bank=_bank(), policy=AEMAPolicy())
        run.manifest.persist(tmp)
        with pytest.raises(FileExistsError):
            run.manifest.persist(tmp)


# ==============================================================================
# Fixed-bank integrity
# ==============================================================================

def test_e1_cannot_mutate_the_fixed_bank():
    async def _go():
        bank = _bank()
        before = bank.bank_hash
        h = _harness(bank=bank)
        for _ in range(3):
            result = await h.run_condition(_pytest_task(), make_e1(AEMAPolicy()))
            assert result.bank_unchanged
            assert result.bank_hash_before == result.bank_hash_after == before
        assert bank.bank_hash == before
        assert len(bank) == 1
    asyncio.run(_go())


def test_pair_execution_leaves_bank_unchanged():
    async def _go():
        bank = _bank()
        before = bank.bank_hash
        obs = await _harness(bank=bank).run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        assert obs.e0.bank_unchanged and obs.e1.bank_unchanged
        assert bank.bank_hash == before
    asyncio.run(_go())


# ==============================================================================
# Isolation -- with runs that ACTIVELY modify their own state
# ==============================================================================

def test_sequential_tasks_and_conditions_do_not_leak_state():
    """
    E0 task A -> E1 task A -> E0 task B -> E1 task B.
    Each E1 run actively drives its own memory toward quarantine; the other runs must
    be completely unaffected.
    """
    async def _go():
        bank = _bank()
        h = _harness(bank=bank)
        task_a, task_b = _pytest_task("task_a"), _pytest_task("task_b")

        obs_a = await h.run_pair(task_a, e1_policy=AEMAPolicy())
        obs_b = await h.run_pair(task_b, e1_policy=AEMAPolicy())

        run_ids = {obs_a.e0.run_id, obs_a.e1.run_id, obs_b.e0.run_id, obs_b.e1.run_id}
        assert len(run_ids) == 4, "every condition execution needs its own run"

        # Each E1 run saw the memory exactly once -- no carry-over of uses.
        for obs in (obs_a, obs_b):
            rec = [r for r in obs.e1.exposures if r["memory_id"] == "m1"][0]
            assert rec["policy_state_before"]["uses"] == 0, "state leaked from a prior run"
            assert rec["policy_state_before"]["extra"]["trust_score"] == 0.75
            assert rec["policy_state_after"]["uses"] == 1

        # E0 runs never exposed a memory at all.
        assert obs_a.e0.memory_ids_exposed == [] and obs_b.e0.memory_ids_exposed == []

        # Exposure logs are disjoint.
        all_ids = [r["run_id"] for o in (obs_a, obs_b) for r in (o.e0.exposures + o.e1.exposures)]
        assert len(set(all_ids)) == 4
        assert bank.bank_hash == _bank().bank_hash
    asyncio.run(_go())


def test_a_run_driven_to_quarantine_does_not_affect_a_parallel_run():
    """Explicit mutation, then verify the neighbour is untouched."""
    bank = _bank()
    busy = RunContext(bank=bank, policy=AEMAPolicy())
    quiet = RunContext(bank=bank, policy=AEMAPolicy())

    for i in range(1, 4):
        busy.trust_state.apply(_obs(idx=i, reward=0.0, binary=0, run_id=busy.run_id))
        busy.exposures.append_record = None  # ensure no shared mutable helper
    assert busy.trust_state.get("m1").uses == 3
    assert busy.trust_state.get("m1").extra["trust_score"] < 0.35

    assert quiet.trust_state.get("m1").uses == 0
    assert quiet.trust_state.get("m1").extra["trust_score"] == 0.75
    assert len(quiet.exposures) == 0
    assert bank.bank_hash == _bank().bank_hash


def test_attempts_and_exposures_do_not_cross_conditions():
    async def _go():
        obs = await _harness().run_pair(_pytest_task(), e1_policy=AEMAPolicy())
        assert obs.e0.n_attempts >= 1 and obs.e1.n_attempts >= 1
        e0_ids = {r["exposure_id"] for r in obs.e0.exposures}
        e1_ids = {r["exposure_id"] for r in obs.e1.exposures}
        assert e0_ids.isdisjoint(e1_ids)
    asyncio.run(_go())


# ==============================================================================
# Reproducibility
# ==============================================================================

def test_same_frozen_task_produces_the_same_evaluator_result():
    async def _go():
        h = _harness()
        task = _pytest_task()
        rewards = []
        for _ in range(3):
            r = await h.run_condition(task, make_e0())
            rewards.append((r.terminal_reward, r.binary_outcome))
        assert len(set(rewards)) == 1, f"evaluator is not reproducible: {rewards}"
    asyncio.run(_go())


def test_replay_still_matches_observed_policy_transitions_through_the_harness():
    async def _go():
        bank = _bank()
        h = _harness(bank=bank)
        task = _pytest_task()

        # Reuse one RunContext across several tasks so a trajectory accumulates.
        run = RunContext(bank=bank, policy=AEMAPolicy(), condition_id="E1")
        from ai_service.graph import execute_task
        from models.task import TaskExecuteRequest

        for _ in range(3):
            await execute_task(
                TaskExecuteRequest(
                    task_input=task.prompt, task_domain=task.domain,
                    memory_enabled=True, memory_mode=MemoryMode.ADAPTIVE,
                    provider="mock", evaluator=task.evaluator,
                    evaluator_config=dict(task.evaluator_config),
                ),
                run_context=run,
            )

        live = run.trust_state.get("m1").to_dict()
        replayed = replay_log(run.exposures, AEMAPolicy(),
                              initial_trust_by_memory={"m1": 0.75})
        assert replayed.final_states["m1"] == live
    asyncio.run(_go())


def test_results_serialise_to_jsonl():
    async def _go():
        with tempfile.TemporaryDirectory() as tmp:
            h = _harness()
            await h.run_pair(_pytest_task(), e1_policy=AEMAPolicy())
            path = os.path.join(tmp, "results.jsonl")
            h.write_results(path)
            lines = open(path, encoding="utf-8").read().splitlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["e0"]["condition_id"] == "E0"
            assert data["e1"]["condition_id"] == "E1"
            assert data["task_specification_identical"] is True
    asyncio.run(_go())
