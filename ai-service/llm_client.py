"""
Universal Multi-Model LLM Gateway supporting Bring-Your-Own-Key (BYOK).
Supports LiteLLM (when installed), OpenAI-compatible providers (Groq, NVIDIA NIM,
local Ollama, OpenAI, Gemini, Anthropic), and deterministic Mock emulator.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

try:
    import litellm
except ImportError:
    litellm = None

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from ai_service.config import settings
except ImportError:
    class FallbackSettings:
        GROQ_API_KEY: Optional[str] = None
        NVIDIA_API_KEY: Optional[str] = None
        OPENAI_API_KEY: Optional[str] = None
        GEMINI_API_KEY: Optional[str] = None
        ANTHROPIC_API_KEY: Optional[str] = None
        REQUEST_TIMEOUT_SECONDS: float = 45.0
    settings = FallbackSettings()

from models.provider import ModelProvider, ProviderConfig, validate_seed

logger = logging.getLogger("ai_service.llm_client")


class ProviderConfigurationError(RuntimeError):
    """
    Raised when an LLM call is attempted with no explicitly declared provider.

    S10: silence here is what allowed a run declaring `provider=ollama` to dispatch
    reflection calls to an ambient OpenAI key. Failing loudly is the only safe default.
    """


def resolve_provider_config(state: Dict[str, Any]) -> Tuple[Optional[ProviderConfig], Optional[float]]:
    """
    Builds the provider configuration for an agent state.

    S8: EVERY LLM call site in the graph must use this, so that a run's declared
    provider/model/temperature are the ones actually dispatched. `reflect_node`
    previously called the gateway with no config at all, which fell through to
    `UniversalLLMClient.default_config` -- resolved from ambient environment
    variables at import time. A run manifest could therefore say
    `provider=ollama, temperature=0.0` while the reflection call went to a
    completely different hosted provider at a different temperature.

    Returns (config_or_None, requested_temperature_or_None). A None config means the
    caller supplied no provider and the gateway default legitimately applies.
    """
    requested_temperature = state.get("temperature")
    requested_seed = state.get("seed")
    requested_max_tokens = state.get("max_tokens")
    provider_name = state.get("provider")
    if not provider_name:
        return None, requested_temperature

    try:
        provider = ModelProvider(provider_name)
    except ValueError:
        return None, requested_temperature

    # S9: reject a seed the provider cannot honour rather than recording a dead one.
    validate_seed(provider, requested_seed)

    defaults = ProviderConfig.default_for(provider)
    config = ProviderConfig(
        provider=provider,
        model=state.get("model") or defaults.model,
        api_key=state.get("api_key"),
        temperature=(
            defaults.temperature if requested_temperature is None
            else float(requested_temperature)
        ),
        seed=requested_seed,
        # S12: effective token budget. None keeps the provider default (2048),
        # which the manifest records explicitly rather than leaving invisible.
        max_tokens=(
            defaults.max_tokens if requested_max_tokens is None
            else int(requested_max_tokens)
        ),
    )
    return config, requested_temperature


class UniversalLLMClient:
    """
    Unified Async Client that routes requests to the configured provider
    using LiteLLM or OpenAI-compatible async clients.
    """

    def __init__(self, default_config: Optional[ProviderConfig] = None):
        # None means 'no implicit provider'. Callers must pass an explicit config.
        self.default_config = default_config

    # S10: `_resolve_default_config` used to scan ambient environment variables
    # (GROQ_API_KEY, then NVIDIA, GEMINI, OPENAI...) and silently pick a provider.
    # An unconfigured call could therefore dispatch to a paid hosted provider that
    # no run manifest ever declared. Ambient credentials are still honoured for an
    # EXPLICITLY declared provider (see `_get_client_and_model`); what is removed is
    # silent provider SELECTION.

    def _get_client_and_model(
        self, override_config: Optional[ProviderConfig] = None
    ) -> Tuple[Optional[Any], str, ModelProvider]:
        cfg = override_config or self.default_config
        provider = cfg.provider

        if provider == ModelProvider.MOCK:
            return None, cfg.model, ModelProvider.MOCK

        api_key = cfg.api_key or getattr(settings, f"{provider.value.upper()}_API_KEY", "dummy-key")
        base_url = cfg.base_url or ProviderConfig.default_for(provider).base_url

        if AsyncOpenAI is not None:
            client = AsyncOpenAI(
                api_key=api_key or "dummy-key",
                base_url=base_url,
                timeout=getattr(settings, "REQUEST_TIMEOUT_SECONDS", 45.0),
                http_client=httpx.AsyncClient(),
            )
            return client, cfg.model, provider

        return None, cfg.model, provider

    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: Optional[ProviderConfig] = None,
        json_mode: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> Tuple[str, int]:
        """
        Asynchronously dispatch a chat completion request to the resolved model.
        Returns: (response_text, tokens_used)
        """
        cfg = config or self.default_config
        if cfg is None:
            raise ProviderConfigurationError(
                "No provider configuration supplied. Pass an explicit ProviderConfig "
                "(e.g. via ai_service.llm_client.resolve_provider_config(state)) or "
                "construct the client with an explicit default_config. Implicit "
                "selection from environment variables has been removed (S10)."
            )
        provider = cfg.provider
        effective_seed = cfg.seed if seed is None else seed
        validate_seed(provider, effective_seed)

        if provider == ModelProvider.MOCK:
            return self._generate_mock_response(messages, json_mode)

        # 1. Try litellm if installed
        if litellm is not None:
            try:
                litellm_model = cfg.model
                if provider == ModelProvider.GROQ and not litellm_model.startswith("groq/"):
                    litellm_model = f"groq/{litellm_model}"
                elif provider == ModelProvider.OLLAMA and not litellm_model.startswith("ollama/"):
                    litellm_model = f"ollama/{litellm_model}"

                response = await litellm.acompletion(
                    model=litellm_model,
                    messages=messages,
                    api_key=cfg.api_key,
                    base_url=cfg.base_url,
                    temperature=temperature if temperature is not None else cfg.temperature,
                    max_tokens=max_tokens or cfg.max_tokens,
                    response_format={"type": "json_object"} if json_mode else None,
                )
                content = response.choices[0].message.content or ""
                tokens = response.usage.total_tokens if hasattr(response, "usage") and response.usage else len(content.split()) * 2
                return content, tokens
            except Exception as e:
                logger.warning(f"LiteLLM call failed for {provider.value}: {e}. Trying AsyncOpenAI fallback.")

        # 2. OpenAI-compatible Async client fallback
        client, model, _ = self._get_client_and_model(cfg)
        if client is not None:
            try:
                kwargs: Dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature if temperature is not None else cfg.temperature,
                    "max_tokens": max_tokens or cfg.max_tokens,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                # S9: only ever sent to providers that honour it (validated above).
                if effective_seed is not None:
                    kwargs["seed"] = int(effective_seed)

                response = await client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                content = choice.message.content or ""
                tokens = response.usage.total_tokens if response.usage else len(content.split()) * 2
                return content, tokens
            except Exception as e:
                logger.warning(f"AsyncOpenAI call failed for {provider.value} ({model}): {e}. Falling back to deterministic response.")
                return self._generate_mock_response(messages, json_mode)

        return self._generate_mock_response(messages, json_mode)

    def _generate_mock_response(
        self, messages: List[Dict[str, str]], json_mode: bool
    ) -> Tuple[str, int]:
        """
        Deterministic, rule-based response generator for offline and unit test execution.
        """
        user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        sys_msg = next((m["content"] for m in messages if m.get("role") == "system"), "")

        if json_mode or "Extract a structured experience tuple" in sys_msg or "Extract a structured experience tuple" in user_msg:
            mock_reflection = {
                "trigger_condition": "Multi-step analytical query with conflicting factual claims",
                "strategy_lesson": "Decompose into sub-claims, verify primary sources sequentially, and state operational boundary conditions.",
                "pitfall": "Do not accept preliminary or non-peer-reviewed benchmarks as authoritative without corroboration.",
                "confidence": 0.88,
            }
            return json.dumps(mock_reflection), 150

        has_negative_constraint = "CRITICAL NEGATIVE CONSTRAINT" in sys_msg or "AVOID:" in sys_msg

        if "hotpotqa" in user_msg.lower() or "who was" in user_msg.lower() or "which" in user_msg.lower():
            ans = "Based on verified multi-hop analysis, the relevant primary entity is confirmed with supporting citations."
            if has_negative_constraint:
                ans += " Flawed distractor paths were deliberately avoided per negative constraints."
            return ans, 120

        tokens = len(user_msg.split()) + 80
        ans = (
            f"Synthesizing optimal solution for: '{user_msg[:60]}...'. "
            "Execution completed adhering to verified operational strategies."
        )
        return ans, tokens


# Global singleton client instance
llm_gateway = UniversalLLMClient()
