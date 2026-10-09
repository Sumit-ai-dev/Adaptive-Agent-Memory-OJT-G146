"""
Dual-Engine Memory Persistence Layer.
Implements SQLiteMemoryStore for zero-dependency reproducible offline benchmarking,
and SupabaseMemoryStore for production PostgreSQL pgvector cloud serving.
"""

from abc import ABC, abstractmethod
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ai_service.config import settings
from models.domain import ExperienceStatus, TaskDomain
from models.experience import Experience, TrustHistoryRecord, utc_now_iso

logger = logging.getLogger("ai_service.memory.store")


class BaseMemoryStore(ABC):
    """
    Abstract interface for Experience persistence.
    """

    @abstractmethod
    async def add_experience(self, exp: Experience) -> str:
        pass

    @abstractmethod
    async def get_experience(self, experience_id: str) -> Optional[Experience]:
        pass

    @abstractmethod
    async def update_trust(
        self,
        experience_id: str,
        new_trust: float,
        reason: Optional[str] = None,
        execution_id: Optional[str] = None,
        status: Optional[str] = None,
        binary_outcome: Optional[int] = None,
    ) -> TrustHistoryRecord:
        """
        F3: `binary_outcome` is the evaluator-produced task outcome (0 or 1).

        When supplied, this call counts as ONE task-level observation and increments
        `uses_count` plus exactly one of `successes_count` / `failures_count`.
        When None, the call is an administrative adjustment (e.g. manual deletion),
        not an observation, and no counter is touched.
        """
        pass

    @abstractmethod
    async def list_experiences(
        self,
        domain: Optional[TaskDomain] = None,
        status: Optional[ExperienceStatus] = None,
        min_trust: Optional[float] = None,
    ) -> List[Experience]:
        pass

    @abstractmethod
    async def search_similar(
        self, query_embedding: List[float], domain: Optional[TaskDomain] = None, top_k: int = 5
    ) -> List[Tuple[Experience, float]]:
        """
        Returns list of (Experience, cosine_similarity) tuples.
        """
        pass


class SQLiteMemoryStore(BaseMemoryStore):
    """
    SQLite-backed local vector store. Zero cloud infrastructure required.
    Uses numpy for vectorized cosine similarity search over stored embeddings.
    """

    def __init__(self, db_path: Optional[str] = None, auto_seed: bool = False):
        self.db_path = db_path or settings.SQLITE_DB_PATH
        self.auto_seed = auto_seed
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    task_domain TEXT NOT NULL,
                    trigger_condition TEXT NOT NULL,
                    strategy_lesson TEXT NOT NULL,
                    pitfall TEXT,
                    confidence REAL NOT NULL DEFAULT 0.85,
                    trust_score REAL NOT NULL DEFAULT 0.75,
                    uses_count INTEGER NOT NULL DEFAULT 0,
                    successes_count INTEGER NOT NULL DEFAULT 0,
                    failures_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    embedding TEXT,
                    source_task_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trust_history (
                    id TEXT PRIMARY KEY,
                    experience_id TEXT NOT NULL,
                    execution_id TEXT,
                    old_trust REAL NOT NULL,
                    new_trust REAL NOT NULL,
                    delta REAL NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(experience_id) REFERENCES experiences(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_domain_status ON experiences(task_domain, status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_trust ON experiences(trust_score DESC)")
            conn.commit()
            if self.auto_seed:
                self._seed_default_experiences(conn)

    def _seed_default_experiences(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM experiences WHERE id = 'exp-coding-001'")
        if cursor.fetchone()[0] > 0:
            return

        seeds = [
            (
                "exp-coding-001", None, "coding",
                "Recursive depth calculation in deeply nested tree structures",
                "Use iterative traversal with an explicit deque/stack to prevent RecursionError on deep trees",
                "Do not use default sys.setrecursionlimit above 5000 due to OS C-stack overflow risks",
                0.92, 0.88, 45, 42, 3, "active", None, None, "2026-08-20T14:20:00Z", "2026-09-08T11:45:00Z"
            ),
            (
                "exp-research-002", None, "research",
                "Multi-source factual claims in academic literature",
                "Cross-reference claims across at least 2 independent peer-reviewed primary citations before synthesizing conclusions",
                "Do not cite single secondary review summaries when empirical rate estimates diverge significantly",
                0.90, 0.94, 120, 114, 6, "active", None, None, "2026-08-15T10:00:00Z", "2026-09-09T18:30:00Z"
            ),
            (
                "exp-analysis-003", None, "analysis",
                "Time series financial forecasting with missing date intervals",
                "Resample time series with forward-fill strictly up to 2 intervals, then flag remaining gaps as NaN",
                "Do not apply linear interpolation across market holiday boundary discontinuities",
                0.85, 0.82, 30, 26, 4, "active", None, None, "2026-08-28T09:15:00Z", "2026-09-07T16:10:00Z"
            ),
            (
                "exp-candidate-004", None, "coding",
                "High-concurrency async SQLite connection pooling",
                "Enable WAL mode and use a dedicated write queue with short exponential backoffs",
                "Do not share raw SQLite connection objects across asyncio thread boundaries",
                0.80, 0.50, 5, 4, 1, "candidate", None, None, "2026-09-01T12:00:00Z", "2026-09-10T14:00:00Z"
            ),
            (
                "exp-deprecated-005", None, "coding",
                "HTML parsing from unstructured web pages",
                "Use complex regular expressions to extract nested div contents",
                "Regex parsing fails catastrophically on malformed or non-compliant HTML trees",
                0.30, 0.22, 18, 2, 16, "deprecated", None, None, "2026-08-10T08:00:00Z", "2026-09-10T20:15:00Z"
            ),
        ]

        try:
            from ai_service.embedder import local_embedder
        except Exception:
            local_embedder = None

        for item in seeds:
            id_, uid, domain, trig, strat, pit, conf, trust, uses, succ, fail, stat, emb, src, cat, uat = item
            if local_embedder is not None:
                try:
                    vec = local_embedder.embed_text(trig)
                    emb = json.dumps(vec)
                except Exception:
                    emb = None
            cursor.execute("""
                INSERT OR IGNORE INTO experiences (
                    id, user_id, task_domain, trigger_condition, strategy_lesson, pitfall,
                    confidence, trust_score, uses_count, successes_count, failures_count,
                    status, embedding, source_task_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (id_, uid, domain, trig, strat, pit, conf, trust, uses, succ, fail, stat, emb, src, cat, uat))
        conn.commit()

    async def add_experience(self, exp: Experience) -> str:
        # P0-3: Nothing in the pipeline previously populated `Experience.embedding`,
        # so every stored memory scored cosine 0.0 and was unreachable by retrieval.
        # Compute the embedding here -- the single write chokepoint for the store --
        # from `trigger_condition`, which is the field the retrieval query is matched
        # against. An explicitly supplied embedding is never overwritten.
        if exp.embedding is None:
            from ai_service.embedder import local_embedder

            exp.embedding = local_embedder.embed_text(exp.trigger_condition or "")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            embedding_json = json.dumps(exp.embedding) if exp.embedding is not None else None
            cursor.execute("""
                INSERT OR REPLACE INTO experiences (
                    id, user_id, task_domain, trigger_condition, strategy_lesson, pitfall,
                    confidence, trust_score, uses_count, successes_count, failures_count,
                    status, embedding, source_task_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp.id, exp.user_id, exp.task_domain.value if isinstance(exp.task_domain, TaskDomain) else exp.task_domain,
                exp.trigger_condition, exp.strategy_lesson, exp.pitfall,
                exp.confidence, exp.trust_score, exp.uses_count, exp.successes_count, exp.failures_count,
                exp.status.value if isinstance(exp.status, ExperienceStatus) else exp.status,
                embedding_json, exp.source_task_id, exp.created_at, exp.updated_at,
            ))
            conn.commit()
            return exp.id

    async def get_experience(self, experience_id: str) -> Optional[Experience]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiences WHERE id = ?", (experience_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_experience(row)

    async def update_trust(
        self,
        experience_id: str,
        new_trust: float,
        reason: Optional[str] = None,
        execution_id: Optional[str] = None,
        status: Optional[str] = None,
        binary_outcome: Optional[int] = None,
    ) -> TrustHistoryRecord:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT trust_score, successes_count, failures_count, uses_count, status FROM experiences WHERE id = ?", (experience_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Experience '{experience_id}' not found.")

            old_trust = float(row["trust_score"])
            delta = float(new_trust - old_trust)

            if status is not None:
                new_status = status
            elif new_trust < settings.THETA_CUTOFF:
                new_status = ExperienceStatus.DEPRECATED.value
            elif row["status"] == ExperienceStatus.CANDIDATE.value and new_trust >= settings.RELIABILITY_THRESHOLD:
                new_status = ExperienceStatus.ACTIVE.value
            else:
                new_status = row["status"]

            # F3: evidence counters are driven by the EVALUATOR-produced outcome, never
            # by the sign of the trust delta.
            #
            # The previous rule was `success_inc = 1 if delta >= 0 else 0`. Under A-EMA's
            # neutral branch delta = 0.20*(R - S), so "success" meant "the reward exceeded
            # the memory's own current trust score" -- a self-referential, moving target.
            # It also scored delta == 0 as a success, and it coupled the Bernoulli record
            # to the trust mechanism, which would make any later mechanism swap silently
            # reinterpret all historical counters.
            #
            # binary_outcome is None  -> administrative adjustment, not an observation:
            #                            trust/status change only, no counter touched.
            # binary_outcome in {0,1} -> exactly one task-level observation.
            #                            Guarantees successes + failures == uses.
            if binary_outcome is None:
                uses_inc = 0
                success_inc = 0
                failure_inc = 0
            else:
                outcome = int(binary_outcome)
                if outcome not in (0, 1):
                    raise ValueError(f"binary_outcome must be 0 or 1, got {binary_outcome!r}")
                uses_inc = 1
                success_inc = 1 if outcome == 1 else 0
                failure_inc = 1 - success_inc

            now = utc_now_iso()

            cursor.execute("""
                UPDATE experiences SET
                    trust_score = ?,
                    status = ?,
                    uses_count = uses_count + ?,
                    successes_count = successes_count + ?,
                    failures_count = failures_count + ?,
                    updated_at = ?
                WHERE id = ?
            """, (new_trust, new_status, uses_inc, success_inc, failure_inc, now, experience_id))

            record = TrustHistoryRecord(
                experience_id=experience_id,
                execution_id=execution_id,
                old_trust=old_trust,
                new_trust=new_trust,
                delta=delta,
                reason=reason,
                created_at=now,
            )

            cursor.execute("""
                INSERT INTO trust_history (id, experience_id, execution_id, old_trust, new_trust, delta, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id, record.experience_id, record.execution_id,
                record.old_trust, record.new_trust, record.delta,
                record.reason, record.created_at,
            ))
            conn.commit()
            return record

    async def list_experiences(
        self,
        domain: Optional[TaskDomain] = None,
        status: Optional[ExperienceStatus] = None,
        min_trust: Optional[float] = None,
    ) -> List[Experience]:
        query = "SELECT * FROM experiences WHERE 1=1"
        params: List[Any] = []
        if domain:
            query += " AND task_domain = ?"
            params.append(domain.value if isinstance(domain, TaskDomain) else domain)
        if status:
            query += " AND status = ?"
            params.append(status.value if isinstance(status, ExperienceStatus) else status)
        if min_trust is not None:
            query += " AND trust_score >= ?"
            params.append(min_trust)
        query += " ORDER BY trust_score DESC, updated_at DESC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_experience(r) for r in cursor.fetchall()]

    async def search_similar(
        self, query_embedding: List[float], domain: Optional[TaskDomain] = None, top_k: int = 5
    ) -> List[Tuple[Experience, float]]:
        experiences = await self.list_experiences(domain=domain)
        if not experiences:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-6:
            return [(e, 0.0) for e in experiences[:top_k]]

        scored: List[Tuple[Experience, float]] = []
        for exp in experiences:
            if not exp.embedding:
                scored.append((exp, 0.0))
                continue
            e_vec = np.array(exp.embedding, dtype=np.float32)
            e_norm = np.linalg.norm(e_vec)
            if e_norm < 1e-6:
                scored.append((exp, 0.0))
                continue
            sim = float(np.dot(q_vec, e_vec) / (q_norm * e_norm))
            scored.append((exp, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _row_to_experience(self, row: sqlite3.Row) -> Experience:
        embedding = json.loads(row["embedding"]) if row["embedding"] else None
        return Experience(
            id=row["id"],
            user_id=row["user_id"],
            task_domain=TaskDomain(row["task_domain"]) if row["task_domain"] in [d.value for d in TaskDomain] else TaskDomain.GENERAL,
            trigger_condition=row["trigger_condition"],
            strategy_lesson=row["strategy_lesson"],
            pitfall=row["pitfall"],
            confidence=float(row["confidence"]),
            trust_score=float(row["trust_score"]),
            uses_count=int(row["uses_count"]),
            successes_count=int(row["successes_count"]),
            failures_count=int(row["failures_count"]),
            status=ExperienceStatus(row["status"]) if row["status"] in [s.value for s in ExperienceStatus] else ExperienceStatus.ACTIVE,
            embedding=embedding,
            source_task_id=row["source_task_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


# Global default store instance
memory_store = SQLiteMemoryStore()
