"""
AI Service Configuration and Hyperparameters.
Reads from environment variables and provides sensible defaults for offline, cloud, and local execution.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from models.provider import ModelProvider


class AIServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys (BYOK or environment)
    GROQ_API_KEY: Optional[str] = Field(default=None)
    NVIDIA_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)

    # Local Ollama endpoint
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")

    # Default Provider and Model Selection
    DEFAULT_PROVIDER: ModelProvider = Field(default=ModelProvider.GROQ)
    DEFAULT_MODEL: str = Field(default="llama-3.3-70b-versatile")
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

    # Mathematical Trust Dynamics Hyperparameters (Theorem 1)
    ALPHA_SUCCESS: float = Field(default=0.85, description="Asymmetric EMA success momentum (Condition D-legacy)")
    BETA_FAILURE: float = Field(default=0.70, description="Asymmetric EMA failure punitive decay (Condition D-legacy)")
    ALPHA_SYMMETRIC: float = Field(default=0.80, description="Symmetric EMA momentum for Condition C (Reflexion)")
    THETA_CUTOFF: float = Field(default=0.35, description="Safety cutoff for quarantine pruning")
    INITIAL_TRUST: float = Field(default=0.75, description="Default initial trust S_0")

    # Bayesian Conjugate Prior Hyperparameters (Ours - Novel Framework)
    PRIOR_ALPHA: float = Field(default=3.0, description="Weakly-informative Beta prior success parameter alpha_0")
    PRIOR_BETA: float = Field(default=1.0, description="Weakly-informative Beta prior failure parameter beta_0")
    LAMBDA_RISK: float = Field(default=1.0, description="Pessimistic LCB risk aversion parameter lambda")
    QUARANTINE_GAMMA: float = Field(default=0.05, description="Bayesian quarantine hypothesis test significance level gamma")
    RELIABILITY_THRESHOLD: float = Field(default=0.70, description="Operational admissibility standard for active memories")
    
    # Constrained Hybrid Retrieval Weights
    WEIGHT_SIMILARITY: float = Field(default=0.70, description="Weight for semantic cosine similarity")
    WEIGHT_TRUST: float = Field(default=0.30, description="Weight for empirical trust S_e(t)")
    SIMILARITY_THRESHOLD: float = Field(default=0.60, description="Minimum cosine similarity cutoff")

    # Storage Paths
    SQLITE_DB_PATH: str = Field(default="data/adaptive_memory.db")
    SUPABASE_URL: Optional[str] = Field(default=None)
    SUPABASE_ANON_KEY: Optional[str] = Field(default=None)
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(default=None)

    # Execution Bounds
    MAX_CYCLICAL_LOOPS: int = Field(default=3, description="Maximum reflection loops before forced exit")
    REQUEST_TIMEOUT_SECONDS: float = Field(default=45.0)


# Global singleton settings instance
settings = AIServiceSettings()
