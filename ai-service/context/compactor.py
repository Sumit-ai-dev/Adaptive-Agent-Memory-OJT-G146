"""
Dynamic Context Compaction for Experiential Memories.
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)

Implements deterministic rank-then-cut context compaction for experiential memories
under strict token budgets (Theorem 1 / Issue #38):
- Strict <= 800 token cap on injected memory prompts
- Fair-share & proportional allocation between positive strategies (+sigma) and negative pitfalls (-pi)
- Eliminates context-window overflow (HTTP 400 Bad Request) from LLM providers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ai_service.context.token_budget import count_tokens, truncate_text_to_tokens

logger = logging.getLogger("ai_service.context.compactor")


@dataclass
class MemoryCompactionResult:
    """Detailed outcome of a memory context compaction pass."""
    positive_strategy: Optional[str]
    negative_pitfall: Optional[str]
    original_tokens: int
    compacted_tokens: int
    was_compacted: bool
    strategy_tokens: int
    pitfall_tokens: int
    budget: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "originalTokens": self.original_tokens,
            "compactedTokens": self.compacted_tokens,
            "wasCompacted": self.was_compacted,
            "strategyTokens": self.strategy_tokens,
            "pitfallTokens": self.pitfall_tokens,
            "budget": self.budget,
        }


def compact_memory_context(
    positive_strategy: Optional[str],
    negative_pitfall: Optional[str],
    max_tokens: int = 800,
    encoding_name: Optional[str] = None,
) -> MemoryCompactionResult:
    """
    Deterministically compacts positive strategies (+sigma) and negative pitfalls (-pi)
    to guarantee their cumulative token count does not exceed max_tokens (default 800).

    Allocation Strategy:
    1. If combined tokens <= max_tokens: retain both completely without modification.
    2. If only one is present: allocate the full max_tokens budget to that component.
    3. If both are present and combined tokens > max_tokens:
       - Give equal base quota (max_tokens // 2 = 400).
       - If one component is smaller than its quota, transfer unused capacity to the other.
       - Truncate cleanly at word boundaries with deterministic truncation.
    """
    strat_clean = (positive_strategy or "").strip()
    pit_clean = (negative_pitfall or "").strip()

    strat_orig_tokens = count_tokens(strat_clean, encoding_name=encoding_name) if strat_clean else 0
    pit_orig_tokens = count_tokens(pit_clean, encoding_name=encoding_name) if pit_clean else 0
    total_orig_tokens = strat_orig_tokens + pit_orig_tokens

    if total_orig_tokens <= max_tokens:
        return MemoryCompactionResult(
            positive_strategy=strat_clean if strat_clean else None,
            negative_pitfall=pit_clean if pit_clean else None,
            original_tokens=total_orig_tokens,
            compacted_tokens=total_orig_tokens,
            was_compacted=False,
            strategy_tokens=strat_orig_tokens,
            pitfall_tokens=pit_orig_tokens,
            budget=max_tokens,
        )

    # Context exceeds budget: deterministic rank-and-cut allocation
    final_strat: Optional[str] = None
    final_pit: Optional[str] = None
    final_strat_tokens = 0
    final_pit_tokens = 0

    if strat_clean and not pit_clean:
        final_strat, final_strat_tokens = truncate_text_to_tokens(
            strat_clean, max_tokens=max_tokens, encoding_name=encoding_name
        )
    elif pit_clean and not strat_clean:
        final_pit, final_pit_tokens = truncate_text_to_tokens(
            pit_clean, max_tokens=max_tokens, encoding_name=encoding_name
        )
    else:
        # Both strategy and pitfall are present
        half_budget = max_tokens // 2

        if strat_orig_tokens <= half_budget:
            # Strategy fits in its half; pitfall gets the rest
            final_strat = strat_clean
            final_strat_tokens = strat_orig_tokens
            pit_budget = max(0, max_tokens - strat_orig_tokens)
            final_pit, final_pit_tokens = truncate_text_to_tokens(
                pit_clean, max_tokens=pit_budget, encoding_name=encoding_name
            )
        elif pit_orig_tokens <= half_budget:
            # Pitfall fits in its half; strategy gets the rest
            final_pit = pit_clean
            final_pit_tokens = pit_orig_tokens
            strat_budget = max(0, max_tokens - pit_orig_tokens)
            final_strat, final_strat_tokens = truncate_text_to_tokens(
                strat_clean, max_tokens=strat_budget, encoding_name=encoding_name
            )
        else:
            # Both exceed half budget; partition equally
            strat_budget = half_budget
            pit_budget = max_tokens - half_budget

            final_strat, final_strat_tokens = truncate_text_to_tokens(
                strat_clean, max_tokens=strat_budget, encoding_name=encoding_name
            )
            final_pit, final_pit_tokens = truncate_text_to_tokens(
                pit_clean, max_tokens=pit_budget, encoding_name=encoding_name
            )

    total_compacted_tokens = final_strat_tokens + final_pit_tokens

    logger.info(
        "Compacted experiential memory context from %d to %d tokens (budget=%d).",
        total_orig_tokens,
        total_compacted_tokens,
        max_tokens,
    )

    return MemoryCompactionResult(
        positive_strategy=final_strat,
        negative_pitfall=final_pit,
        original_tokens=total_orig_tokens,
        compacted_tokens=total_compacted_tokens,
        was_compacted=True,
        strategy_tokens=final_strat_tokens,
        pitfall_tokens=final_pit_tokens,
        budget=max_tokens,
    )


def compact_retrieved_memories_list(
    memories: List[Dict[str, Any]],
    max_tokens: int = 800,
    encoding_name: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int, bool]:
    """
    Filters and compacts an ordered list of retrieved memory dictionaries to guarantee
    that total extracted strategy and pitfall text does not exceed max_tokens.
    Memories are processed in priority order (by composite_score descending).

    Returns:
        (compacted_memories, total_tokens, was_compacted)
    """
    if not memories or max_tokens <= 0:
        return [], 0, False

    retained: List[Dict[str, Any]] = []
    tokens_used = 0
    was_compacted = False

    for mem in memories:
        exp = mem.get("experience", {})
        strat = exp.get("strategyLesson") or exp.get("strategy_lesson") or ""
        pit = exp.get("pitfall") or ""

        exp_tokens = count_tokens(strat, encoding_name) + count_tokens(pit, encoding_name)
        remaining = max_tokens - tokens_used

        if remaining <= 0:
            was_compacted = True
            break

        if exp_tokens <= remaining:
            retained.append(mem)
            tokens_used += exp_tokens
        else:
            # Partially fit by compacting this memory
            comp_res = compact_memory_context(
                strat, pit, max_tokens=remaining, encoding_name=encoding_name
            )
            # Create shallow copy with compacted text
            compacted_mem = dict(mem)
            compacted_exp = dict(exp)
            if comp_res.positive_strategy:
                compacted_exp["strategyLesson"] = comp_res.positive_strategy
                compacted_exp["strategy_lesson"] = comp_res.positive_strategy
            else:
                compacted_exp["strategyLesson"] = None
                compacted_exp["strategy_lesson"] = None

            if comp_res.negative_pitfall:
                compacted_exp["pitfall"] = comp_res.negative_pitfall
            else:
                compacted_exp["pitfall"] = None

            compacted_mem["experience"] = compacted_exp
            compacted_mem["wasCompacted"] = True
            compacted_mem["compactedTokens"] = comp_res.compacted_tokens
            retained.append(compacted_mem)
            tokens_used += comp_res.compacted_tokens
            was_compacted = True
            break

    return retained, tokens_used, was_compacted
