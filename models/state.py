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
    memory_store: Optional[Any]
    
    # Retrieval outputs
    retrieved_memories: List[Dict[str, Any]]
    positive_strategy: Optional[str]
    negative_pitfall: Optional[str]
    
    # Execution & tool call traces
    messages: List[Dict[str, str]]
    tool_calls: List[Dict[str, Any]]
    final_answer: Optional[str]
    
    # Evaluation outputs
    outcome_score: float           # R_t in [0.0, 1.0]
    outcome_quality: str           # "positive", "neutral", "negative"
    evaluator_reason: str
    
    # Reflection & candidate memory
    candidate_experience: Optional[Dict[str, Any]]
    new_experience_created: bool
    
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
