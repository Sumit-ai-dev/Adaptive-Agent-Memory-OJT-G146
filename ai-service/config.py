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
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys (BYOK or environment)
    GROQ_API_KEY: Optional[str] = Field(default=None)
    NVIDIA_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    MEM0_API_KEY: Optional[str] = Field(default=None)
    ADMIN_API_KEY: Optional[str] = Field(default=None)

    # Local Ollama endpoint
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")

    # Default Provider and Model Selection
    DEFAULT_PROVIDER: ModelProvider = Field(default=ModelProvider.GROQ)
    DEFAULT_MODEL: str = Field(default="openai/gpt-oss-120b")
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

    # Storage Paths & Engines
    STORAGE_ENGINE: str = Field(default="sqlite", description="Storage backend: 'sqlite', 'postgres', or 'supabase'")
    SQLITE_DB_PATH: str = Field(default="data/adaptive_memory.db")
    DATABASE_URL: Optional[str] = Field(default=None, description="PostgreSQL / Supabase connection URL with pgvector")
    SUPABASE_URL: Optional[str] = Field(default=None)
    SUPABASE_ANON_KEY: Optional[str] = Field(default=None)
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(default=None)

    # Execution Bounds
    MAX_CYCLICAL_LOOPS: int = Field(default=3, description="Maximum reflection loops before forced exit")
    REQUEST_TIMEOUT_SECONDS: float = Field(default=90.0, description="HTTP timeout in seconds for LLM generation requests")

    # Token Budgeting & Context Compaction Bounds (Issue #38)
    MAX_PROMPT_TOKENS: int = Field(default=4096, description="Upper bound for total task prompt context tokens")
    MAX_RETRIEVED_MEMORY_TOKENS: int = Field(default=800, description="Strict upper bound for injected experiential memories into prompts")
    MAX_TASK_COST_USD: float = Field(default=0.05, description="Maximum allowed token expenditure in USD per task execution")
    MAX_TASK_TOKENS: int = Field(default=8192, description="Upper bound for cumulative tokens across cyclical execution loops")
    TOKENIZER_ENCODING: str = Field(default="cl100k_base", description="Default tokenizer encoding family for budget calculations")

    # Security & API Protection
    HOST: str = Field(default="127.0.0.1", description="Default network bind address for the API server")
    PORT: int = Field(default=8000, description="Default port for the API server")
    AGENT_API_KEY: Optional[str] = Field(default=None, description="API key required for agent execution when auth is enabled")
    REQUIRE_AGENT_AUTH: bool = Field(default=False, description="When true, requires valid AGENT_API_KEY or ADMIN_API_KEY on /agent/execute")
    REQUIRE_USER_AUTH: bool = Field(default=False, description="When true, strictly requires authenticated user context or machine API key")
    SUPABASE_JWT_SECRET: Optional[str] = Field(default=None, description="Supabase GoTrue JWT secret for validating user Bearer tokens")
    AEMA_JWT_SECRET: str = Field(default="dev-insecure-jwt-secret-do-not-use-in-prod-12345", description="Fallback secret for local JWT signing and test verification")
    JWT_ALGORITHM: str = Field(default="HS256", description="Algorithm for symmetric JWT validation")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60, description="Max execution requests per minute per IP")
    CORS_ALLOWED_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origin list",
    )
    SANDBOX_AST_STRICT: bool = Field(default=True, description="Enforce strict AST code safety verification before evaluation")

    # Observability & Distributed Tracing (Issue #36)
    OBSERVABILITY_ENABLED: bool = Field(default=True, description="Enable distributed tracing telemetry")
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(default=None, description="Langfuse Cloud or Self-hosted Public Key")
    LANGFUSE_SECRET_KEY: Optional[str] = Field(default=None, description="Langfuse Cloud or Self-hosted Secret Key")
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com", description="Langfuse host URL")
    LANGSMITH_TRACING: bool = Field(default=False, description="Enable LangSmith OpenTelemetry tracing")
    LANGSMITH_API_KEY: Optional[str] = Field(default=None, description="LangSmith API Key")
    LANGSMITH_PROJECT: str = Field(default="adaptive-agent-memory", description="LangSmith Project Name")


# Global singleton settings instance
settings = AIServiceSettings()
