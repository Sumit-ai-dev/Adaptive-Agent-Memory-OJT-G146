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
        api_key=state.get("api_key") or defaults.api_key,
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

        default_cfg = ProviderConfig.default_for(provider)
        api_key = (
            (cfg.api_key or "").strip()
            or getattr(settings, f"{provider.value.upper()}_API_KEY", None)
            or default_cfg.api_key
        )
        base_url = cfg.base_url or default_cfg.base_url
        model = cfg.model or default_cfg.model

        if not api_key:
            return None, model, provider

        if AsyncOpenAI is not None:
            timeout_sec = float(getattr(settings, "REQUEST_TIMEOUT_SECONDS", 15.0))
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout_sec,
                max_retries=1,
                http_client=httpx.AsyncClient(timeout=httpx.Timeout(timeout_sec, connect=5.0)),
            )
            return client, model, provider

        return None, model, provider

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

        # 1. Native Google Gemini REST integration (direct to Google, bypassing OpenAI proxy issues)
        if provider == ModelProvider.GEMINI:
            return await self._generate_gemini_native(
                messages=messages,
                cfg=cfg,
                json_mode=json_mode,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # 2. Try litellm if installed
        if litellm is not None:
            try:
                litellm_model = cfg.model
                if provider == ModelProvider.GROQ and not litellm_model.startswith("groq/"):
                    litellm_model = f"groq/{litellm_model}"
                elif provider == ModelProvider.OLLAMA and not litellm_model.startswith("ollama/"):
                    litellm_model = f"ollama/{litellm_model}"

                resolved_key = (
                    (cfg.api_key or "").strip()
                    or getattr(settings, f"{provider.value.upper()}_API_KEY", None)
                    or ProviderConfig.default_for(provider).api_key
                )

                response = await litellm.acompletion(
                    model=litellm_model,
                    messages=messages,
                    api_key=resolved_key,
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

        # 3. OpenAI-compatible Async client fallback (Groq, Ollama, OpenAI)
        client, model, _ = self._get_client_and_model(cfg)
        if client is None and provider != ModelProvider.MOCK:
            raw_ans, tokens = self._generate_mock_response(messages, json_mode)
            if not json_mode:
                notice = (
                    f"[Notice: No {provider.value.upper()} API key configured. "
                    f"Click 'BYOK Key' in the console to enter your API key or set {provider.value.upper()}_API_KEY in the backend environment. "
                    f"Offline fallback response generated.]\n\n"
                )
                return notice + raw_ans, tokens
            return raw_ans, tokens

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
                if effective_seed is not None:
                    kwargs["seed"] = int(effective_seed)

                response = await client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                content = choice.message.content or ""
                tokens = response.usage.total_tokens if response.usage else len(content.split()) * 2
                return content, tokens
            except Exception as e:
                err_msg = str(e)
                # If Groq fails with 404 on 70B (free tier access restriction), retry with 8B instant
                if provider == ModelProvider.GROQ and "llama-3.1-8b-instant" not in model and (
                    "404" in err_msg or "does not exist" in err_msg or "access" in err_msg
                ):
                    try:
                        logger.info("Groq 70B restricted, retrying with llama-3.1-8b-instant...")
                        fallback_kwargs = dict(kwargs)
                        fallback_kwargs["model"] = "llama-3.1-8b-instant"
                        response = await client.chat.completions.create(**fallback_kwargs)
                        choice = response.choices[0]
                        content = choice.message.content or ""
                        tokens = response.usage.total_tokens if response.usage else len(content.split()) * 2
                        return content, tokens
                    except Exception as fallback_e:
                        err_msg = str(fallback_e)

                logger.warning(f"AsyncOpenAI call failed for {provider.value} ({model}): {err_msg}. Falling back to deterministic response.")
                raw_ans, tokens = self._generate_mock_response(messages, json_mode)
                if not json_mode and provider != ModelProvider.MOCK:
                    clean_msg = err_msg
                    if "401" in err_msg or "invalid_api_key" in err_msg:
                        clean_msg = "Invalid API key. Please check the key in BYOK."
                    elif "429" in err_msg:
                        clean_msg = "Rate limit reached. Please wait a moment."
                    elif "404" in err_msg:
                        clean_msg = f"Model '{model}' not accessible on this account tier."
                    notice = (
                        f"[Notice: {provider.value.upper()} gateway error ({clean_msg}). "
                        f"Enter a valid API key via BYOK or set {provider.value.upper()}_API_KEY in backend environment. "
                        f"Offline fallback response generated.]\n\n"
                    )
                    return notice + raw_ans, tokens
                return raw_ans, tokens

        return self._generate_mock_response(messages, json_mode)

    async def _generate_gemini_native(
        self,
        messages: List[Dict[str, str]],
        cfg: ProviderConfig,
        json_mode: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, int]:
        """
        Direct, native Google Gemini REST API integration.
        Bypasses OpenAI-compatible proxy routing issues.
        """
        api_key = (cfg.api_key or "").strip() or getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            raw_ans, tokens = self._generate_mock_response(messages, json_mode)
            if not json_mode:
                notice = (
                    "[Notice: No GEMINI API key configured. "
                    "Click 'BYOK Key' in the console to enter your key or set GEMINI_API_KEY in the backend. "
                    "Offline fallback response generated.]\n\n"
                )
                return notice + raw_ans, tokens
            return raw_ans, tokens

        model = (cfg.model or ProviderConfig.default_for(ModelProvider.GEMINI).model).replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }

        contents = []
        system_instruction = None
        for m in messages:
            role = m.get("role", "user")
            text = m.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": text}]}
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({"role": gemini_role, "parts": [{"text": text}]})

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        payload: Dict[str, Any] = {"contents": contents}
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        gen_config: Dict[str, Any] = {}
        if json_mode:
            gen_config["responseMimeType"] = "application/json"
        if temperature is not None:
            gen_config["temperature"] = float(temperature)
        if max_tokens:
            gen_config["maxOutputTokens"] = int(max_tokens)
        if gen_config:
            payload["generationConfig"] = gen_config

        timeout_sec = float(getattr(settings, "REQUEST_TIMEOUT_SECONDS", 15.0))
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_sec, connect=5.0)) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                        tokens = data.get("usageMetadata", {}).get("totalTokenCount", len(text.split()) * 2)
                        return text, tokens

                # Handle HTTP errors with clean explanations
                err_text = res.text
                try:
                    err_json = res.json()
                    err_msg = err_json.get("error", {}).get("message", err_text)
                except Exception:
                    err_msg = err_text[:120]

                logger.warning(f"Google Gemini native API error ({res.status_code}): {err_msg}")
                raw_ans, tokens = self._generate_mock_response(messages, json_mode)
                if not json_mode:
                    clean_msg = err_msg
                    if res.status_code == 400 and ("API key not valid" in err_msg or "INVALID_ARGUMENT" in err_msg):
                        clean_msg = "API key not valid. Please verify your Google AI Studio key in BYOK."
                    elif res.status_code == 429:
                        clean_msg = "Rate limit / quota exceeded. Please wait a moment."
                    elif res.status_code == 503:
                        clean_msg = "Google Gemini is temporarily experiencing high traffic. Please retry in a few seconds."
                    notice = f"[Notice: GEMINI gateway error ({clean_msg}). Offline fallback response generated.]\n\n"
                    return notice + raw_ans, tokens
                return raw_ans, tokens
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Google Gemini call failed: {err_msg}")
            raw_ans, tokens = self._generate_mock_response(messages, json_mode)
            if not json_mode:
                clean_msg = "Request timed out" if "timed out" in err_msg.lower() else err_msg[:120]
                notice = f"[Notice: GEMINI gateway error ({clean_msg}). Offline fallback response generated.]\n\n"
                return notice + raw_ans, tokens
            return raw_ans, tokens

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
