"""
Unit and Integration Tests for Dynamic Context Compaction & Runtime Token/Cost Budgeting (Issue #38).
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)
"""

import pytest
from ai_service.config import settings
from ai_service.context.compactor import (
    compact_memory_context,
    compact_retrieved_memories_list,
)
from ai_service.context.token_budget import (
    calculate_token_cost,
    count_tokens,
    truncate_text_to_tokens,
)
from ai_service.graph import execute_task, should_loop_or_finish
from ai_service.nodes.execute_node import execute_node
from ai_service.nodes.retrieve_node import async_retrieve_node
from models.domain import MemoryMode, TaskDomain
from models.task import TaskExecuteRequest


def test_count_tokens_deterministic():
    """Validates deterministic BPE-approximating token count with symbols and code."""
    text = "def solution(x: int) -> bool:\n    return {'status': 'active', 'score': 0.95}"
    tokens = count_tokens(text)
    assert tokens > 10
    assert count_tokens("") == 0
    assert count_tokens(text) == count_tokens(text)


def test_truncate_text_to_tokens():
    """Ensures token truncation strictly respects the ceiling constraint."""
    long_text = " ".join([f"operational_strategy_step_{i}" for i in range(500)])
    max_budget = 50
    truncated, token_count = truncate_text_to_tokens(long_text, max_tokens=max_budget)

    assert token_count <= max_budget
    assert count_tokens(truncated) <= max_budget
    assert "[...]" in truncated


def test_compact_memory_context_under_budget():
    """Memories under the 800 token limit are unmodified."""
    strat = "Always validate preconditions before array indexing."
    pit = "Never catch generic BaseException without logging."

    res = compact_memory_context(strat, pit, max_tokens=800)
    assert res.was_compacted is False
    assert res.positive_strategy == strat
    assert res.negative_pitfall == pit
    assert res.compacted_tokens <= 800


def test_compact_memory_context_oversized_strategy():
    """When positive strategy exceeds budget while pitfall is small, pitfall is preserved and strategy is cut."""
    huge_strat = " ".join(["always_verify_invariant" for _ in range(900)])
    short_pit = "Do not allow buffer underflow."

    res = compact_memory_context(huge_strat, short_pit, max_tokens=800)
    assert res.was_compacted is True
    assert res.compacted_tokens <= 800
    assert res.negative_pitfall == short_pit
    assert "[...]" in res.positive_strategy


def test_compact_memory_context_both_oversized():
    """When both strategy and pitfall are oversized, each receives equal fair quota (400 tokens)."""
    huge_strat = " ".join(["execute_carefully_step" for _ in range(600)])
    huge_pit = " ".join(["avoid_catastrophic_failure" for _ in range(600)])

    res = compact_memory_context(huge_strat, huge_pit, max_tokens=800)
    assert res.was_compacted is True
    assert res.compacted_tokens <= 800
    assert res.strategy_tokens <= 400
    assert res.pitfall_tokens <= 400
    assert "[...]" in res.positive_strategy
    assert "[...]" in res.negative_pitfall


def test_compact_retrieved_memories_list():
    """Ordered candidate list is truncated and compacted so cumulative tokens <= 800."""
    memories = [
        {
            "experience": {
                "strategyLesson": " ".join(["strat_one"] * 300),
                "pitfall": " ".join(["pit_one"] * 200),
            },
            "compositeScore": 0.95,
        },
        {
            "experience": {
                "strategyLesson": " ".join(["strat_two"] * 300),
                "pitfall": " ".join(["pit_two"] * 200),
            },
            "compositeScore": 0.85,
        },
    ]

    retained, total_tokens, was_compacted = compact_retrieved_memories_list(memories, max_tokens=800)
    assert was_compacted is True
    assert total_tokens <= 800
    assert len(retained) >= 1


def test_calculate_token_cost_models():
    """Computes accurate USD pricing across providers."""
    # Mock / Local
    assert calculate_token_cost("mock", "mock", 1000, 500) == 0.0
    assert calculate_token_cost("ollama", "llama3", 1000, 500) == 0.0

    # Groq openai/gpt-oss-120b: $0.59 prompt, $0.79 completion per 1M
    cost_groq = calculate_token_cost("groq", "openai/gpt-oss-120b", 1_000_000, 1_000_000)
    assert cost_groq == pytest.approx(1.38, rel=1e-3)

    # OpenAI gpt-4o: $2.50 prompt, $10.00 completion per 1M
    cost_openai = calculate_token_cost("openai", "gpt-4o", 10_000, 2_000)
    # (10k / 1M)*2.50 + (2k / 1M)*10.00 = 0.025 + 0.020 = 0.045
    assert cost_openai == pytest.approx(0.045, rel=1e-3)


@pytest.mark.asyncio
async def test_execute_node_prompt_ceiling_circuit_breaker():
    """Prompt exceeding MAX_PROMPT_TOKENS (4096) trips the circuit breaker gracefully."""
    gigantic_prompt = "word " * 5000
    state = {
        "task_input": gigantic_prompt,
        "messages": [],
        "provider": "mock",
        "model": "mock",
        "tokens_used": 0,
        "total_cost_usd": 0.0,
    }

    result = await execute_node(state)
    assert result["status"] == "failed"
    assert result["budget_exceeded"] is True
    assert "Prompt context exceeded maximum allowable limit" in result["final_answer"]
    assert result["prompt_tokens"] > settings.MAX_PROMPT_TOKENS


@pytest.mark.asyncio
async def test_execute_node_cost_ceiling_circuit_breaker():
    """Cumulative task cost exceeding MAX_TASK_COST_USD ($0.05) halts execution immediately."""
    state = {
        "task_input": "Calculate sum of numbers",
        "messages": [],
        "provider": "mock",
        "model": "mock",
        "tokens_used": 500,
        "total_cost_usd": 0.06,  # exceeds $0.05 limit
    }

    result = await execute_node(state)
    assert result["status"] == "failed"
    assert result["budget_exceeded"] is True
    assert "Cumulative task expenditure exceeded budget" in result["final_answer"]


def test_should_loop_or_finish_respects_circuit_breaker():
    """Cyclical feedback edge aborts if budget was exceeded."""
    state_breached = {
        "outcome_score": 0.50,
        "loop_count": 1,
        "max_loops": 3,
        "budget_exceeded": True,
    }
    assert should_loop_or_finish(state_breached) == "__end__"

    state_cost_limit = {
        "outcome_score": 0.50,
        "loop_count": 1,
        "max_loops": 3,
        "total_cost_usd": 0.051,
    }
    assert should_loop_or_finish(state_cost_limit) == "__end__"


@pytest.mark.asyncio
async def test_end_to_end_task_execution_metadata():
    """End-to-end task execution returns complete token breakdown and USD cost in execution_metadata."""
    req = TaskExecuteRequest(
        task_input="Write a python function to compute factorial of n",
        task_domain=TaskDomain.CODING,
        memory_mode=MemoryMode.OFF,
        provider="mock",
        model="mock",
    )

    execution = await execute_task(req, memory_store=None)
    assert execution.prompt_tokens > 0
    assert execution.completion_tokens > 0
    assert execution.total_cost_usd >= 0.0
    assert execution.budget_exceeded is False

    meta = execution.execution_metadata
    assert meta is not None
    assert meta.prompt_tokens > 0
    assert meta.completion_tokens > 0
    assert meta.total_cost_usd >= 0.0
    assert meta.tokens_used > 0
