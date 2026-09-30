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
