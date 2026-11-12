"""
Drop-in Python SDK for Adaptive Experience Memory (AEMA).
Works identically on a developer's laptop (zero-config SQLite), inside async
voice/chat servers, or connected to a remote AEMA HTTP/Postgres backend.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from typing import Any, Coroutine, Dict, List, Optional, TypeVar

from aema._compat import import_pkg

_T = TypeVar("_T")


def _run_sync(coro: Coroutine[Any, Any, _T]) -> _T:
    """Execute an async coroutine safely from both sync scripts and running event loops."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _default_db_path() -> str:
    env_path = os.environ.get("AEMA_DB_PATH") or os.environ.get("SQLITE_DB_PATH")
    if env_path:
        return env_path
    return str(Path.home() / ".aema" / "memory.db")


class AdaptiveMemory:
    """
    Lightweight, plug-and-play experiential memory with Theorem 1 quarantine protection.

    Example:
        from aema import AdaptiveMemory

        mem = AdaptiveMemory()
        item = mem.remember("Voice agent shouldn't read markdown symbols aloud")
        hits = mem.recall("Format reply for voice TTS")
        mem.feedback(item["id"], success=True)
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        database_url: Optional[str] = None,
        quarantine_threshold: float = 0.35,
        initial_trust: float = 0.75,
    ) -> None:
        self.api_url = (api_url or os.environ.get("AEMA_API_URL") or "").strip().rstrip("/") or None
        self.api_key = (api_key or os.environ.get("AEMA_API_KEY") or "").strip() or None
        self.quarantine_threshold = quarantine_threshold
        self.initial_trust = initial_trust
        self._store = None

        if not self.api_url:
            store_mod = import_pkg("ai_service.memory.store")
            if database_url:
                self._store = store_mod.get_memory_store(
                    engine="postgres",
                    database_url=database_url,
                    auto_seed=False,
                )
            else:
                resolved_path = db_path or _default_db_path()
                self._store = store_mod.get_memory_store(
                    engine="sqlite",
                    db_path=resolved_path,
                    auto_seed=False,
                )

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        return headers

    def _embed(self, text: str) -> tuple[List[float], bool]:
        embedder_mod = import_pkg("ai_service.embedder")
        vec = embedder_mod.local_embedder.embed_text(text)
        using_neural = embedder_mod.local_embedder._model is not None
        return vec, using_neural

    # ── Async API ────────────────────────────────────────────────────────────

    async def aremember(
        self,
        task: str,
        strategy: Optional[str] = None,
        pitfall: Optional[str] = None,
        domain: str = "general",
        initial_trust: Optional[float] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store a reusable lesson/strategy in AEMA memory."""
        trust = self.initial_trust if initial_trust is None else max(0.0, min(1.0, float(initial_trust)))
        effective_strategy = strategy or task

        if self.api_url:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.api_url}/api/v1/memories",
                    headers=self._headers(),
                    json={
                        "taskDomain": domain,
                        "triggerCondition": task,
                        "strategyLesson": effective_strategy,
                        "pitfall": pitfall,
                        "trustScore": trust,
                        "confidence": trust,
                    },
                )
                res.raise_for_status()
                d = res.json()
                return {
                    "id": d["id"],
                    "task": d.get("triggerCondition", task),
                    "strategy": d.get("strategyLesson", effective_strategy),
                    "pitfall": d.get("pitfall"),
                    "domain": d.get("taskDomain", domain),
                    "trust": float(d.get("trustScore", trust)),
                    "status": str(d.get("status", "candidate")),
                }

        dom_mod = import_pkg("models.domain")
        exp_mod = import_pkg("models.experience")

        try:
            resolved_domain = dom_mod.TaskDomain(domain.lower())
        except ValueError:
            resolved_domain = dom_mod.TaskDomain.GENERAL

        embedding, _ = self._embed(f"{task} {effective_strategy}")
        exp = exp_mod.Experience(
            user_id=user_id,
            task_domain=resolved_domain,
            trigger_condition=task,
            strategy_lesson=effective_strategy,
            pitfall=pitfall,
            confidence=trust,
            trust_score=trust,
            status=dom_mod.ExperienceStatus.ACTIVE,
            embedding=embedding,
        )
        await self._store.add_experience(exp)
        return {
            "id": exp.id,
            "task": exp.trigger_condition,
            "strategy": exp.strategy_lesson,
            "pitfall": exp.pitfall,
            "domain": exp.task_domain.value,
            "trust": exp.trust_score,
            "status": exp.status.value,
        }

    async def arecall(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5,
        min_trust: Optional[float] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve reliable, non-quarantined experiences relevant to `query`."""
        trust_cutoff = self.quarantine_threshold if min_trust is None else float(min_trust)

        if self.api_url:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                payload: Dict[str, Any] = {
                    "query": query,
                    "top_k": top_k,
                    "min_trust": trust_cutoff,
                }
                if min_similarity is not None:
                    payload["min_similarity"] = min_similarity
                if domain and domain != "all":
                    payload["domain"] = domain
                res = await client.post(
                    f"{self.api_url}/api/v1/memories/search",
                    headers=self._headers(),
                    json=payload,
                )
                res.raise_for_status()
                matches = res.json()
                out = []
                for m in matches:
                    e = m.get("experience", m)
                    sim = float(m.get("similarity", 0.0))
                    tr = float(e.get("trustScore", e.get("trust_score", 0.0)))
                    out.append({
                        "id": e["id"],
                        "task": e.get("triggerCondition", e.get("trigger_condition", "")),
                        "strategy": e.get("strategyLesson", e.get("strategy_lesson", "")),
                        "pitfall": e.get("pitfall"),
                        "domain": e.get("taskDomain", e.get("task_domain", "general")),
                        "trust": tr,
                        "similarity": round(sim, 4),
                        "score": round(float(m.get("compositeScore", 0.70 * sim + 0.30 * tr)), 4),
                        "status": str(e.get("status", "active")),
                    })
                return out

        dom_mod = import_pkg("models.domain")
        resolved_domain = None
        if domain and domain != "all":
            try:
                resolved_domain = dom_mod.TaskDomain(domain.lower())
            except ValueError:
                resolved_domain = None

        query_emb, using_neural = self._embed(query)
        sim_cutoff = (
            float(min_similarity)
            if min_similarity is not None
            else (0.45 if using_neural else 0.12)
        )

        # Fetch generous candidate pool, then enforce Theorem 1 + composite ranking
        raw_hits = await self._store.search_similar(
            query_embedding=query_emb,
            domain=resolved_domain,
            top_k=max(top_k * 4, 20),
        )
        ranked: List[Dict[str, Any]] = []
        for exp, sim in raw_hits:
            status_val = exp.status.value if hasattr(exp.status, "value") else str(exp.status)
            if status_val != "active":
                continue
            if exp.trust_score < trust_cutoff or sim < sim_cutoff:
                continue
            composite = 0.70 * sim + 0.30 * exp.trust_score
            ranked.append({
                "id": exp.id,
                "task": exp.trigger_condition,
                "strategy": exp.strategy_lesson,
                "pitfall": exp.pitfall,
                "domain": exp.task_domain.value if hasattr(exp.task_domain, "value") else str(exp.task_domain),
                "trust": round(exp.trust_score, 4),
                "similarity": round(sim, 4),
                "score": round(composite, 4),
                "status": status_val,
            })

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_k]

    async def afeedback(
        self,
        experience_id: str,
        success: Optional[bool] = None,
        reward: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Update memory trust via Asymmetric EMA; quarantines below threshold."""
        if reward is None:
            if success is None:
                raise ValueError("Provide either `success=True/False` or numeric `reward`.")
            reward = 1.0 if success else 0.0

        if self.api_url:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.api_url}/api/v1/memories/{experience_id}/feedback",
                    headers=self._headers(),
                    json={
                        "outcome": "success" if reward >= 0.8 else "failure",
                        "outcome_score": reward,
                    },
                )
                res.raise_for_status()
                data = res.json()
                tu = data.get("trustUpdate", {})
                exp = data.get("experience", {})
                new_trust = float(tu.get("newScore", exp.get("trustScore", 0.0)))
                return {
                    "id": experience_id,
                    "previous_trust": float(tu.get("oldScore", 0.0)),
                    "new_trust": new_trust,
                    "delta": float(tu.get("delta", 0.0)),
                    "quarantined": new_trust < self.quarantine_threshold,
                    "status": str(exp.get("status", "deprecated" if new_trust < self.quarantine_threshold else "active")),
                }

        exp = await self._store.get_experience(experience_id)
        if not exp:
            raise KeyError(f"Experience '{experience_id}' not found.")

        trust_mod = import_pkg("ai_service.trust_math")
        old_trust = exp.trust_score
        new_trust = trust_mod.asymmetric_ema_update(old_trust=old_trust, outcome_score=reward)
        quarantined = new_trust < self.quarantine_threshold
        new_status = "deprecated" if quarantined else "active"
        bin_outcome = 1 if reward >= 0.80 else (0 if reward <= 0.30 else None)

        await self._store.update_trust(
            experience_id=experience_id,
            new_trust=new_trust,
            reason=f"sdk_feedback(reward={reward:.2f})",
            status=new_status,
            binary_outcome=bin_outcome,
        )
        return {
            "id": experience_id,
            "previous_trust": round(old_trust, 4),
            "new_trust": round(new_trust, 4),
            "delta": round(new_trust - old_trust, 4),
            "quarantined": quarantined,
            "status": new_status,
        }

    async def astatus(self) -> Dict[str, Any]:
        """Return memory store health counts and mean trust score."""
        if self.api_url:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    f"{self.api_url}/api/v1/memories",
                    headers=self._headers(),
                    params={"limit": 200},
                )
                res.raise_for_status()
                items = res.json()
                active = [e for e in items if e.get("status") == "active" and e.get("trustScore", 0) >= self.quarantine_threshold]
                quarantined = [e for e in items if e.get("status") == "deprecated" or e.get("trustScore", 1) < self.quarantine_threshold]
                avg = sum(float(e.get("trustScore", 0)) for e in items) / len(items) if items else 0.0
                return {
                    "total": len(items),
                    "active": len(active),
                    "quarantined": len(quarantined),
                    "average_trust": round(avg, 4),
                    "backend": "http",
                }

        exps = await self._store.list_experiences()
        active = [e for e in exps if (e.status.value if hasattr(e.status, "value") else e.status) == "active" and e.trust_score >= self.quarantine_threshold]
        quarantined = [e for e in exps if (e.status.value if hasattr(e.status, "value") else e.status) == "deprecated" or e.trust_score < self.quarantine_threshold]
        avg = sum(e.trust_score for e in exps) / len(exps) if exps else 0.0
        return {
            "total": len(exps),
            "active": len(active),
            "quarantined": len(quarantined),
            "average_trust": round(avg, 4),
            "backend": "postgres" if "Postgres" in type(self._store).__name__ else "sqlite",
        }

    # ── Sync Wrappers (Safe inside both sync scripts and running async loops) ──

    def remember(
        self,
        task: str,
        strategy: Optional[str] = None,
        pitfall: Optional[str] = None,
        domain: str = "general",
        initial_trust: Optional[float] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return _run_sync(
            self.aremember(
                task=task,
                strategy=strategy,
                pitfall=pitfall,
                domain=domain,
                initial_trust=initial_trust,
                user_id=user_id,
            )
        )

    def recall(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5,
        min_trust: Optional[float] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        return _run_sync(
            self.arecall(
                query=query,
                domain=domain,
                top_k=top_k,
                min_trust=min_trust,
                min_similarity=min_similarity,
            )
        )

    def feedback(
        self,
        experience_id: str,
        success: Optional[bool] = None,
        reward: Optional[float] = None,
    ) -> Dict[str, Any]:
        return _run_sync(
            self.afeedback(experience_id=experience_id, success=success, reward=reward)
        )

    def status(self) -> Dict[str, Any]:
        return _run_sync(self.astatus())

    def format_for_prompt(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 3,
    ) -> str:
        """Retrieve verified memories and format them into a ready-to-inject prompt block."""
        hits = self.recall(query=query, domain=domain, top_k=top_k)
        if not hits:
            return ""
        lines = ["Verified Experiential Memory Guidance:"]
        for i, hit in enumerate(hits, 1):
            lines.append(f"{i}. [Trust {hit['trust']:.2f}] Strategy: {hit['strategy']}")
            if hit.get("pitfall"):
                lines.append(f"   Avoid: {hit['pitfall']}")
        return "\n".join(lines)
