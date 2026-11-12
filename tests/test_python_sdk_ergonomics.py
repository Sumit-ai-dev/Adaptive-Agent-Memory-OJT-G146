"""
Tests for the plug-and-play `AdaptiveMemory` Python SDK and pure-Python incomplete beta math.
"""

import pytest
import scipy.special as sc

from aema import AdaptiveMemory
from ai_service.trust_math import _betainc_pure


@pytest.mark.parametrize(
    "a,b,x",
    [
        (3.0, 1.0, 0.70),
        (3.0, 4.0, 0.70),
        (3.0, 5.0, 0.70),
        (10.0, 2.0, 0.85),
        (2.5, 6.5, 0.35),
        (1.0, 1.0, 0.50),
    ],
)
def test_pure_python_betainc_matches_scipy(a: float, b: float, x: float):
    assert abs(_betainc_pure(a, b, x) - float(sc.betainc(a, b, x))) < 1e-11


def test_adaptive_memory_sdk_lifecycle_and_quarantine(tmp_path):
    db_file = str(tmp_path / "voice_agent.db")
    mem = AdaptiveMemory(db_path=db_file)

    item = mem.remember(
        task="Voice TTS markdown formatting rule",
        strategy="Strip asterisks and backticks before sending text to TTS synthesizer.",
        pitfall="Do not speak raw markdown symbols aloud.",
        domain="general",
    )
    assert item["status"] == "active"
    assert item["trust"] == 0.75

    hits = mem.recall("Format reply for voice TTS model", min_similarity=0.05)
    assert len(hits) == 1
    assert hits[0]["id"] == item["id"]

    prompt_ctx = mem.format_for_prompt("Format reply for voice TTS model")
    assert "Strip asterisks" in prompt_ctx

    # 3 consecutive failures trigger Theorem 1 deterministic quarantine (0.75 -> 0.525 -> 0.3675 -> 0.2572 < 0.35)
    r1 = mem.feedback(item["id"], success=False)
    r2 = mem.feedback(item["id"], success=False)
    r3 = mem.feedback(item["id"], success=False)
    assert r1["quarantined"] is False
    assert r2["quarantined"] is False
    assert r3["quarantined"] is True
    assert r3["new_trust"] < 0.35
    assert r3["status"] == "deprecated"

    # Quarantined experience is automatically excluded from recall
    post_hits = mem.recall("Format reply for voice TTS model", min_similarity=0.05)
    assert post_hits == []

    stats = mem.status()
    assert stats["total"] == 1
    assert stats["quarantined"] == 1
    assert stats["active"] == 0


@pytest.mark.asyncio
async def test_adaptive_memory_sync_wrappers_safe_inside_running_event_loop(tmp_path):
    db_file = str(tmp_path / "async_voice.db")
    mem = AdaptiveMemory(db_path=db_file)

    # Calling sync methods inside a running FastAPI / Voice WebSocket event loop must not raise RuntimeError
    created = mem.remember("Keep spoken turns concise", domain="general")
    assert created["id"]

    hits = mem.recall("spoken turns", min_similarity=0.05)
    assert len(hits) == 1
