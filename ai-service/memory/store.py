"""
Dual-Engine Memory Persistence Layer.
Implements SQLiteMemoryStore for zero-dependency reproducible offline benchmarking,
and SupabaseMemoryStore for production PostgreSQL pgvector cloud serving.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
import httpx
import numpy as np

try:
    import asyncpg
    from pgvector.asyncpg import register_vector
    HAS_POSTGRES = True
except ImportError:
    asyncpg = None
    register_vector = None
    HAS_POSTGRES = False

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


class PostgresMemoryStore(BaseMemoryStore):
    """
    Production-grade PostgreSQL memory store with native pgvector HNSW indexing.
    Connects via asyncpg and performs sub-millisecond semantic retrieval using (<=>).
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        auto_seed: bool = False,
        pool: Optional[Any] = None,
    ):
        if not HAS_POSTGRES:
            raise RuntimeError(
                "PostgreSQL support requires 'asyncpg' and 'pgvector'. "
                "Install them with `pip install asyncpg pgvector`."
            )
        self.database_url = database_url or settings.DATABASE_URL or os.getenv("DATABASE_URL")
        self.auto_seed = auto_seed
        self._pool = pool
        self._initialized = False

    async def _get_pool(self) -> Any:
        if self._pool is None:
            if not self.database_url:
                raise ValueError("PostgresMemoryStore requires a valid database_url or DATABASE_URL env var")

            async def init_connection(conn):
                if register_vector:
                    await register_vector(conn)

            self._pool = await asyncpg.create_pool(
                dsn=self.database_url,
                init=init_connection,
                min_size=1,
                max_size=10,
            )
        if not self._initialized:
            await self.init_db()
            self._initialized = True
        return self._pool

    async def init_db(self) -> None:
        """Initializes pgvector extension, schema tables, and HNSW cosine index."""
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    task_domain TEXT NOT NULL,
                    trigger_condition TEXT NOT NULL,
                    strategy_lesson TEXT NOT NULL,
                    pitfall TEXT,
                    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.85,
                    trust_score DOUBLE PRECISION NOT NULL DEFAULT 0.75,
                    uses_count INTEGER NOT NULL DEFAULT 0,
                    successes_count INTEGER NOT NULL DEFAULT 0,
                    failures_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    embedding vector(384),
                    source_task_id TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trust_history (
                    id TEXT PRIMARY KEY,
                    experience_id TEXT NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
                    execution_id TEXT,
                    old_trust DOUBLE PRECISION NOT NULL,
                    new_trust DOUBLE PRECISION NOT NULL,
                    delta DOUBLE PRECISION NOT NULL,
                    reason TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_exp_domain_status ON experiences(task_domain, status);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_exp_trust ON experiences(trust_score DESC);")
            try:
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pg_exp_embedding ON experiences
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)
            except Exception as e:
                logger.warning(f"Could not build HNSW index (fallback to exact search): {e}")

            if self.auto_seed:
                await self._seed_default_experiences(conn)

    async def _seed_default_experiences(self, conn: Any) -> None:
        count = await conn.fetchval("SELECT COUNT(*) FROM experiences WHERE id = 'exp-coding-001'")
        if count and count > 0:
            return

        seeds = [
            (
                "exp-coding-001", None, "coding",
                "Recursive depth calculation in deeply nested tree structures",
                "Use iterative traversal with an explicit deque/stack to prevent RecursionError on deep trees",
                "Do not use default sys.setrecursionlimit above 5000 due to OS C-stack overflow risks",
                0.92, 0.88, 45, 42, 3, "active", None, None,
            ),
            (
                "exp-research-002", None, "research",
                "Multi-source factual claims in academic literature",
                "Cross-reference claims across at least 2 independent peer-reviewed primary citations before synthesizing conclusions",
                "Do not cite single secondary review summaries when empirical rate estimates diverge significantly",
                0.90, 0.94, 120, 114, 6, "active", None, None,
            ),
            (
                "exp-analysis-003", None, "analysis",
                "Time series financial forecasting with missing date intervals",
                "Resample time series with forward-fill strictly up to 2 intervals, then flag remaining gaps as NaN",
                "Do not apply linear interpolation across market holiday boundary discontinuities",
                0.85, 0.82, 30, 26, 4, "active", None, None,
            ),
            (
                "exp-candidate-004", None, "coding",
                "High-concurrency async SQLite connection pooling",
                "Enable WAL mode and use a dedicated write queue with short exponential backoffs",
                "Do not share raw SQLite connection objects across asyncio thread boundaries",
                0.80, 0.50, 5, 4, 1, "candidate", None, None,
            ),
            (
                "exp-deprecated-005", None, "coding",
                "HTML parsing from unstructured web pages",
                "Use complex regular expressions to extract nested div contents",
                "Regex parsing fails catastrophically on malformed or non-compliant HTML trees",
                0.30, 0.22, 18, 2, 16, "deprecated", None, None,
            ),
        ]

        try:
            from ai_service.embedder import local_embedder
        except Exception:
            local_embedder = None

        now = datetime.now(timezone.utc)
        for item in seeds:
            id_, uid, domain, trig, strat, pit, conf, trust, uses, succ, fail, stat, emb, src = item
            if local_embedder is not None and emb is None:
                try:
                    emb = local_embedder.embed_text(trig)
                except Exception:
                    emb = None
            await conn.execute("""
                INSERT INTO experiences (
                    id, user_id, task_domain, trigger_condition, strategy_lesson, pitfall,
                    confidence, trust_score, uses_count, successes_count, failures_count,
                    status, embedding, source_task_id, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (id) DO NOTHING;
            """, id_, uid, domain, trig, strat, pit, conf, trust, uses, succ, fail, stat, emb, src, now, now)

    def _record_to_experience(self, row: Any) -> Experience:
        emb = row["embedding"]
        emb_list = None
        if emb is not None:
            if hasattr(emb, "tolist"):
                emb_list = emb.tolist()
            elif isinstance(emb, (list, tuple)):
                emb_list = [float(x) for x in emb]
            elif isinstance(emb, str):
                emb_list = json.loads(emb)
            else:
                emb_list = list(emb)

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
            embedding=emb_list,
            source_task_id=row["source_task_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def add_experience(self, exp: Experience) -> str:
        if exp.embedding is None:
            from ai_service.embedder import local_embedder
            exp.embedding = local_embedder.embed_text(exp.trigger_condition or "")

        pool = await self._get_pool()
        domain_val = exp.task_domain.value if isinstance(exp.task_domain, TaskDomain) else str(exp.task_domain)
        status_val = exp.status.value if isinstance(exp.status, ExperienceStatus) else str(exp.status)
        created_at = exp.created_at if isinstance(exp.created_at, datetime) else datetime.now(timezone.utc)
        updated_at = exp.updated_at if isinstance(exp.updated_at, datetime) else datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO experiences (
                    id, user_id, task_domain, trigger_condition, strategy_lesson, pitfall,
                    confidence, trust_score, uses_count, successes_count, failures_count,
                    status, embedding, source_task_id, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (id) DO UPDATE SET
                    trigger_condition = EXCLUDED.trigger_condition,
                    strategy_lesson = EXCLUDED.strategy_lesson,
                    pitfall = EXCLUDED.pitfall,
                    confidence = EXCLUDED.confidence,
                    trust_score = EXCLUDED.trust_score,
                    status = EXCLUDED.status,
                    embedding = EXCLUDED.embedding,
                    updated_at = EXCLUDED.updated_at;
            """,
                exp.id, exp.user_id, domain_val, exp.trigger_condition, exp.strategy_lesson, exp.pitfall,
                float(exp.confidence), float(exp.trust_score), int(exp.uses_count), int(exp.successes_count),
                int(exp.failures_count), status_val, exp.embedding, exp.source_task_id, created_at, updated_at
            )
        return exp.id

    async def get_experience(self, experience_id: str) -> Optional[Experience]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM experiences WHERE id = $1", experience_id)
            return self._record_to_experience(row) if row else None

    async def update_trust(
        self,
        experience_id: str,
        new_trust: float,
        reason: Optional[str] = None,
        execution_id: Optional[str] = None,
        status: Optional[str] = None,
        binary_outcome: Optional[int] = None,
    ) -> TrustHistoryRecord:
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT trust_score, status, uses_count, successes_count, failures_count FROM experiences WHERE id = $1 FOR UPDATE",
                    experience_id
                )
                if not row:
                    raise ValueError(f"Experience not found: {experience_id}")

                old_trust = float(row["trust_score"])
                new_trust = max(0.0, min(1.0, float(new_trust)))
                delta = new_trust - old_trust
                new_status = status or row["status"]

                uses_inc = 1 if binary_outcome is not None else 0
                success_inc = 1 if binary_outcome == 1 else 0
                failure_inc = 1 if binary_outcome == 0 else 0

                await conn.execute("""
                    UPDATE experiences SET
                        trust_score = $1,
                        status = $2,
                        uses_count = uses_count + $3,
                        successes_count = successes_count + $4,
                        failures_count = failures_count + $5,
                        updated_at = $6
                    WHERE id = $7
                """, new_trust, new_status, uses_inc, success_inc, failure_inc, now, experience_id)

                rec_id = str(uuid4())
                await conn.execute("""
                    INSERT INTO trust_history (id, experience_id, execution_id, old_trust, new_trust, delta, reason, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, rec_id, experience_id, execution_id, old_trust, new_trust, delta, reason, now)

                return TrustHistoryRecord(
                    id=rec_id,
                    experience_id=experience_id,
                    execution_id=execution_id,
                    old_trust=old_trust,
                    new_trust=new_trust,
                    delta=delta,
                    reason=reason,
                    created_at=now.isoformat(),
                )

    async def list_experiences(
        self,
        domain: Optional[TaskDomain] = None,
        status: Optional[ExperienceStatus] = None,
        min_trust: Optional[float] = None,
    ) -> List[Experience]:
        pool = await self._get_pool()
        query = "SELECT * FROM experiences WHERE 1=1"
        params: List[Any] = []
        param_idx = 1

        if domain:
            query += f" AND task_domain = ${param_idx}"
            params.append(domain.value if isinstance(domain, TaskDomain) else domain)
            param_idx += 1
        if status:
            query += f" AND status = ${param_idx}"
            params.append(status.value if isinstance(status, ExperienceStatus) else status)
            param_idx += 1
        if min_trust is not None:
            query += f" AND trust_score >= ${param_idx}"
            params.append(min_trust)
            param_idx += 1

        query += " ORDER BY trust_score DESC, updated_at DESC"
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._record_to_experience(r) for r in rows]

    async def search_similar(
        self, query_embedding: List[float], domain: Optional[TaskDomain] = None, top_k: int = 5
    ) -> List[Tuple[Experience, float]]:
        pool = await self._get_pool()
        domain_val = domain.value if isinstance(domain, TaskDomain) else domain

        async with pool.acquire() as conn:
            query = """
                SELECT id, user_id, task_domain, trigger_condition, strategy_lesson, pitfall,
                       confidence, trust_score, uses_count, successes_count, failures_count,
                       status, embedding, source_task_id, created_at, updated_at,
                       1 - (embedding <=> $1) AS similarity
                FROM experiences
                WHERE status = 'active'
                  AND ($2::text IS NULL OR task_domain = $2)
                  AND embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT $3;
            """
            rows = await conn.fetch(query, query_embedding, domain_val, top_k)
            results = []
            for r in rows:
                exp = self._record_to_experience(r)
                sim = max(0.0, min(1.0, float(r["similarity"]))) if r["similarity"] is not None else 0.0
                results.append((exp, sim))
            return results

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


class SupabaseMemoryStore(BaseMemoryStore):
    """
    Cloud-hosted Supabase memory store communicating over PostgREST HTTP RPC.
    Executes remote vector similarity via the match_experiences() stored procedure.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        anon_key: Optional[str] = None,
        service_role_key: Optional[str] = None,
        auto_seed: bool = False,
    ):
        self.url = (url or settings.SUPABASE_URL or "").rstrip("/")
        self.anon_key = anon_key or settings.SUPABASE_ANON_KEY or ""
        self.service_role_key = service_role_key or settings.SUPABASE_SERVICE_ROLE_KEY or ""
        self.auto_seed = auto_seed

        if not self.url or not self.anon_key:
            raise ValueError("SupabaseMemoryStore requires SUPABASE_URL and SUPABASE_ANON_KEY")

    def _headers(self) -> Dict[str, str]:
        key = self.service_role_key or self.anon_key
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def add_experience(self, exp: Experience) -> str:
        if exp.embedding is None:
            from ai_service.embedder import local_embedder
            exp.embedding = local_embedder.embed_text(exp.trigger_condition or "")

        payload = {
            "id": exp.id,
            "user_id": exp.user_id,
            "task_domain": exp.task_domain.value if isinstance(exp.task_domain, TaskDomain) else str(exp.task_domain),
            "trigger_condition": exp.trigger_condition,
            "strategy_lesson": exp.strategyLesson if hasattr(exp, "strategyLesson") else exp.strategy_lesson,
            "pitfall": exp.pitfall,
            "confidence": float(exp.confidence),
            "trust_score": float(exp.trust_score),
            "uses_count": int(exp.uses_count),
            "successes_count": int(exp.successes_count),
            "failures_count": int(exp.failures_count),
            "status": exp.status.value if isinstance(exp.status, ExperienceStatus) else str(exp.status),
            "embedding": exp.embedding,
            "source_task_id": exp.source_task_id,
        }

        async with httpx.AsyncClient(base_url=self.url, headers=self._headers(), timeout=15.0) as client:
            resp = await client.post("/rest/v1/experiences", json=payload)
            resp.raise_for_status()
            return exp.id

    async def get_experience(self, experience_id: str) -> Optional[Experience]:
        async with httpx.AsyncClient(base_url=self.url, headers=self._headers(), timeout=15.0) as client:
            resp = await client.get(f"/rest/v1/experiences?id=eq.{experience_id}")
            if resp.status_code == 200 and resp.json():
                return self._dict_to_experience(resp.json()[0])
            return None

    async def update_trust(
        self,
        experience_id: str,
        new_trust: float,
        reason: Optional[str] = None,
        execution_id: Optional[str] = None,
        status: Optional[str] = None,
        binary_outcome: Optional[int] = None,
    ) -> TrustHistoryRecord:
        exp = await self.get_experience(experience_id)
        if not exp:
            raise ValueError(f"Experience not found: {experience_id}")

        old_trust = float(exp.trust_score)
        new_trust = max(0.0, min(1.0, float(new_trust)))
        delta = new_trust - old_trust
        new_status = status or exp.status.value if hasattr(exp.status, "value") else str(exp.status)

        uses_inc = 1 if binary_outcome is not None else 0
        success_inc = 1 if binary_outcome == 1 else 0
        failure_inc = 1 if binary_outcome == 0 else 0

        now = utc_now_iso()
        patch_payload = {
            "trust_score": new_trust,
            "status": new_status,
            "uses_count": exp.uses_count + uses_inc,
            "successes_count": exp.successes_count + success_inc,
            "failures_count": exp.failures_count + failure_inc,
            "updated_at": now,
        }

        async with httpx.AsyncClient(base_url=self.url, headers=self._headers(), timeout=15.0) as client:
            resp = await client.patch(f"/rest/v1/experiences?id=eq.{experience_id}", json=patch_payload)
            resp.raise_for_status()

            rec = TrustHistoryRecord(
                experience_id=experience_id,
                execution_id=execution_id,
                old_trust=old_trust,
                new_trust=new_trust,
                delta=delta,
                reason=reason,
                created_at=now,
            )
            await client.post("/rest/v1/trust_history", json={
                "id": rec.id,
                "experience_id": rec.experience_id,
                "execution_id": rec.execution_id,
                "old_trust": rec.old_trust,
                "new_trust": rec.new_trust,
                "delta": rec.delta,
                "reason": rec.reason,
                "created_at": rec.created_at,
            })
            return rec

    async def list_experiences(
        self,
        domain: Optional[TaskDomain] = None,
        status: Optional[ExperienceStatus] = None,
        min_trust: Optional[float] = None,
    ) -> List[Experience]:
        params = ["select=*"]
        if domain:
            params.append(f"task_domain=eq.{domain.value if isinstance(domain, TaskDomain) else domain}")
        if status:
            params.append(f"status=eq.{status.value if isinstance(status, ExperienceStatus) else status}")
        if min_trust is not None:
            params.append(f"trust_score=gte.{min_trust}")
        params.append("order=trust_score.desc,updated_at.desc")

        url = f"/rest/v1/experiences?{'&'.join(params)}"
        async with httpx.AsyncClient(base_url=self.url, headers=self._headers(), timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return [self._dict_to_experience(d) for d in resp.json()]

    async def search_similar(
        self, query_embedding: List[float], domain: Optional[TaskDomain] = None, top_k: int = 5
    ) -> List[Tuple[Experience, float]]:
        domain_val = (domain.value if isinstance(domain, TaskDomain) else domain) if domain else None
        rpc_payload = {
            "query_embedding": query_embedding,
            "match_threshold": 0.0,
            "match_count": top_k,
            "filter_domain": domain_val,
        }

        async with httpx.AsyncClient(base_url=self.url, headers=self._headers(), timeout=15.0) as client:
            try:
                resp = await client.post("/rest/v1/rpc/match_experiences", json=rpc_payload)
                if resp.status_code == 200:
                    rows = resp.json()
                    results = []
                    for r in rows:
                        exp = self._dict_to_experience(r)
                        sim = float(r.get("similarity", 0.0))
                        results.append((exp, sim))
                    return results
            except Exception as e:
                logger.warning(f"Supabase RPC match_experiences call failed ({e}); falling back to client-side cosine")

        # Resilient fallback: list and compute cosine similarity
        all_exps = await self.list_experiences(domain=domain)
        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-6:
            return [(e, 0.0) for e in all_exps[:top_k]]

        scored = []
        for exp in all_exps:
            if not exp.embedding:
                continue
            e_vec = np.array(exp.embedding, dtype=np.float32)
            e_norm = np.linalg.norm(e_vec)
            if e_norm < 1e-6:
                continue
            sim = float(np.dot(q_vec, e_vec) / (q_norm * e_norm))
            scored.append((exp, max(0.0, min(1.0, sim))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _dict_to_experience(self, d: Dict[str, Any]) -> Experience:
        return Experience(
            id=d["id"],
            user_id=d.get("user_id"),
            task_domain=TaskDomain(d["task_domain"]) if d.get("task_domain") in [x.value for x in TaskDomain] else TaskDomain.GENERAL,
            trigger_condition=d["trigger_condition"],
            strategy_lesson=d["strategy_lesson"],
            pitfall=d.get("pitfall"),
            confidence=float(d.get("confidence", 0.85)),
            trust_score=float(d.get("trust_score", 0.75)),
            uses_count=int(d.get("uses_count", 0)),
            successes_count=int(d.get("successes_count", 0)),
            failures_count=int(d.get("failures_count", 0)),
            status=ExperienceStatus(d.get("status", "active")),
            embedding=d.get("embedding"),
            source_task_id=d.get("source_task_id"),
            created_at=d.get("created_at") or utc_now_iso(),
            updated_at=d.get("updated_at") or utc_now_iso(),
        )


def get_memory_store(
    engine: Optional[str] = None,
    db_path: Optional[str] = None,
    database_url: Optional[str] = None,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    auto_seed: bool = True,
) -> BaseMemoryStore:
    """
    Factory creating the configured persistent memory store:
    - 'postgres' -> PostgresMemoryStore (asyncpg + pgvector HNSW)
    - 'supabase' -> SupabaseMemoryStore (PostgREST + RPC)
    - 'sqlite' (or default) -> SQLiteMemoryStore (local WAL + numpy)
    """
    selected_engine = (engine or settings.STORAGE_ENGINE or "sqlite").lower()

    if selected_engine in ("postgres", "postgresql"):
        url = database_url or settings.DATABASE_URL
        if url and HAS_POSTGRES:
            return PostgresMemoryStore(database_url=url, auto_seed=auto_seed)
        if not HAS_POSTGRES:
            logger.warning("PostgreSQL engine requested but asyncpg/pgvector not installed; falling back to SQLite")
        else:
            logger.warning("PostgreSQL engine requested but no DATABASE_URL provided; falling back to SQLite")

    if selected_engine == "supabase":
        url = supabase_url or settings.SUPABASE_URL
        key = supabase_key or settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY
        if url and key:
            return SupabaseMemoryStore(url=url, anon_key=key, auto_seed=auto_seed)
        logger.warning("Supabase engine requested but SUPABASE_URL / key missing; falling back to SQLite")

    return SQLiteMemoryStore(db_path=db_path or settings.SQLITE_DB_PATH, auto_seed=auto_seed)


# Global default store instance
memory_store = get_memory_store()
