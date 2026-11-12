"""
Drop-in Python SDK for Adaptive Experience Memory (AEMA).
Works identically on a developer's laptop (zero-config SQLite), inside async
voice/chat servers, or connected to a remote AEMA HTTP/Postgres backend.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from typing import Any, Coroutine, Dict, List, Optional, TypeVar

from aema._compat import import_pkg, resolve_db_path

_T = TypeVar("_T")


def _run_sync(coro: Coroutine[Any, Any, _T]) -> _T:
    """Execute an async coroutine safely from both sync scripts and running event loops."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class AdaptiveMemory:
    """
    Lightweight, plug-and-play experiential memory with Theorem 1 quarantine protection.

    Example:
        from aema import AdaptiveMemory

        mem = AdaptiveMemory(user_id="user_123")
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
        user_id: Optional[str] = None,
        quarantine_threshold: float = 0.35,
        initial_trust: float = 0.75,
    ) -> None:
        self.api_url = (api_url or os.environ.get("AEMA_API_URL") or "").strip().rstrip("/") or None
        self.api_key = (api_key or os.environ.get("AEMA_API_KEY") or "").strip() or None
        self.default_user_id = user_id
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
                resolved_path = db_path or resolve_db_path()
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

    def _resolve_user(self, user_id: Optional[str]) -> Optional[str]:
        return user_id if user_id is not None else self.default_user_id

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
        effective_user = self._resolve_user(user_id)

        if self.api_url:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.api_url}/api/v1/memories",
                    headers=self._headers(),
                    json={
                        "userId": effective_user,
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
                    "user_id": d.get("userId", effective_user),
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
            user_id=effective_user,
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
            "user_id": exp.user_id,
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
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve reliable, non-quarantined experiences scoped to `user_id` if provided."""
        trust_cutoff = self.quarantine_threshold if min_trust is None else float(min_trust)
        effective_user = self._resolve_user(user_id)

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
                if effective_user is not None:
                    payload["user_id"] = effective_user
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
                        "user_id": e.get("userId", e.get("user_id")),
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

        raw_hits = await self._store.search_similar(
            query_embedding=query_emb,
            domain=resolved_domain,
            top_k=max(top_k * 4, 20),
            user_id=effective_user,
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
                "user_id": exp.user_id,
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

    async def aforget(self, experience_id: str, hard_delete: bool = False) -> bool:
        """
        Remove or quarantine a memory entry.
        Set `hard_delete=True` for permanent GDPR/PII erasure; otherwise soft-quarantines.
        """
        if self.api_url:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.delete(
                    f"{self.api_url}/api/v1/memories/{experience_id}",
                    params={"hard_delete": "true"} if hard_delete else None,
                    headers=self._headers(),
                )
                if res.status_code == 404:
                    return False
                res.raise_for_status()
                return True

        if hard_delete:
            return await self._store.delete_experience(experience_id)

        exp = await self._store.get_experience(experience_id)
        if not exp:
            return False
        await self._store.update_trust(
            experience_id=experience_id,
            new_trust=0.0,
            reason="sdk_forget_soft_quarantine",
            status="deprecated",
        )
        return True

    async def arecover(
        self,
        experience_id: str,
        reason: str = "Developer requested probationary recovery",
    ) -> Dict[str, Any]:
        """
        Safely transition a quarantined (`deprecated`) memory into `candidate` probation.
        Honors AEMA's state machine invariant (deprecated -> candidate -> active).
        """
        audit_reason = reason if len(reason) >= 15 else f"{reason} (SDK recovery)"

        if self.api_url:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.api_url}/api/v1/memories/{experience_id}/recover",
                    headers=self._headers(),
                    json={"reason": audit_reason},
                )
                res.raise_for_status()
                d = res.json()
                return {
                    "id": d["id"],
                    "trust": float(d.get("trustScore", 0.5)),
                    "status": str(d.get("status", "candidate")),
                }

        recovered = await self._store.admin_recover_to_probation(
            experience_id=experience_id,
            reason=audit_reason,
            actor_id="sdk:developer",
        )
        return {
            "id": recovered.id,
            "trust": round(recovered.trust_score, 4),
            "status": recovered.status.value if hasattr(recovered.status, "value") else str(recovered.status),
        }

    async def alist(
        self,
        domain: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List stored memories with optional domain, status, and user_id filters."""
        effective_user = self._resolve_user(user_id)

        if self.api_url:
            import httpx

            params: Dict[str, Any] = {"limit": 200}
            if domain and domain != "all":
                params["domain"] = domain
            if status and status != "all":
                params["status"] = status
            if effective_user is not None:
                params["userId"] = effective_user

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    f"{self.api_url}/api/v1/memories",
                    headers=self._headers(),
                    params=params,
                )
                res.raise_for_status()
                items = res.json()
                return [
                    {
                        "id": e["id"],
                        "user_id": e.get("userId", e.get("user_id")),
                        "task": e.get("triggerCondition", e.get("trigger_condition", "")),
                        "strategy": e.get("strategyLesson", e.get("strategy_lesson", "")),
                        "pitfall": e.get("pitfall"),
                        "domain": e.get("taskDomain", e.get("task_domain", "general")),
                        "trust": float(e.get("trustScore", e.get("trust_score", 0.0))),
                        "status": str(e.get("status", "active")),
                    }
                    for e in items
                ]

        dom_mod = import_pkg("models.domain")
        resolved_domain = None
        if domain and domain != "all":
            try:
                resolved_domain = dom_mod.TaskDomain(domain.lower())
            except ValueError:
                resolved_domain = None

        resolved_status = None
        if status and status != "all":
            try:
                resolved_status = dom_mod.ExperienceStatus(status.lower())
            except ValueError:
                resolved_status = None

        exps = await self._store.list_experiences(
            domain=resolved_domain,
            status=resolved_status,
            user_id=effective_user,
        )
        return [
            {
                "id": e.id,
                "user_id": e.user_id,
                "task": e.trigger_condition,
                "strategy": e.strategy_lesson,
                "pitfall": e.pitfall,
                "domain": e.task_domain.value if hasattr(e.task_domain, "value") else str(e.task_domain),
                "trust": round(e.trust_score, 4),
                "status": e.status.value if hasattr(e.status, "value") else str(e.status),
            }
            for e in exps
        ]

    async def astatus(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Return memory store health counts and mean trust score."""
        items = await self.alist(user_id=user_id)
        active = [e for e in items if e["status"] == "active" and e["trust"] >= self.quarantine_threshold]
        quarantined = [e for e in items if e["status"] == "deprecated" or e["trust"] < self.quarantine_threshold]
        avg = sum(e["trust"] for e in items) / len(items) if items else 0.0
        backend = (
            "http"
            if self.api_url
            else ("postgres" if "Postgres" in type(self._store).__name__ else "sqlite")
        )
        return {
            "total": len(items),
            "active": len(active),
            "quarantined": len(quarantined),
            "average_trust": round(avg, 4),
            "backend": backend,
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
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return _run_sync(
            self.arecall(
                query=query,
                domain=domain,
                top_k=top_k,
                min_trust=min_trust,
                min_similarity=min_similarity,
                user_id=user_id,
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

    def forget(self, experience_id: str, hard_delete: bool = False) -> bool:
        return _run_sync(self.aforget(experience_id=experience_id, hard_delete=hard_delete))

    def recover(
        self,
        experience_id: str,
        reason: str = "Developer requested probationary recovery",
    ) -> Dict[str, Any]:
        return _run_sync(self.arecover(experience_id=experience_id, reason=reason))

    def list(
        self,
        domain: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return _run_sync(self.alist(domain=domain, status=status, user_id=user_id))

    def status(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        return _run_sync(self.astatus(user_id=user_id))

    def export_json(self, output_path: str, user_id: Optional[str] = None) -> int:
        """Export memories (optionally scoped to `user_id`) to a JSON file."""
        items = self.list(user_id=user_id)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(items, indent=2), encoding="utf-8")
        return len(items)

    def format_for_prompt(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 3,
        user_id: Optional[str] = None,
    ) -> str:
        """Retrieve verified memories and format them into a ready-to-inject prompt block."""
        hits = self.recall(query=query, domain=domain, top_k=top_k, user_id=user_id)
        if not hits:
            return ""
        lines = ["Verified Experiential Memory Guidance:"]
        for i, hit in enumerate(hits, 1):
            lines.append(f"{i}. [Trust {hit['trust']:.2f}] Strategy: {hit['strategy']}")
            if hit.get("pitfall"):
                lines.append(f"   Avoid: {hit['pitfall']}")
        return "\n".join(lines)
