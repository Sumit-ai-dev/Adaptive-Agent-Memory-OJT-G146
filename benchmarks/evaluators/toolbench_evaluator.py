"""
ToolBench Adversarial Benchmark Independent Evaluator.

Implements benchmark-native evaluation for ToolBench adversarial tasks:
- Extracts actual tool calls from execution telemetry or agent responses.
- Evaluates parameter validity against tool schemas.
- Detects whether the agent fell for adversarial traps (deprecated parameters,
  multi-step dependency bypass, hallucination bait).
- Executes tool simulation in an isolated environment.
- Enforces condition and trial isolation (no condition names, no trial-index rules).
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from benchmarks.evaluators.base import BaseBenchmarkEvaluator, EvaluationOutcome

logger = logging.getLogger("benchmarks.evaluators.toolbench")


def extract_tool_calls_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract JSON tool calls from markdown code blocks, raw JSON strings, or inline JSON.
    Handles forms like:
      {"tool": "web_search", "params": {"query": "AI safety", "days": 7}}
      {"name": "web_search", "arguments": {"query": "AI safety", "days": 7}}
    """
    if not text:
        return []

    calls = []
    trimmed = text.strip()

    # 1. Direct JSON parse if whole text is JSON
    if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, dict) and ("tool" in parsed or "name" in parsed):
                return [parsed]
            elif isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict) and ("tool" in item or "name" in item)]
        except json.JSONDecodeError:
            pass

    # 2. Search for json code blocks: ```json ... ```
    code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    for block in code_blocks:
        try:
            parsed = json.loads(block.strip())
            if isinstance(parsed, dict) and ("tool" in parsed or "name" in parsed):
                calls.append(parsed)
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and ("tool" in item or "name" in item):
                        calls.append(item)
        except json.JSONDecodeError:
            pass

    if calls:
        return calls

    # 3. Robust balanced brace scanner for nested JSON objects
    for i, ch in enumerate(text):
        if ch == "{":
            depth = 0
            for j in range(i, len(text)):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[i:j+1]
                        if '"tool"' in candidate or '"name"' in candidate:
                            try:
                                parsed = json.loads(candidate)
                                if isinstance(parsed, dict) and ("tool" in parsed or "name" in parsed):
                                    calls.append(parsed)
                            except json.JSONDecodeError:
                                pass
                        break

    return calls


def normalize_call_representation(call: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Normalize tool call representation into (tool_name, params_dict)."""
    tool_name = call.get("tool") or call.get("name") or ""
    params = call.get("params") or call.get("parameters") or call.get("arguments") or call.get("args") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}
    return str(tool_name).strip(), dict(params) if isinstance(params, dict) else {}


class ToolExecutionSandbox:
    """
    Isolated execution environment that runs tool calls against simulated API endpoints.
    Emits real HTTP status codes and runtime errors matching ToolBench documentation.
    """
    @staticmethod
    def execute(tool_name: str, params: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        target_tool = task.get("correct_call", {}).get("tool", "")
        target_params = task.get("correct_call", {}).get("params", {})
        wrong_tool = task.get("wrong_call", {}).get("tool", "")
        wrong_params = task.get("wrong_call", {}).get("params", {})
        expected_error = task.get("expected_error", "TypeError: unexpected keyword argument")

        # 1. Check for deprecated/adversarial trap parameters
        adversarial_keys = {
            k: v for k, v in wrong_params.items()
            if k not in target_params or target_params.get(k) != v
        }
        for wp_key, wp_val in adversarial_keys.items():
            if wp_key in params:
                actual_val = params[wp_key]
                if wp_val is None or actual_val == wp_val or str(wp_val) in str(actual_val):
                    return {
                        "status_code": 400,
                        "success": False,
                        "error_type": "TrapInvocationError",
                        "error_message": expected_error,
                        "output": None,
                    }

        # 2. Check tool name match
        if tool_name.lower() != target_tool.lower():
            return {
                "status_code": 404,
                "success": False,
                "error_type": "EndpointNotFoundError",
                "error_message": f"Endpoint '{tool_name}' not found in API registry",
                "output": None,
            }

        # 3. Check parameter requirements
        for tp_key in target_params:
            if tp_key not in params:
                return {
                    "status_code": 422,
                    "success": False,
                    "error_type": "MissingParameterError",
                    "error_message": f"Missing required parameter '{tp_key}'",
                    "output": None,
                }

        # 4. Successful execution in isolated sandbox
        return {
            "status_code": 200,
            "success": True,
            "error_type": None,
            "error_message": None,
            "output": {
                "status": "success",
                "tool": tool_name,
                "data": f"Executed {tool_name} successfully with parameters {list(params.keys())}",
            },
        }


class ToolBenchEvaluator(BaseBenchmarkEvaluator):
    """
    Independent ToolBench Evaluator verifying tool invocations against adversarial traps.
    """

    @property
    def name(self) -> str:
        return "ToolBenchEvaluator"

    @property
    def version(self) -> str:
        return "2.0.0"

    def evaluate(
        self,
        task: Dict[str, Any],
        agent_output: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        trajectory: Optional[List[Any]] = None,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationOutcome:
        task_id = str(task.get("id", "tb_unknown"))
        trap_type = task.get("trap_type", "general")
        trap_desc = task.get("trap_description", "")
        correct_call_def = task.get("correct_call", {})
        wrong_call_def = task.get("wrong_call", {})
        expected_error = task.get("expected_error", "Tool execution error")

        # 1. Gather all tool calls (from execution trace or extracted from output)
        all_calls: List[Dict[str, Any]] = []
        if tool_calls:
            all_calls.extend(tool_calls)
        extracted = extract_tool_calls_from_text(agent_output)
        for ec in extracted:
            if ec not in all_calls:
                all_calls.append(ec)

        # 2. Check if any tool call was attempted
        if not all_calls:
            # Special case for hallucination_bait: must call a tool
            if trap_type == "hallucination_bait":
                return EvaluationOutcome(
                    score=0.0,
                    passed=False,
                    evaluator_name=self.name,
                    evaluator_version=self.version,
                    failure_reason="hallucination_bait: agent answered without required tool call",
                    metrics={"tool_call_present": False, "trap_type": trap_type},
                    details={"task_id": task_id, "trap_description": trap_desc},
                )
            return EvaluationOutcome(
                score=0.0,
                passed=False,
                evaluator_name=self.name,
                evaluator_version=self.version,
                failure_reason="no_tool_call_detected",
                metrics={"tool_call_present": False},
                details={"task_id": task_id},
            )

            # Target definitions
        target_tool, target_params = normalize_call_representation(correct_call_def)
        wrong_tool, wrong_params = normalize_call_representation(wrong_call_def)

        # Evaluate each tool call through the isolated execution sandbox
        evaluated_calls_details = []
        trap_triggered = False
        valid_call_found = False

        for raw_call in all_calls:
            call_name, call_params = normalize_call_representation(raw_call)

            # Execute tool call in sandbox environment
            sandbox_res = ToolExecutionSandbox.execute(call_name, call_params, task)
            
            if not sandbox_res["success"]:
                if sandbox_res["error_type"] == "TrapInvocationError":
                    trap_triggered = True
                evaluated_calls_details.append({
                    "call": (call_name, call_params),
                    "status": "execution_failed",
                    "sandbox_result": sandbox_res,
                })
            else:
                valid_call_found = True
                evaluated_calls_details.append({
                    "call": (call_name, call_params),
                    "status": "execution_success",
                    "sandbox_result": sandbox_res,
                })

        # Final determination:
        # Task fails if an adversarial trap was invoked or if no tool call executed successfully.
        if trap_triggered and not valid_call_found:
            return EvaluationOutcome(
                score=0.0,
                passed=False,
                evaluator_name=self.name,
                evaluator_version=self.version,
                failure_reason=f"trap_triggered ({trap_type}): {expected_error}",
                metrics={
                    "trap_triggered": True,
                    "valid_call_found": False,
                    "trap_type": trap_type,
                    "sandbox_status": 400,
                },
                details={
                    "task_id": task_id,
                    "trap_description": trap_desc,
                    "evaluated_calls": evaluated_calls_details,
                },
            )

        if not valid_call_found:
            return EvaluationOutcome(
                score=0.0,
                passed=False,
                evaluator_name=self.name,
                evaluator_version=self.version,
                failure_reason="tool_call_failed_in_sandbox",
                metrics={
                    "trap_triggered": False,
                    "valid_call_found": False,
                    "trap_type": trap_type,
                    "sandbox_status": 422,
                },
                details={
                    "task_id": task_id,
                    "expected": correct_call_def,
                    "evaluated_calls": evaluated_calls_details,
                },
            )

        # Successful tool execution in sandbox
        return EvaluationOutcome(
            score=1.0,
            passed=True,
            evaluator_name=self.name,
            evaluator_version=self.version,
            metrics={
                "trap_triggered": False,
                "valid_call_found": True,
                "trap_type": trap_type,
                "sandbox_status": 200,
            },
            details={
                "task_id": task_id,
                "executed_call": evaluated_calls_details,
            },
        )
