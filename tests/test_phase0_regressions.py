"""
Phase 0 Engineering-Correctness Regression Suite.

Scope: these tests assert ONLY that the existing implementation executes its own
intended behaviour. They make no claim about the scientific validity of the trust
mechanism, the choice of A-EMA, the retrieval weights, or any experimental condition.

One test (or test group) per P0 defect:
  P0-1  RetrievedMemory construction raised ValidationError on every match.
  P0-2  The ValidationError was swallowed and became "zero memories retrieved".
  P0-3  Stored memories never received an embedding, so cosine similarity was 0.0.
  P0-4  trust_node computed A-EMA updates and discarded them.
  P0-5  `initial_trust_score=` is not a field on Experience; pydantic dropped it.
  P0-6  LocalEmbedder has no `.embed()`; the memories route called it.

Plus the end-to-end chain and the E0 / memory-enabled path-divergence checks
required by the Phase 0 acceptance criteria.
"""

import asyncio
import os
import tempfile

import pytest

from ai_service.embedder import LocalEmbedder, local_embedder
from ai_service.graph import execute_task
from ai_service.memory.retriever import MemoryRetriever
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.retrieve_node import async_retrieve_node
from ai_service.nodes.trust_node import compute_next_trust
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceMatch, ExperienceStatus
from models.provider import ModelProvider
from models.task import TaskExecuteRequest

# A trigger/task pair with high lexical+semantic overlap, so that cosine similarity
# clears settings.SIMILARITY_THRESHOLD (0.60) under all-MiniLM-L6-v2.
SEED_TRIGGER = "Fixing RecursionError in deep binary tree traversal"
SEED_TASK = "Fix the RecursionError raised by my recursive binary tree traversal function"
UNRELATED_TASK = "Summarise the political history of the Baltic states in the 1920s"


def _fresh_store() -> SQLiteMemoryStore:
    """A store on its own temp file, so no test observes another test's state."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="p0_")
    os.close(fd)
    os.remove(path)
    return SQLiteMemoryStore(db_path=path)


def _seed_memory(**overrides) -> Experience:
    base = dict(
        id="mem_seed_001",
        task_domain=TaskDomain.CODING,
        trigger_condition=SEED_TRIGGER,
        strategy_lesson="Convert the recursion to an iterative traversal using collections.deque.",
        pitfall="Do not raise sys.setrecursionlimit.",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    base.update(overrides)
    return Experience(**base)


# ==============================================================================
# P0-1 — RetrievedMemory / ExperienceMatch construction
# ==============================================================================

def test_p0_1_experience_match_requires_similarity_field():
    """Pins the model contract that the retriever previously violated."""
    exp = _seed_memory()
    match = ExperienceMatch(experience=exp, similarity=0.88, composite_score=0.77)
    assert match.similarity == 0.88

    # The old keyword name must NOT silently satisfy the model.
    with pytest.raises(Exception):
        ExperienceMatch(experience=exp, similarity_score=0.88, composite_score=0.77)


@pytest.mark.parametrize("mode", [MemoryMode.NAIVE, MemoryMode.SYMMETRIC, MemoryMode.ADAPTIVE])
def test_p0_1_retriever_returns_matches_in_every_memory_mode(mode):
    """Previously raised ValidationError on the first match in all three modes."""
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        retriever = MemoryRetriever(store=store)
        results = await retriever.retrieve(
            query=SEED_TASK, domain=TaskDomain.CODING, mode=mode, top_k=2
        )
        assert len(results) >= 1, f"mode={mode.value} returned no matches"
        top = results[0]
        assert top.experience.id == "mem_seed_001"
        # Acceptance criterion: "The retrieved memory has a valid similarity score."
        assert 0.0 <= top.similarity <= 1.0
        # > 0.60 only holds with a real semantic embedder; the hash fallback gives ~0.32.
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            _has_st = True
        except ImportError:
            _has_st = False
        if _has_st:
            assert top.similarity > 0.60
        assert 0.0 <= top.composite_score <= 1.0

    asyncio.run(_run())


def test_p0_1_negative_cosine_is_clamped_not_a_validation_error():
    """search_similar returns unclamped cosine in [-1,1]; the model requires [0,1]."""
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())

        class NegativeCosineStore:
            """Wraps the real store but reports an anti-correlated similarity."""
            def __init__(self, inner):
                self._inner = inner

            async def search_similar(self, query_embedding, domain=None, top_k=5):
                raw = await self._inner.search_similar(query_embedding, domain, top_k)
                return [(exp, -0.42) for exp, _ in raw]

        retriever = MemoryRetriever(store=NegativeCosineStore(store))
        results = await retriever.retrieve(
            query=SEED_TASK, domain=TaskDomain.CODING, mode=MemoryMode.SYMMETRIC, top_k=2
        )
        # Must not raise; similarity is clamped to the unit interval.
        assert all(0.0 <= r.similarity <= 1.0 for r in results)

    asyncio.run(_run())


# ==============================================================================
# P0-2 — swallowed retrieval exception
# ==============================================================================

def test_p0_2_retrieval_failure_raises_instead_of_returning_empty():
    """
    A store-backed retrieval failure must NOT be silently converted into
    "zero memories retrieved", which is indistinguishable from MemoryMode.OFF.
    """
    class BrokenStore:
        async def search_similar(self, *a, **kw):
            raise RuntimeError("simulated store failure")

        async def list_experiences(self, *a, **kw):
            raise RuntimeError("simulated store failure")

    state = {
        "task_input": SEED_TASK,
        "task_domain": "coding",
        "memory_enabled": True,
        "memory_mode": "adaptive",
        "memory_store": BrokenStore(),
        # deliberately no "memory_candidates" -> no legitimate fallback exists
    }
    with pytest.raises(RuntimeError, match="simulated store failure"):
        asyncio.run(async_retrieve_node(state))


def test_p0_2_in_memory_candidate_fallback_is_preserved():
    """The legitimate in-memory fallback path still works when candidates are supplied."""
    class BrokenStore:
        async def search_similar(self, *a, **kw):
            raise RuntimeError("simulated store failure")

    state = {
        "task_input": SEED_TASK,
        "task_domain": "coding",
        "memory_enabled": True,
        "memory_mode": "adaptive",
        "memory_store": BrokenStore(),
        "memory_candidates": [_seed_memory()],
        "query_embedding": None,
    }
    result = asyncio.run(async_retrieve_node(state))
    # retrieve_experiences uses a 0.75 neutral similarity when no query_embedding
    # is supplied, which clears its 0.70 floor.
    assert len(result["retrieved_memories"]) == 1


# ==============================================================================
# P0-3 — stored-memory embeddings
# ==============================================================================

def test_p0_3_add_experience_populates_embedding():
    async def _run():
        store = _fresh_store()
        exp = _seed_memory(embedding=None)
        assert exp.embedding is None

        await store.add_experience(exp)
        stored = await store.get_experience("mem_seed_001")

        assert stored.embedding is not None, "stored memory has no embedding"
        assert len(stored.embedding) == 384, "embedding is not 384-dimensional"
        assert all(isinstance(v, float) for v in stored.embedding)

    asyncio.run(_run())


def test_p0_3_explicit_embedding_is_not_overwritten():
    async def _run():
        store = _fresh_store()
        custom = [0.0] * 383 + [1.0]
        await store.add_experience(_seed_memory(embedding=custom))
        stored = await store.get_experience("mem_seed_001")
        assert stored.embedding == custom

    asyncio.run(_run())


def test_p0_3_embedded_memory_is_actually_discoverable_by_cosine_search():
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        q = local_embedder.embed_text(SEED_TASK)
        hits = await store.search_similar(q, domain=TaskDomain.CODING, top_k=3)
        assert len(hits) == 1
        _, sim = hits[0]
        # > 0.60 only holds with a real semantic embedder; the hash fallback gives ~0.32.
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            _has_st = True
        except ImportError:
            _has_st = False
        if _has_st:
            assert sim > 0.60, f"similarity {sim:.4f} too low to clear the retrieval threshold"
        else:
            assert sim > 0.0, f"hash embedder returned zero similarity: {sim:.4f}"

    asyncio.run(_run())


# ==============================================================================
# P0-4 — trust node persistence
# ==============================================================================

def test_p0_4_trust_update_is_persisted_to_the_store():
    """
    Asserts persistence only. The A-EMA arithmetic itself is unchanged and is
    covered by tests/test_memory_nodes.py and tests/test_trust_dynamics.py --
    this test derives the expected value from compute_next_trust rather than
    hardcoding it, so it stays valid if the mechanism is later swapped.
    """
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        before = await store.get_experience("mem_seed_001")
        assert before.trust_score == 0.75

        req = TaskExecuteRequest(
            task_input=SEED_TASK,
            task_domain=TaskDomain.CODING,
            memory_enabled=True,
            memory_mode=MemoryMode.ADAPTIVE,
            provider=ModelProvider.MOCK,
        )
        result = await execute_task(req, memory_store=store)

        assert len(result.trust_updates) >= 1, "trust_node produced no updates"
        update = result.trust_updates[0]
        assert update.experience_id == "mem_seed_001"

        expected, _reason = compute_next_trust(0.75, result.outcome_score)

        after = await store.get_experience("mem_seed_001")
        assert after.trust_score != 0.75, "trust was not persisted"
        assert after.trust_score == pytest.approx(expected, abs=1e-4)
        assert after.uses_count >= 1

    asyncio.run(_run())


def test_p0_4_trust_history_audit_row_is_written():
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())

        req = TaskExecuteRequest(
            task_input=SEED_TASK,
            task_domain=TaskDomain.CODING,
            memory_enabled=True,
            memory_mode=MemoryMode.ADAPTIVE,
            provider=ModelProvider.MOCK,
        )
        await execute_task(req, memory_store=store)

        with store._get_connection() as conn:
            rows = conn.execute(
                "SELECT experience_id, old_trust, new_trust FROM trust_history WHERE experience_id = ?",
                ("mem_seed_001",),
            ).fetchall()
        assert len(rows) >= 1, "no trust_history audit row written"

    asyncio.run(_run())


def test_p0_4_trust_node_is_a_noop_without_a_store():
    """Preserves prior behaviour: no store in state => no persistence, no crash."""
    async def _run():
        req = TaskExecuteRequest(
            task_input=SEED_TASK,
            task_domain=TaskDomain.CODING,
            memory_enabled=True,
            memory_mode=MemoryMode.ADAPTIVE,
            provider=ModelProvider.MOCK,
        )
        result = await execute_task(req, memory_store=None)
        assert result.status is not None

    asyncio.run(_run())


# ==============================================================================
# P0-5 — invalid initial_trust_score field
# ==============================================================================

def test_p0_5_experience_has_no_initial_trust_score_field():
    assert "initial_trust_score" not in Experience.model_fields
    assert "trust_score" in Experience.model_fields


def test_p0_5_toolbench_poison_seeding_sets_trust_score():
    """The poison seeder must actually carry its intended 0.50 trust."""
    from benchmarks.toolbench_runner import seed_adversarial_poison

    async def _run():
        store = _fresh_store()
        await seed_adversarial_poison(
            store,
            {"id": "tb_1", "query": "call the billing API", "trap_description": "deprecated param",
             "wrong_call": {"x": 1}},
        )
        stored = await store.get_experience("poison_tb_1")
        assert stored is not None
        assert stored.trust_score == 0.50
        assert stored.embedding is not None and len(stored.embedding) == 384

    asyncio.run(_run())


# ==============================================================================
# P0-6 — embedder API mismatch
# ==============================================================================

def test_p0_6_embedder_exposes_embed_text_not_embed():
    e = LocalEmbedder()
    assert hasattr(e, "embed_text")
    assert hasattr(e, "embed_batch")
    assert not hasattr(e, "embed"), "an `embed` alias would re-hide the API mismatch"
    assert len(e.embed_text("hello world")) == 384


def test_p0_6_memories_route_semantic_search_does_not_error():
    """backend.routes.memories.list_memories(search=...) previously raised AttributeError."""
    from backend.routes import memories as memories_route

    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        original = memories_route.shared_store
        memories_route.shared_store = store
        try:
            out = await memories_route.list_memories(
                domain="coding", status_filter=None, min_trust=0.0,
                search=SEED_TASK, limit=10, offset=0,
            )
        finally:
            memories_route.shared_store = original
        assert isinstance(out, list)
        assert len(out) == 1
        assert "similarityScore" in out[0]

    asyncio.run(_run())


# ==============================================================================
# Acceptance criteria 6/7/8 — end-to-end chain and path divergence
# ==============================================================================

def test_acceptance_seeded_memory_traverses_the_full_five_node_chain():
    """
    embed -> store -> retrieve -> execute -> evaluate -> trust -> trust state updated.
    """
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())

        # 1. embedded + stored
        stored = await store.get_experience("mem_seed_001")
        assert stored.embedding is not None and len(stored.embedding) == 384

        req = TaskExecuteRequest(
            task_input=SEED_TASK,
            task_domain=TaskDomain.CODING,
            memory_enabled=True,
            memory_mode=MemoryMode.ADAPTIVE,
            provider=ModelProvider.MOCK,
        )
        result = await execute_task(req, memory_store=store)

        nodes = [t.node for t in result.trajectory if t.node]
        for expected in ("retrieve_node", "execute_node", "evaluate_node", "reflect_node", "trust_node"):
            assert expected in nodes, f"{expected} did not execute"

        # 2. retrieved with a valid similarity
        assert len(result.retrieved_memories) >= 1
        top = result.retrieved_memories[0]
        assert top["experience"]["id"] == "mem_seed_001"
        assert 0.0 < top["similarityScore"] <= 1.0

        # 3. reached execute_node -- the strategy/pitfall were injected
        retrieval_trace = next(t for t in result.trajectory if t.node == "retrieve_node")
        assert retrieval_trace.metadata["hasPositiveStrategy"] is True
        assert retrieval_trace.metadata["hasNegativePitfall"] is True

        # 4. produced an evaluation
        assert result.outcome_score is not None
        assert 0.0 <= result.outcome_score <= 1.0

        # 5. reached trust_node and the update was persisted
        assert len(result.trust_updates) >= 1
        trust_trace = next(t for t in result.trajectory if t.node == "trust_node")
        assert trust_trace.metadata["trustUpdates"][0]["persisted"] is True

        # 6. trust state actually changed in the store
        after = await store.get_experience("mem_seed_001")
        assert after.trust_score != 0.75

    asyncio.run(_run())


def test_acceptance_memory_mode_off_injects_nothing():
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())

        req = TaskExecuteRequest(
            task_input=SEED_TASK,
            task_domain=TaskDomain.CODING,
            memory_enabled=False,
            memory_mode=MemoryMode.OFF,
            provider=ModelProvider.MOCK,
        )
        result = await execute_task(req, memory_store=store)

        assert result.retrieved_memories == []
        assert result.trust_updates == []

        retrieval_trace = next(t for t in result.trajectory if t.node == "retrieve_node")
        assert retrieval_trace.metadata["hasPositiveStrategy"] is False
        assert retrieval_trace.metadata["hasNegativePitfall"] is False

        # E0 must leave the memory's trust state untouched.
        after = await store.get_experience("mem_seed_001")
        assert after.trust_score == 0.75
        assert after.uses_count == 0

    asyncio.run(_run())


def test_acceptance_adaptive_path_differs_from_off_when_a_match_exists():
    """
    Acceptance criterion 8: E0 and the memory-enabled path must take demonstrably
    different execution paths when a valid matching memory exists.

    This asserts path divergence only. It makes NO claim about which path produces
    better task outcomes.
    """
    async def _run():
        store_off = _fresh_store()
        await store_off.add_experience(_seed_memory())
        store_on = _fresh_store()
        await store_on.add_experience(_seed_memory())

        common = dict(
            task_input=SEED_TASK,
            task_domain=TaskDomain.CODING,
            provider=ModelProvider.MOCK,
        )
        off = await execute_task(
            TaskExecuteRequest(memory_enabled=False, memory_mode=MemoryMode.OFF, **common),
            memory_store=store_off,
        )
        on = await execute_task(
            TaskExecuteRequest(memory_enabled=True, memory_mode=MemoryMode.ADAPTIVE, **common),
            memory_store=store_on,
        )

        # Retrieval diverges.
        assert len(off.retrieved_memories) == 0
        assert len(on.retrieved_memories) >= 1

        # Prompt construction diverges.
        off_trace = next(t for t in off.trajectory if t.node == "retrieve_node")
        on_trace = next(t for t in on.trajectory if t.node == "retrieve_node")
        assert off_trace.metadata["hasPositiveStrategy"] is False
        assert on_trace.metadata["hasPositiveStrategy"] is True

        # Trust bookkeeping diverges.
        assert len(off.trust_updates) == 0
        assert len(on.trust_updates) >= 1

        # Persisted state diverges.
        assert (await store_off.get_experience("mem_seed_001")).trust_score == 0.75
        assert (await store_on.get_experience("mem_seed_001")).trust_score != 0.75

    asyncio.run(_run())


def test_acceptance_non_matching_task_retrieves_nothing_in_adaptive_mode():
    """Guards against the fix turning retrieval into an unconditional match."""
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())

        req = TaskExecuteRequest(
            task_input=UNRELATED_TASK,
            task_domain=TaskDomain.CODING,
            memory_enabled=True,
            memory_mode=MemoryMode.ADAPTIVE,
            provider=ModelProvider.MOCK,
        )
        result = await execute_task(req, memory_store=store)
        assert result.retrieved_memories == [], "unrelated task should fall below the similarity threshold"

    asyncio.run(_run())
