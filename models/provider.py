"""
LLM Provider Enums and BYOK Configurations.
Supports Groq (free cloud default), NVIDIA NIM, local Ollama, OpenAI, Gemini, Anthropic, and deterministic Mock.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class ModelProvider(str, Enum):
    GROQ = "groq"
    NVIDIA = "nvidia"
    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class ProviderConfig(BaseModel):
    provider: ModelProvider = Field(default=ModelProvider.GROQ)
    model: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=64, le=16384)
    seed: Optional[int] = Field(default=None, description='S9: only set for seed-capable providers')

    @model_validator(mode="after")
    def _resolve_defaults(self) -> "ProviderConfig":
        model_defaults = {
            ModelProvider.GROQ: ("openai/gpt-oss-120b", "https://api.groq.com/openai/v1", None),
            ModelProvider.NVIDIA: ("nvidia/llama-3.1-nemotron-70b-instruct", "https://integrate.api.nvidia.com/v1", None),
            ModelProvider.OLLAMA: ("llama3.2:3b", "http://localhost:11434/v1", "ollama"),
            ModelProvider.GEMINI: ("gemini-1.5-flash", "https://generativelanguage.googleapis.com/v1beta", None),
            ModelProvider.OPENAI: ("gpt-4o-mini", "https://api.openai.com/v1", None),
            ModelProvider.ANTHROPIC: ("claude-3-5-haiku-20241022", "https://api.anthropic.com/v1", None),
            ModelProvider.MOCK: ("mock-deterministic-v1", "mock://localhost", None),
        }
        def_model, def_url, def_key = model_defaults.get(self.provider, ("default", None, None))
        if self.model is None or not str(self.model).strip():
            self.model = def_model
        if self.base_url is None:
            self.base_url = def_url
        if self.api_key is None and def_key is not None:
            self.api_key = def_key
        return self

    @classmethod
    def default_for(cls, provider: ModelProvider) -> "ProviderConfig":
        return cls(provider=provider)


# ======================================================================
# S9: provider seed-capability contract
# ======================================================================
#
# A recorded seed must correspond to a seed the provider actually honours.
# Providers whose chat API exposes a `seed` parameter are listed as True;
# everything else is False and MUST reject a seed request rather than record
# one that was never applied.
PROVIDER_SUPPORTS_SEED: dict = {
    ModelProvider.OPENAI: True,    # OpenAI chat completions accept `seed`
    ModelProvider.OLLAMA: True,    # Ollama's OpenAI-compatible endpoint accepts `seed`
    ModelProvider.GROQ: True,      # Groq's OpenAI-compatible endpoint accepts `seed`
    ModelProvider.NVIDIA: True,    # NIM OpenAI-compatible endpoint accepts `seed`
    ModelProvider.GEMINI: False,   # no seed on the OpenAI-compat shim
    ModelProvider.ANTHROPIC: False,# Messages API exposes no seed
    ModelProvider.MOCK: False,     # deterministic by construction; a seed would be meaningless
}


def provider_supports_seed(provider) -> bool:
    """True when the provider genuinely honours a `seed` parameter."""
    if not isinstance(provider, ModelProvider):
        provider = ModelProvider(str(provider))
    return bool(PROVIDER_SUPPORTS_SEED.get(provider, False))


class UnsupportedSeedError(ValueError):
    """Raised when a seed is requested from a provider that cannot honour it."""


def validate_seed(provider, seed) -> None:
    """
    Rejects a seed request the provider cannot satisfy.

    Deliberately strict: silently recording an unused seed would make a run manifest
    claim reproducibility it does not have.
    """
    if seed is None:
        return
    if not provider_supports_seed(provider):
        name = provider.value if isinstance(provider, ModelProvider) else str(provider)
        raise UnsupportedSeedError(
            f"provider '{name}' does not support a seed parameter; "
            f"requested seed={seed!r}. Use seed=None (recorded as not-applicable) "
            f"or choose a seed-capable provider."
        )
