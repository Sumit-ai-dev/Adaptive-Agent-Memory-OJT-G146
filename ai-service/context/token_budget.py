"""
Token Budgeting, Counting, and Cost Estimation Engine.
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)

Provides:
- Deterministic token counting matching BPE tokenization (tiktoken with robust fallback)
- Safe token truncation respecting word and syntax boundaries
- Model provider pricing lookup and USD cost tracking
"""

from __future__ import annotations

import logging
import math
import re
from typing import Dict, Optional, Tuple

logger = logging.getLogger("ai_service.context.token_budget")

try:
    import tiktoken
except ImportError:
    tiktoken = None

# Default rates per 1,000,000 tokens (USD): (prompt_rate, completion_rate)
MODEL_PRICING_PER_MILLION: Dict[str, Tuple[float, float]] = {
    # Groq / Open Source Hosted
    "openai/gpt-oss-120b": (0.59, 0.79),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "mixtral-8x7b-32768": (0.24, 0.24),
    "gemma2-9b-it": (0.20, 0.20),
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    # Google Gemini
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-2.0-flash-exp": (0.00, 0.00),
    # Anthropic
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3-opus": (15.00, 75.00),
    # Local & Mock
    "mock": (0.00, 0.00),
    "ollama": (0.00, 0.00),
}

DEFAULT_FALLBACK_RATES: Tuple[float, float] = (0.50, 1.50)


def _bpe_fallback_count(text: str) -> int:
    """
    Deterministic token estimation that closely tracks BPE tokenizers without tiktoken.
    Accurately scores code, JSON, and multilingual Unicode text (including CJK and accented words)
    by treating individual syntax symbols, numbers, and subwords as distinct tokens.
    """
    if not text:
        return 0

    # Token patterns: Unicode word runs, digits, individual symbols/punctuation, and whitespace
    tokens = re.findall(r"[^\W\d_]+|\d+|[^\w\s]|\s+", text, re.UNICODE)
    count = 0

    for token in tokens:
        if token.isspace():
            # In BPE, newlines are usually 1 token each; 2-4 spaces constitute 1 token
            newlines = token.count("\n")
            spaces = len(token) - newlines
            count += newlines + max(0, (spaces + 2) // 4)
        elif token.isdigit():
            # Numbers in BPE are typically 1-3 digits per token
            count += max(1, (len(token) + 2) // 3)
        elif token.isalpha():
            # Handle CJK ideographs (each CJK char is typically 1-2 BPE tokens)
            cjk_chars = sum(
                1 for c in token
                if "\u4e00" <= c <= "\u9fff"
                or "\u3040" <= c <= "\u30ff"
                or "\uac00" <= c <= "\ud7af"
            )
            non_cjk_len = len(token) - cjk_chars
            count += cjk_chars + (max(1, (non_cjk_len + 3) // 4) if non_cjk_len > 0 else 0)
        else:
            # Punctuation and symbols (JSON brackets, colons, arithmetic) are individual tokens
            count += len(token)

    return max(1, count)


def count_tokens(text: str, encoding_name: Optional[str] = "cl100k_base") -> int:
    """
    Counts the number of tokens in a string using tiktoken if available,
    falling back to deterministic BPE-approximating segmentation.
    """
    if not text:
        return 0

    if tiktoken is not None:
        try:
            enc = tiktoken.get_encoding(encoding_name or "cl100k_base")
            return len(enc.encode(text, disallowed_special=()))
        except Exception:
            pass

    return _bpe_fallback_count(text)


def estimate_tokens_fast(text: str) -> int:
    """
    High-speed heuristic token counter for inner loops and tight latency paths.
    """
    return count_tokens(text)


def truncate_text_to_tokens(
    text: str,
    max_tokens: int,
    encoding_name: Optional[str] = "cl100k_base",
    suffix: str = " [...]",
) -> Tuple[str, int]:
    """
    Deterministically truncates text so that its token count is strictly <= max_tokens.
    Preserves word boundaries and appends suffix indicator when truncated.

    Returns:
        (truncated_text, token_count)
    """
    if max_tokens <= 0 or not text:
        return "", 0

    current_tokens = count_tokens(text, encoding_name=encoding_name)
    if current_tokens <= max_tokens:
        return text, current_tokens

    suffix_tokens = count_tokens(suffix, encoding_name=encoding_name)

    # If the budget is too small to even accommodate the suffix, truncate text directly without suffix
    if max_tokens <= suffix_tokens:
        candidate = text
        while candidate and count_tokens(candidate, encoding_name=encoding_name) > max_tokens:
            candidate = candidate[:-1]
        final_count = count_tokens(candidate, encoding_name=encoding_name)
        return candidate, final_count

    # Use tiktoken exact slicing if available
    if tiktoken is not None:
        try:
            enc = tiktoken.get_encoding(encoding_name or "cl100k_base")
            effective_budget = max(1, max_tokens - suffix_tokens)
            encoded = enc.encode(text, disallowed_special=())
            if len(encoded) > effective_budget:
                truncated_text = enc.decode(encoded[:effective_budget]).rstrip() + suffix
                final_count = count_tokens(truncated_text, encoding_name=encoding_name)
                # Guarantee absolute cap
                while final_count > max_tokens and effective_budget > 1:
                    effective_budget -= 1
                    truncated_text = enc.decode(encoded[:effective_budget]).rstrip() + suffix
                    final_count = count_tokens(truncated_text, encoding_name=encoding_name)
                if final_count <= max_tokens:
                    return truncated_text, final_count
        except Exception:
            pass

    # Deterministic fallback word-level search
    words = text.split(" ")
    low = 0
    high = len(words)
    best_candidate = ""

    while low <= high:
        mid = (low + high) // 2
        candidate = " ".join(words[:mid]).rstrip() + suffix
        cand_tokens = count_tokens(candidate, encoding_name=encoding_name)

        if cand_tokens <= max_tokens:
            best_candidate = candidate
            low = mid + 1
        else:
            high = mid - 1

    if not best_candidate:
        # Fallback character slice reserving room for suffix
        best_candidate = text
        while best_candidate and count_tokens(best_candidate + suffix, encoding_name=encoding_name) > max_tokens:
            best_candidate = best_candidate[:-1]
        best_candidate = (best_candidate.rstrip() + suffix) if best_candidate else ""

    # Strict invariant check: ensure result NEVER exceeds max_tokens under any tokenization
    while best_candidate and count_tokens(best_candidate, encoding_name=encoding_name) > max_tokens:
        best_candidate = best_candidate[:-1].rstrip()

    final_count = count_tokens(best_candidate, encoding_name=encoding_name)
    return best_candidate, final_count


def calculate_token_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    Computes total task execution cost in USD based on provider and model rates.
    """
    prov_clean = (provider or "").lower().strip()
    mod_clean = (model or "").lower().strip()

    if prov_clean in ("mock", "ollama") or "mock" in mod_clean:
        return 0.0

    prompt_rate, completion_rate = DEFAULT_FALLBACK_RATES

    # Check direct model name
    for known_model, rates in MODEL_PRICING_PER_MILLION.items():
        if known_model == mod_clean or known_model.split("/")[-1] == mod_clean:
            prompt_rate, completion_rate = rates
            break
    else:
        # Match by provider category
        if "groq" in prov_clean:
            prompt_rate, completion_rate = (0.59, 0.79)
        elif "gemini" in prov_clean:
            prompt_rate, completion_rate = (0.10, 0.40)
        elif "openai" in prov_clean:
            prompt_rate, completion_rate = (0.50, 1.50)
        elif "anthropic" in prov_clean:
            prompt_rate, completion_rate = (3.00, 15.00)

    prompt_cost = (max(0, prompt_tokens) / 1_000_000.0) * prompt_rate
    completion_cost = (max(0, completion_tokens) / 1_000_000.0) * completion_rate
    total_cost = prompt_cost + completion_cost

    return round(total_cost, 6)
