"""
Pluggable trust/reuse policy layer.

The architecture is stable; the mechanism is experimentally replaceable. Step 1 ships
the abstraction plus the existing A-EMA behind it. No new mechanism is introduced.
"""

from ai_service.trust.aema import AEMAPolicy, StaticTrustPolicy
from ai_service.trust.base import (
    Decision,
    Observation,
    PolicyContext,
    PolicyState,
    TrustPolicy,
)
from ai_service.trust.registry import available_policies, build_policy, register_policy

__all__ = [
    "TrustPolicy",
    "PolicyState",
    "Observation",
    "PolicyContext",
    "Decision",
    "AEMAPolicy",
    "StaticTrustPolicy",
    "build_policy",
    "register_policy",
    "available_policies",
]
