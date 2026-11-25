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
    assert groq_cfg.model == "openai/gpt-oss-120b"
    assert "groq" in groq_cfg.base_url

    gemini_cfg = ProviderConfig.default_for(ModelProvider.GEMINI)
    assert gemini_cfg.provider == ModelProvider.GEMINI
    assert gemini_cfg.model == "gemini-2.5-flash"
    assert "googleapis" in gemini_cfg.base_url

    # Verify that directly initializing ProviderConfig per provider gets correct default models
    assert ProviderConfig(provider=ModelProvider.GROQ).model == "openai/gpt-oss-120b"
    assert ProviderConfig(provider=ModelProvider.GEMINI).model == "gemini-2.5-flash"
    assert ProviderConfig(provider=ModelProvider.OLLAMA).model == "llama3.2:3b"

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


def test_gemini_byok_request_and_error_formatting():
    """Verify BYOK Gemini key alignment and unified HTTP error formatting."""
    client = UniversalLLMClient()
    dummy_key = "aaa-000"
    cfg = ProviderConfig(provider=ModelProvider.GEMINI, model="gemini-2.5-flash-lite", api_key=dummy_key)
    model, headers, payload = client._build_gemini_request(
        messages=[{"role": "system", "content": "Be concise."}, {"role": "user", "content": "Hi"}],
        cfg=cfg,
        temperature=0.2,
    )
    assert model == "gemini-2.5-flash-lite"
    assert headers["x-goog-api-key"] == dummy_key
    assert payload["systemInstruction"]["parts"][0]["text"] == "Be concise."

    err_400 = client._format_gemini_http_error(400, '{"error":{"message":"API key not valid. Please pass a valid API key."}}')
    assert "API key not valid" in err_400
    err_429 = client._format_gemini_http_error(429, '{"error":{"message":"Quota exceeded"}}')
    assert "quota exceeded" in err_429.lower()

    # High demand / policy block diagnostics
    err_503 = client._format_gemini_http_error(503, '{"error":{"message":"High demand"}}', "gemini-3.8-flash")
    assert "gemini-3.5-flash-lite" in err_503
    assert "high demand" in err_503.lower()

    err_403_policy = client._format_gemini_http_error(403, 'Request not allowed by policy', "gemini-3.8-flash")
    assert "gemini-3.5-flash-lite" in err_403_policy

    err_compat_timeout = client._format_openai_compat_error(ModelProvider.GEMINI, "gemini-3.8-flash", "Request timed out")
    assert "gemini-3.5-flash-lite" in err_compat_timeout
    assert "high demand" in err_compat_timeout.lower()

    err_compat_policy = client._format_openai_compat_error(
        ModelProvider.GEMINI,
        "gemini-3.8-flash",
        "Request to POST /v1beta/chat/completions on generativelanguage.googleapis.com not allowed by policy",
    )
    assert "gemini-3.5-flash-lite" in err_compat_policy


def test_anthropic_byok_request_and_error_formatting():
    """Verify Anthropic BYOK request builder, json_mode instruction, and HTTP error formatting."""
    client = UniversalLLMClient()
    dummy_key = "bbb-000"
    cfg = ProviderConfig(provider=ModelProvider.ANTHROPIC, model="claude-sonnet-5-5", api_key=dummy_key)
    headers, payload = client._build_anthropic_request(
        messages=[{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Hello"}],
        cfg=cfg,
        json_mode=True,
        temperature=0.3,
    )
    assert headers["x-api-key"] == dummy_key
    assert headers["anthropic-version"] == "2023-06-01"
    assert payload["model"] == "claude-sonnet-5-5"
    assert "Be brief." in payload["system"]
    assert "valid JSON object" in payload["system"]
    assert payload["messages"] == [{"role": "user", "content": "Hello"}]

    err_401 = client._format_anthropic_http_error(401, '{"error":{"type":"authentication_error","message":"invalid x-api-key"}}')
    assert "invalid anthropic api key" in err_401.lower()
    err_429 = client._format_anthropic_http_error(429, '{"error":{"message":"rate limit exceeded"}}')
    assert "rate limit" in err_429.lower()


def test_byok_route_forwards_provider_model_and_key_end_to_end():
    """Verify /api/agent/execute forwards camelCase provider, model, and apiKey into llm_gateway."""
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from backend.main import app
    from ai_service.llm_client import llm_gateway

    test_client = TestClient(app)
    cases = [
        ("gemini", "gemini-3.8-flash", "aaa-111"),
        ("openai", "gpt-6.2-sol", "bbb-111"),
        ("anthropic", "claude-sonnet-5-5", "ccc-111"),
    ]

    for expected_provider, expected_model, expected_key in cases:
        captured = []

        async def _fake_generate(messages, config=None, json_mode=False, temperature=None, max_tokens=None, seed=None):
            captured.append(config)
            if json_mode:
                return json.dumps({
                    "trigger_condition": "General query",
                    "strategy_lesson": "Verify outputs",
                    "pitfall": "Avoid guessing",
                    "confidence": 0.85,
                }), 40
            return "Verified response from route.", 25

        with patch.object(llm_gateway, "generate", side_effect=_fake_generate):
            res = test_client.post(
                "/api/agent/execute",
                json={
                    "taskInput": "Say hello cleanly",
                    "taskDomain": "general",
                    "memoryEnabled": False,
                    "provider": expected_provider,
                    "model": expected_model,
                    "apiKey": expected_key,
                },
            )
            assert res.status_code == 200, res.text
            assert len(captured) >= 1
            for cfg in captured:
                assert cfg.provider.value == expected_provider
                assert cfg.model == expected_model
                assert cfg.api_key == expected_key


def test_reflect_node_skips_on_provider_error():
    """Verify reflect_node short-circuits instead of making a second failing LLM call."""
    from unittest.mock import AsyncMock, patch
    from ai_service.nodes.reflect_node import reflect_node
    from ai_service.llm_client import llm_gateway

    async def _run():
        state: AgentState = {
            "task_input": "Explain quantum tunneling",
            "task_domain": "general",
            "final_answer": "Execution encountered a model provider error: 400 invalid key",
            "outcome_score": 0.5,
            "evaluator_details": {"error": "provider_error"},
            "provider": "gemini",
            "api_key": "AIzaBadKey",
        }
        with patch.object(llm_gateway, "generate", new=AsyncMock(side_effect=AssertionError("Should not call LLM"))) as mock_gen:
            res = await reflect_node(state)
            mock_gen.assert_not_called()
            assert res["candidate_experience"] is None
            assert res["new_experience_created"] is False

    asyncio.run(_run())
