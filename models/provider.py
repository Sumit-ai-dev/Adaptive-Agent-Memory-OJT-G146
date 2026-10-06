"""
LLM Provider Enums and BYOK Configurations.
Supports Groq (free cloud default), NVIDIA NIM, local Ollama, OpenAI, Gemini, Anthropic, and deterministic Mock.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


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
    model: str = Field(default="llama-3.3-70b-versatile")
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=64, le=16384)
    seed: Optional[int] = Field(default=None, description='S9: only set for seed-capable providers')

    @classmethod
    def default_for(cls, provider: ModelProvider) -> "ProviderConfig":
        if provider == ModelProvider.GROQ:
            return cls(
                provider=ModelProvider.GROQ,
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
            )
        elif provider == ModelProvider.NVIDIA:
            return cls(
                provider=ModelProvider.NVIDIA,
                model="nvidia/llama-3.1-nemotron-70b-instruct",
                base_url="https://integrate.api.nvidia.com/v1",
            )
        elif provider == ModelProvider.OLLAMA:
            return cls(
                provider=ModelProvider.OLLAMA,
                model="llama3.2:3b",
                base_url="http://localhost:11434/v1",
                api_key="ollama",
            )
        elif provider == ModelProvider.GEMINI:
            return cls(
                provider=ModelProvider.GEMINI,
                model="gemini-2.0-flash",
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
        elif provider == ModelProvider.OPENAI:
            return cls(
                provider=ModelProvider.OPENAI,
                model="gpt-4o-mini",
                base_url="https://api.openai.com/v1",
            )
        elif provider == ModelProvider.MOCK:
            return cls(
                provider=ModelProvider.MOCK,
                model="mock-deterministic-v1",
                base_url="mock://localhost",
            )
        return cls(provider=provider, model="default")


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
