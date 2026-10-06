"""
LangGraph Node 4: reflect_node
Distills completed execution trajectories into structured procedural tuples:
  {trigger_condition, strategy_lesson, pitfall, confidence}
Saves candidate experiences into quarantine status for empirical validation.
"""

import json
import time
from typing import Any, Dict

from ai_service.llm_client import llm_gateway, resolve_provider_config
from models.domain import TaskDomain
from models.experience import ExperienceStatus
from models.state import AgentState


async def reflect_node(state: AgentState) -> Dict[str, Any]:
    start_ts = time.time()
    task_input = state.get("task_input", "")
    domain = state.get("task_domain", "general")
    final_answer = state.get("final_answer", "")
    outcome_score = state.get("outcome_score", 0.5)

    prompt = (
        f"You are the Reflection Engine for an autonomous agent with persistent experiential memory.\n"
        f"Analyze this completed task execution:\n"
        f"Task: {task_input}\n"
        f"Domain: {domain}\n"
        f"Final Output: {final_answer[:400]}\n"
        f"Outcome Score (R): {outcome_score:.2f}\n\n"
        f"Extract a structured experience tuple in valid JSON format with keys:\n"
        f"- 'trigger_condition': General applicability predicate (when to recall this lesson)\n"
        f"- 'strategy_lesson': Actionable positive operational directive (+sigma)\n"
        f"- 'pitfall': Critical negative pitfall to avoid (-pi)\n"
        f"- 'confidence': Float between 0.0 and 1.0"
    )

    messages = [
        {"role": "system", "content": "You extract concise, actionable procedural memory tuples in JSON."},
        {"role": "user", "content": prompt},
    ]

    # S8: reflection previously called the gateway with NO config, silently falling
    # through to `default_config` resolved from ambient environment variables. It now
    # uses the run's declared provider/model/temperature like every other call site.
    provider_config, requested_temperature = resolve_provider_config(state)

    candidate_exp = None
    try:
        raw_json, _ = await llm_gateway.generate(
            messages, config=provider_config, json_mode=True,
            temperature=requested_temperature,
        )
        # Parse JSON
        parsed = json.loads(raw_json)
        candidate_exp = {
            "task_domain": domain,
            "trigger_condition": parsed.get("trigger_condition", f"Tasks similar to: {task_input[:50]}"),
            "strategy_lesson": parsed.get("strategy_lesson", "Follow verified step-by-step reasoning constraints."),
            "pitfall": parsed.get("pitfall", "Avoid relying on uncorroborated single-source facts."),
            "confidence": float(parsed.get("confidence", 0.85)),
            "status": ExperienceStatus.CANDIDATE.value,
        }
    except Exception:
        candidate_exp = {
            "task_domain": domain,
            "trigger_condition": f"Tasks involving: {task_input[:50]}",
            "strategy_lesson": "Verify domain constraints and validate output syntax against expectations.",
            "pitfall": "Do not skip preliminary boundary condition validation.",
            "confidence": 0.80,
            "status": ExperienceStatus.CANDIDATE.value,
        }

    duration_ms = int((time.time() - start_ts) * 1000)

    # Build stepper trace
    trace = {
        "id": f"step_reflect_{int(start_ts)}",
        "type": "reflection",
        "node": "reflect_node",
        "title": "Structured Experience Distillation",
        "detail": (
            f"Distilled candidate experience tuple for domain '{domain}'. "
            f"Strategy: '{candidate_exp['strategy_lesson'][:70]}...'. "
            f"Pitfall: '{candidate_exp['pitfall'][:70]}...'."
        ),
        "durationMs": duration_ms,
        "metadata": {
            "candidate": candidate_exp,
        },
    }

    trajectory = list(state.get("trajectory", []))
    trajectory.append(trace)

    return {
        "candidate_experience": candidate_exp,
        "new_experience_created": True,
        "trajectory": trajectory,
        "status": "updating_trust",
    }
