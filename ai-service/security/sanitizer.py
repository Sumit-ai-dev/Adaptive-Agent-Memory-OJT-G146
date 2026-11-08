"""
Prompt Injection Sanitization and Bilateral Constraint Formatting.
Implements XML delimiter encapsulation and control token escaping (OWASP LLM01 defense).
"""

from __future__ import annotations

import html
import re
from typing import List, Optional, Tuple

# Markers commonly used in prompt injection attempts to forge system instructions
INJECTION_MARKERS = [
    r"\[(?:SYSTEM|INSTRUCTION|ASSISTANT|USER)\]",
    r"<\/?(?:system|instruction|admin|prompt)>",
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"disregard\s+(?:all\s+)?prior\s+guidelines",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
]

INJECTION_REGEX = re.compile("|".join(INJECTION_MARKERS), re.IGNORECASE)

# Case-insensitive, whitespace-tolerant regex matching boundary tags
BOUNDARY_TAG_RE = re.compile(
    r"<\s*(/?)\s*(experiential_strategy|prohibited_pitfall)\s*>",
    re.IGNORECASE,
)


def _escape_boundary_tag(match: re.Match) -> str:
    """Helper callback to escape matched boundary tags."""
    closing_slash = match.group(1) or ""
    tag_name = match.group(2).lower()
    return f"&lt;{closing_slash}{tag_name}&gt;"


def detect_prompt_injection_heuristic(text: str) -> Tuple[bool, Optional[str]]:
    """
    Scans input or memory strings for common heuristic prompt injection patterns.
    Returns (detected, matched_pattern).
    """
    if not text:
        return False, None
    m = INJECTION_REGEX.search(text)
    if m:
        return True, m.group(0)
    return False, None


def sanitize_memory_content(text: str) -> str:
    """
    Sanitizes untrusted memory strings to prevent prompt injection and delimiter breakout:
    1. Neutralizes common prompt injection directives (e.g. 'ignore previous instructions').
    2. Escapes custom XML wrapper tags regardless of casing or inner whitespace.
    3. Strips dangerous raw null bytes or ASCII control characters.
    """
    if not text:
        return ""

    # Neutralize heuristic prompt injection directives in stored memory text
    sanitized = INJECTION_REGEX.sub("[FILTERED_PROMPT_INJECTION]", text)

    # Escape custom XML wrapper tags regardless of casing or inner whitespace
    sanitized = BOUNDARY_TAG_RE.sub(_escape_boundary_tag, sanitized)

    # Strip dangerous raw null bytes or control characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)
    return sanitized.strip()


def format_bilateral_constraints(
    positive_strategy: Optional[str] = None,
    negative_pitfall: Optional[str] = None,
) -> List[str]:
    """
    Wraps experiential strategies and anti-pattern constraints into
    isolated XML boundaries, neutralizing injection breakout attempts.
    Treats memory text strictly as passive observational context.
    """
    constraints: List[str] = []

    if positive_strategy and positive_strategy.strip():
        safe_strategy = sanitize_memory_content(positive_strategy)
        constraints.append(
            f"<experiential_strategy>\n{safe_strategy}\n</experiential_strategy>"
        )

    if negative_pitfall and negative_pitfall.strip():
        safe_pitfall = sanitize_memory_content(negative_pitfall)
        constraints.append(
            f"<prohibited_pitfall>\n{safe_pitfall}\n</prohibited_pitfall>"
        )

    return constraints
