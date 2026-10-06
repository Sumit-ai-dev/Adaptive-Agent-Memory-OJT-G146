"""
Policy registry -- name -> constructor.

Exists so a run manifest can record a policy by name and a replay can reconstruct it.
Registration is NOT endorsement: a registered policy gets no privileged code path and
no default status.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from ai_service.trust.aema import AEMAPolicy, StaticTrustPolicy
from ai_service.trust.base import TrustPolicy

_REGISTRY: Dict[str, Callable[..., TrustPolicy]] = {
    AEMAPolicy.name: AEMAPolicy,
    StaticTrustPolicy.name: StaticTrustPolicy,
}


def register_policy(name: str, factory: Callable[..., TrustPolicy]) -> None:
    if name in _REGISTRY:
        raise ValueError(f"policy '{name}' is already registered")
    _REGISTRY[name] = factory


def build_policy(name: str, **params: Any) -> TrustPolicy:
    if name not in _REGISTRY:
        raise KeyError(f"unknown policy '{name}'; registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name](**params)


def available_policies() -> List[str]:
    return sorted(_REGISTRY)
