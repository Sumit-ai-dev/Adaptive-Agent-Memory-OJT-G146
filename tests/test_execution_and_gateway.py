"""
Unit tests for Month 2 Deliverables:
- models/provider.py (ModelProvider, ProviderConfig)
- models/state.py (AgentState)
- ai-service/llm_client.py (UniversalLLMClient, BYOK Gateway)
- ai-service/nodes/execute_node.py (execute_node, bilateral constraint injection)
"""

import asyncio
import json
from models.provider import ModelProvider, ProviderConfig
from models.state import AgentState
from ai_service.llm_client import UniversalLLMClient
from ai_service.nodes.execute_node import execute_node, sync_execute_node


def test_model_provider_enum_and_defaults():
    """Verify all supported providers and their default configurations."""
    assert ModelProvider.GROQ == "groq"
    assert ModelProvider.NVIDIA == "nvidia"
    assert ModelProvider.OLLAMA == "ollama"
    assert ModelProvider.OPENAI == "openai"
    assert ModelProvider.GEMINI == "gemini"
    assert ModelProvider.ANTHROPIC == "anthropic"
    assert ModelProvider.MOCK == "mock"

    groq_cfg = ProviderConfig.default_for(ModelProvider.GROQ)
    assert groq_cfg.provider == ModelProvider.GROQ
    assert "groq" in groq_cfg.base_url

    gemini_cfg = ProviderConfig.default_for(ModelProvider.GEMINI)
    assert gemini_cfg.provider == ModelProvider.GEMINI
    assert "googleapis" in gemini_cfg.base_url

    ollama_cfg = ProviderConfig.default_for(ModelProvider.OLLAMA)
    assert ollama_cfg.provider == ModelProvider.OLLAMA
    assert "11434" in ollama_cfg.base_url

    mock_cfg = ProviderConfig.default_for(ModelProvider.MOCK)
    assert mock_cfg.provider == ModelProvider.MOCK


def test_agent_state_typed_dict():
    """Verify AgentState schema keys and instantiation."""
    state: AgentState = {
        "execution_id": "exec-101",
        "task_id": "task-abc",
        "task_input": "Design an async cache system",
        "task_domain": "code_generation",
        "memory_enabled": True,
        "memory_mode": "adaptive",
        "positive_strategy": "Use LRU eviction policy with O(1) complexity.",
        "negative_pitfall": "Do not block the asyncio event loop with synchronous I/O.",
        "tokens_used": 0,
        "loop_count": 0,
        "status": "retrieved",
    }
    assert state["execution_id"] == "exec-101"
    assert state["positive_strategy"] is not None
    assert state["negative_pitfall"] is not None
    assert state["memory_mode"] == "adaptive"


def test_llm_gateway_deterministic_mock():
    """Verify mock LLM generation produces reproducible answers and counts tokens."""
    async def _run():
        # S10: no implicit provider -- the mock must be declared explicitly.
        client = UniversalLLMClient(
            default_config=ProviderConfig(provider=ModelProvider.MOCK,
                                          model='mock-deterministic-v1')
        )
        messages = [
            {"role": "system", "content": "You are a test agent."},
            {"role": "user", "content": "hotpotqa: who was the prime minister?"},
        ]
        response, tokens = await client.generate(messages)
        assert isinstance(response, str)
        assert len(response) > 10
        assert tokens > 0
        assert "verified" in response.lower() or "citations" in response.lower()

    asyncio.run(_run())


def test_llm_gateway_json_mode():
    """Verify JSON mode returns structured JSON response."""
    async def _run():
        # S10: no implicit provider -- the mock must be declared explicitly.
        client = UniversalLLMClient(
            default_config=ProviderConfig(provider=ModelProvider.MOCK,
                                          model='mock-deterministic-v1')
        )
        messages = [
            {"role": "system", "content": "Extract a structured experience tuple"},
            {"role": "user", "content": "Synthesize learning"},
        ]
        response, tokens = await client.generate(messages, json_mode=True)
        data = json.loads(response)
        assert "trigger_condition" in data
        assert "strategy_lesson" in data
        assert "pitfall" in data
        assert tokens > 0

    asyncio.run(_run())


def test_execute_node_bilateral_constraints():
    """Verify execute_node injects +strategy and -pitfall constraints and updates state."""
    async def _run():
        initial_state: AgentState = {
            "task_input": "Analyze the revenue metrics for Q3",
            "task_domain": "general",
            "provider": "mock",   # S10: explicit provider required
            "positive_strategy": "Cross-check audited financial filings.",
            "negative_pitfall": "Do not cite unaudited press releases.",
            "loop_count": 0,
            "tokens_used": 0,
        }

        result = await execute_node(initial_state)

        assert "final_answer" in result
        assert result["final_answer"] != ""
        assert result["tokens_used"] > 0
        assert result["loop_count"] == 1
        assert result["status"] == "evaluating"
        assert len(result["trajectory"]) == 1

        trace = result["trajectory"][0]
        assert trace["node"] == "execute_node"
        assert trace["metadata"]["hasStrategy"] is True
        assert trace["metadata"]["hasPitfall"] is True

    asyncio.run(_run())


def test_sync_execute_node_wrapper():
    """Verify synchronous wrapper works correctly without requiring explicit asyncio loop."""
    initial_state: AgentState = {
        "provider": "mock",   # S10: explicit provider required
        "task_input": "Summarize policy documents",
        "task_domain": "general",
        "loop_count": 0,
        "tokens_used": 10,
    }

    result = sync_execute_node(initial_state)
    assert result["loop_count"] == 1
    assert result["tokens_used"] > 10
    assert result["status"] == "evaluating"


def test_execute_node_with_byok_provider():
    """Verify execute_node respects BYOK provider override in state."""
    async def _run():
        state: AgentState = {
            "task_input": "Compute deterministic matrix eigenvalues",
            "task_domain": "general",
            "provider": "mock",
            "model": "mock-deterministic-v1",
            "loop_count": 1,
        }

        result = await execute_node(state)
        assert result["loop_count"] == 2
        assert "final_answer" in result

    asyncio.run(_run())
