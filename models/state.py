"""
LangGraph AgentState TypedDict for the 5-Node Cyclical Orchestration StateGraph.
Tracks runtime context across:
  retrieve_node -> execute_node -> evaluate_node -> reflect_node -> trust_node
"""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # Initial task parameters
    execution_id: str
    task_id: str
    user_id: Optional[str]
    task_input: str
    task_domain: str
    memory_enabled: bool
    memory_mode: str               # "off", "naive", "symmetric", "adaptive"
    
    # Provider & model settings
    provider: Optional[str]
    model: Optional[str]
    api_key: Optional[str]
    temperature: Optional[float]   # S8: effective sampling temperature
    seed: Optional[int]            # S9: only set for seed-capable providers
    max_tokens: Optional[int]      # S12: None => provider default
    memory_store: Optional[Any]
    # Step 1: injected run-scoped, policy-backed retriever. When present, retrieval
    # reads trust state from the RunContext and admissibility from the injected
    # TrustPolicy instead of from the shared memory bank.
    policy_retriever: Optional[Any]
    top_k: int
    
    # Retrieval outputs
    retrieved_memories: List[Dict[str, Any]]
    positive_strategy: Optional[str]
    negative_pitfall: Optional[str]
    
    # Execution & tool call traces
    messages: List[Dict[str, str]]
    tool_calls: List[Dict[str, Any]]
    final_answer: Optional[str]
    
    # Evaluator selection (F2) -- explicit at task level, never inferred from task_domain
    evaluator: Optional[str]            # EvaluatorName value, or None to infer from directives
    evaluator_config: Dict[str, Any]    # e.g. {"test_code": ..., "timeout_s": 10}

    # Evaluation outputs
    outcome_score: float           # R_t in [0.0, 1.0] -- continuous reward, always retained
    outcome_quality: str           # "positive", "neutral", "negative"
    evaluator_reason: str

    # F3 outcome contract: produced by the evaluator, consumed by the trust layer
    binary_outcome: int            # 0 or 1
    outcome_threshold: float       # explicit binarisation cut-point
    evaluator_name: str
    evaluator_version: str

    # F1: per-attempt diagnostics. Copy-appended by evaluate_node on every retry
    # iteration (same convention as `trajectory`). The TERMINAL entry defines the
    # single task-level outcome; earlier entries are diagnostic only.
    attempts: List[Dict[str, Any]]
    
    # Reflection & candidate memory
    candidate_experience: Optional[Dict[str, Any]]
    new_experience_created: bool
    # `trust_node` has always returned this key, but it was never declared as a
    # channel, so LangGraph dropped it from the final state. Harmless while the node
    # persisted directly; load-bearing now that execute_task performs the single
    # task-level write.
    new_experience: Optional[Any]
    
    # Trust dynamics
    trust_updates: List[Dict[str, Any]]
    
    # Telemetry and loop management
    trajectory: List[Dict[str, Any]]
    tokens_used: int
    loop_count: int
    max_loops: int
    start_time: float
    latency_ms: int
    status: str
    error: Optional[str]
