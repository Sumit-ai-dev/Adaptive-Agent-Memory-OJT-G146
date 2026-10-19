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
from ai_service.tools.evaluator import EvaluationOutcome
from ai_service.trust_math import calculate_probation_quota, should_quarantine
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
    async def admin_recover_to_probation(
        self,
        experience_id: str,
        reason: str,
        actor_id: str = "system:admin_api_key",
        client_ref: Optional[str] = None,
    ) -> Experience:
        """
        Safely transitions an experience from DEPRECATED to CANDIDATE probation.
        Preserves all historical failure, success, and uses counters.
        """
        pass

    @abstractmethod
    async def record_probationary_probe(
        self,
        experience_id: str,
        outcome: EvaluationOutcome,
        execution_id: str,
        task_fingerprint: str,
        actor_id: str = "system:admin_api_key",
        client_ref: Optional[str] = None,
    ) -> Tuple[Experience, TrustHistoryRecord]:
        """
        Atomically evaluates and persists an isolated probationary validation probe.
        Enforces fingerprint and execution-id idempotency.
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

    def _get_write_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA journal_mode = WAL")
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
                    probation_successes INTEGER NOT NULL DEFAULT 0,
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS probation_task_fingerprints (
                    id TEXT PRIMARY KEY,
                    experience_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL UNIQUE,
                    fingerprint TEXT NOT NULL,
                    outcome_reward REAL NOT NULL,
                    is_success INTEGER NOT NULL,
                    actor_id TEXT NOT NULL,
                    client_ref TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(experience_id) REFERENCES experiences(id),
                    UNIQUE(experience_id, fingerprint)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_domain_status ON experiences(task_domain, status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_trust ON experiences(trust_score DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_probation_fp ON probation_task_fingerprints(experience_id, fingerprint)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_probation_exec ON probation_task_fingerprints(execution_id)")

            # Idempotent migration for existing SQLite databases
            cursor.execute("PRAGMA table_info(experiences)")
            columns = [col[1] for col in cursor.fetchall()]
            if "probation_successes" not in columns:
                cursor.execute("ALTER TABLE experiences ADD COLUMN probation_successes INTEGER NOT NULL DEFAULT 0")

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
                    probation_successes, status, embedding, source_task_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
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
            prob_successes = getattr(exp, "probation_successes", 0)
            cursor.execute("""
                INSERT OR REPLACE INTO experiences (
                    id, user_id, task_domain, trigger_condition, strategy_lesson, pitfall,
                    confidence, trust_score, uses_count, successes_count, failures_count,
                    probation_successes, status, embedding, source_task_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp.id, exp.user_id, exp.task_domain.value if isinstance(exp.task_domain, TaskDomain) else exp.task_domain,
                exp.trigger_condition, exp.strategy_lesson, exp.pitfall,
                exp.confidence, exp.trust_score, exp.uses_count, exp.successes_count, exp.failures_count,
                prob_successes,
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
            cursor.execute("SELECT trust_score, successes_count, failures_count, uses_count, status, probation_successes FROM experiences WHERE id = ?", (experience_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Experience '{experience_id}' not found.")

            old_trust = float(row["trust_score"])
            delta = float(new_trust - old_trust)
            current_status = row["status"]

            if status is not None:
                new_status = status
            elif new_trust < settings.THETA_CUTOFF:
                new_status = ExperienceStatus.DEPRECATED.value
            elif current_status == ExperienceStatus.CANDIDATE.value and new_trust >= settings.RELIABILITY_THRESHOLD:
                quota = calculate_probation_quota(int(row["failures_count"]))
                cur_probation = int(row["probation_successes"]) if "probation_successes" in row.keys() else 0
                calc_successes = int(row["successes_count"]) + (1 if binary_outcome == 1 else 0)
                calc_failures = int(row["failures_count"]) + (1 if binary_outcome == 0 else 0)
                if (cur_probation >= quota and
                    not should_quarantine(calc_successes, calc_failures, gamma=settings.QUARANTINE_GAMMA, threshold=settings.RELIABILITY_THRESHOLD)):
                    new_status = ExperienceStatus.ACTIVE.value
                else:
                    new_status = ExperienceStatus.CANDIDATE.value
            else:
                new_status = current_status

            # Enforce state machine transitions:
            # 1. Reject direct DEPRECATED -> ACTIVE transitions
            if current_status == ExperienceStatus.DEPRECATED.value and new_status == ExperienceStatus.ACTIVE.value:
                raise ValueError(
                    f"Invalid state transition: Cannot transition directly from {current_status} to {new_status}. "
                    f"DEPRECATED experiences must transition through CANDIDATE probation first."
                )

            # 2. Promote candidate only when quota is met, trust >= 0.70, and quarantine permits retrieval
            if current_status == ExperienceStatus.CANDIDATE.value and new_status == ExperienceStatus.ACTIVE.value:
                quota = calculate_probation_quota(int(row["failures_count"]))
                cur_probation = int(row["probation_successes"]) if "probation_successes" in row.keys() else 0
                calc_successes = int(row["successes_count"]) + (1 if binary_outcome == 1 else 0)
                calc_failures = int(row["failures_count"]) + (1 if binary_outcome == 0 else 0)
                if cur_probation < quota:
                    raise ValueError(
                        f"Cannot promote CANDIDATE '{experience_id}' to ACTIVE: probation quota not met "
                        f"({cur_probation}/{quota} verified probationary successes)."
                    )
                if new_trust < settings.RELIABILITY_THRESHOLD:
                    raise ValueError(
                        f"Cannot promote CANDIDATE '{experience_id}' to ACTIVE: trust score {new_trust:.4f} "
                        f"is below reliability threshold {settings.RELIABILITY_THRESHOLD:.2f}."
                    )
                if should_quarantine(calc_successes, calc_failures, gamma=settings.QUARANTINE_GAMMA, threshold=settings.RELIABILITY_THRESHOLD):
                    raise ValueError(
                        f"Cannot promote CANDIDATE '{experience_id}' to ACTIVE: Bayesian quarantine policy forbids promotion."
                    )

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

    async def admin_recover_to_probation(
        self,
        experience_id: str,
        reason: str,
        actor_id: str = "system:admin_api_key",
        client_ref: Optional[str] = None,
    ) -> Experience:
        if not reason or len(reason.strip()) < 15:
            raise ValueError("A meaningful audit reason of at least 15 characters is required for recovery.")

        conn = self._get_write_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiences WHERE id = ?", (experience_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Experience '{experience_id}' not found.")

            current_status = row["status"]
            if current_status != ExperienceStatus.DEPRECATED.value:
                raise ValueError(
                    f"Experience '{experience_id}' is in status '{current_status}'. "
                    f"Only DEPRECATED memories can be recovered to CANDIDATE probation."
                )

            now = utc_now_iso()
            cursor.execute("""
                UPDATE experiences SET
                    status = ?,
                    probation_successes = 0,
                    updated_at = ?
                WHERE id = ?
            """, (ExperienceStatus.CANDIDATE.value, now, experience_id))

            old_trust = float(row["trust_score"])
            audit_reason = f"Administrative recovery to probation by {actor_id}: {reason.strip()}"
            if client_ref:
                audit_reason += f" [CLIENT_REF: {client_ref.strip()}]"

            rec_id = str(uuid4())
            cursor.execute("""
                INSERT INTO trust_history (id, experience_id, execution_id, old_trust, new_trust, delta, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (rec_id, experience_id, f"admin_rec_{uuid4().hex[:8]}", old_trust, old_trust, 0.0, audit_reason, now))

            cursor.execute("SELECT * FROM experiences WHERE id = ?", (experience_id,))
            updated_row = cursor.fetchone()
            result_exp = self._row_to_experience(updated_row)
            conn.execute("COMMIT")
            return result_exp
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception as rb_err:
                logger.warning(f"Rollback failed: {rb_err}")
            raise
        finally:
            conn.close()

    async def record_probationary_probe(
        self,
        experience_id: str,
        outcome: EvaluationOutcome,
        execution_id: str,
        task_fingerprint: str,
        actor_id: str = "system:admin_api_key",
        client_ref: Optional[str] = None,
    ) -> Tuple[Experience, TrustHistoryRecord]:
        conn = self._get_write_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            # 1. Idempotency checks
            cursor.execute("SELECT id FROM probation_task_fingerprints WHERE execution_id = ?", (execution_id,))
            if cursor.fetchone():
                raise ValueError(f"Duplicate execution ID '{execution_id}': cannot process probe twice.")

            cursor.execute("SELECT id FROM trust_history WHERE execution_id = ?", (execution_id,))
            if cursor.fetchone():
                raise ValueError(f"Duplicate execution ID '{execution_id}': cannot process probe twice.")

            cursor.execute(
                "SELECT id FROM probation_task_fingerprints WHERE experience_id = ? AND fingerprint = ?",
                (experience_id, task_fingerprint),
            )
            if cursor.fetchone():
                raise ValueError(
                    f"Duplicate task fingerprint '{task_fingerprint}' for experience '{experience_id}'. "
                    f"Repeated probe cannot mutate counters or increment probation quota."
                )

            # 2. Fetch experience
            cursor.execute("SELECT * FROM experiences WHERE id = ?", (experience_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Experience '{experience_id}' not found.")

            if row["status"] != ExperienceStatus.CANDIDATE.value:
                raise ValueError(
                    f"Experience '{experience_id}' is in status '{row['status']}'. "
                    f"Only CANDIDATE memories can undergo probationary validation."
                )

            old_trust = float(row["trust_score"])
            cur_uses = int(row["uses_count"])
            cur_successes = int(row["successes_count"])
            cur_failures = int(row["failures_count"])
            cur_probation = int(row["probation_successes"]) if "probation_successes" in row.keys() else 0

            # 3. Classify outcome
            details = outcome.details or {}
            is_inconclusive = (
                details.get("status") == "inconclusive"
                or details.get("error") in ("missing_test_code", "harness_error", "infrastructure_error", "invalid_setup", "provider_error")
                or (bool(outcome.reason) and outcome.reason.strip().lower().startswith("inconclusive"))
            )

            now = utc_now_iso()
            if is_inconclusive:
                new_trust = old_trust
                delta = 0.0
                new_status = ExperienceStatus.CANDIDATE.value
                uses_inc = 0
                success_inc = 0
                failure_inc = 0
                prob_inc = 0
                audit_reason = f"Inconclusive probe evaluation ({details.get('error', 'unverified')}): trust and counters preserved"
            elif outcome.is_success:
                new_trust = round((settings.ALPHA_SUCCESS * old_trust) + ((1.0 - settings.ALPHA_SUCCESS) * 1.0), 4)
                delta = round(new_trust - old_trust, 4)
                uses_inc = 1
                success_inc = 1
                failure_inc = 0
                prob_inc = 1
                new_probation = cur_probation + prob_inc
                new_successes = cur_successes + success_inc

                quota = calculate_probation_quota(cur_failures)
                is_quota_met = new_probation >= quota
                is_trust_admissible = new_trust >= settings.RELIABILITY_THRESHOLD
                is_quarantine_permitted = not should_quarantine(
                    new_successes,
                    cur_failures,
                    gamma=settings.QUARANTINE_GAMMA,
                    threshold=settings.RELIABILITY_THRESHOLD,
                )

                if is_quota_met and is_trust_admissible and is_quarantine_permitted:
                    new_status = ExperienceStatus.ACTIVE.value
                    audit_reason = (
                        f"Probation verified success (R={outcome.reward:.2f}): promoted to ACTIVE "
                        f"(quota {new_probation}/{quota} met, trust {new_trust:.4f} >= {settings.RELIABILITY_THRESHOLD:.2f})"
                    )
                else:
                    new_status = ExperienceStatus.CANDIDATE.value
                    reasons = []
                    if not is_quota_met:
                        reasons.append(f"quota {new_probation}/{quota}")
                    if not is_trust_admissible:
                        reasons.append(f"trust {new_trust:.4f} < {settings.RELIABILITY_THRESHOLD:.2f}")
                    if not is_quarantine_permitted:
                        reasons.append("quarantine policy")
                    audit_reason = (
                        f"Probation verified success (R={outcome.reward:.2f}): retained in CANDIDATE "
                        f"({', '.join(reasons)})"
                    )
            else:
                new_trust = round(settings.BETA_FAILURE * old_trust, 4)
                delta = round(new_trust - old_trust, 4)
                new_status = ExperienceStatus.DEPRECATED.value
                uses_inc = 1
                success_inc = 0
                failure_inc = 1
                prob_inc = 0
                audit_reason = f"Probation verified failure ({outcome.reason}): revoked to DEPRECATED"

            if client_ref:
                audit_reason += f" [CLIENT_REF: {client_ref.strip()}]"

            # 4. Atomically persist experience updates
            cursor.execute("""
                UPDATE experiences SET
                    trust_score = ?,
                    status = ?,
                    uses_count = uses_count + ?,
                    successes_count = successes_count + ?,
                    failures_count = failures_count + ?,
                    probation_successes = probation_successes + ?,
                    updated_at = ?
                WHERE id = ?
            """, (new_trust, new_status, uses_inc, success_inc, failure_inc, prob_inc, now, experience_id))

            # 5. Idempotently record fingerprint for verified observations (success or failure)
            if not is_inconclusive:
                fp_id = str(uuid4())
                cursor.execute("""
                    INSERT INTO probation_task_fingerprints (
                        id, experience_id, execution_id, fingerprint, outcome_reward,
                        is_success, actor_id, client_ref, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fp_id, experience_id, execution_id, task_fingerprint,
                    float(outcome.reward), 1 if outcome.is_success else 0,
                    actor_id, client_ref, now
                ))

            # 6. Append trust history ledger
            history_record = TrustHistoryRecord(
                experience_id=experience_id,
                execution_id=execution_id,
                old_trust=old_trust,
                new_trust=new_trust,
                delta=delta,
                reason=audit_reason,
                created_at=now,
            )
            cursor.execute("""
                INSERT INTO trust_history (id, experience_id, execution_id, old_trust, new_trust, delta, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                history_record.id, history_record.experience_id, history_record.execution_id,
                history_record.old_trust, history_record.new_trust, history_record.delta,
                history_record.reason, history_record.created_at
            ))

            cursor.execute("SELECT * FROM experiences WHERE id = ?", (experience_id,))
            updated_exp_row = cursor.fetchone()
            result_exp = self._row_to_experience(updated_exp_row)
            conn.execute("COMMIT")
            return result_exp, history_record
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception as rb_err:
                logger.warning(f"Rollback failed: {rb_err}")
            raise
        finally:
            conn.close()

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

        from ai_service.embedder import local_embedder

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-6:
            return [(e, 0.0) for e in experiences[:top_k]]

        scored: List[Tuple[Experience, float]] = []
        for exp in experiences:
            if not exp.embedding:
                try:
                    exp.embedding = local_embedder.embed_text(exp.trigger_condition or "")
                    with self._get_connection() as conn:
                        conn.execute("UPDATE experiences SET embedding = ? WHERE id = ?", (json.dumps(exp.embedding), exp.id))
                        conn.commit()
                except Exception:
                    scored.append((exp, 0.0))
                    continue

            # Self-healing: if neural model is active but memory has offline hash embedding, re-align
            if local_embedder._model is not None and exp.trigger_condition:
                try:
                    h_vec = np.array(local_embedder._deterministic_hash_vector(exp.trigger_condition), dtype=np.float32)
                    if np.linalg.norm(np.array(exp.embedding, dtype=np.float32) - h_vec) < 1e-4:
                        exp.embedding = local_embedder.embed_text(exp.trigger_condition)
                        with self._get_connection() as conn:
                            conn.execute("UPDATE experiences SET embedding = ? WHERE id = ?", (json.dumps(exp.embedding), exp.id))
                            conn.commit()
                except Exception:
                    pass

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
        prob_successes = int(row["probation_successes"]) if "probation_successes" in row.keys() else 0
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
            probation_successes=prob_successes,
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
                    probation_successes INTEGER NOT NULL DEFAULT 0,
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
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS probation_task_fingerprints (
                    id TEXT PRIMARY KEY,
                    experience_id TEXT NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
                    execution_id TEXT NOT NULL UNIQUE,
                    fingerprint TEXT NOT NULL,
                    outcome_reward DOUBLE PRECISION NOT NULL,
                    is_success INTEGER NOT NULL,
                    actor_id TEXT NOT NULL,
                    client_ref TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(experience_id, fingerprint)
                );
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_exp_domain_status ON experiences(task_domain, status);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_exp_trust ON experiences(trust_score DESC);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_probation_fp ON probation_task_fingerprints(experience_id, fingerprint);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_probation_exec ON probation_task_fingerprints(execution_id);")

            # Idempotent migration for existing PostgreSQL databases
            await conn.execute("ALTER TABLE experiences ADD COLUMN IF NOT EXISTS probation_successes INTEGER NOT NULL DEFAULT 0;")

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
                    probation_successes, status, embedding, source_task_id, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 0, $12, $13, $14, $15, $16)
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

        prob_successes = int(row["probation_successes"]) if "probation_successes" in row else 0

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
            probation_successes=prob_successes,
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
        prob_successes = getattr(exp, "probation_successes", 0)

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO experiences (
                    id, user_id, task_domain, trigger_condition, strategy_lesson, pitfall,
                    confidence, trust_score, uses_count, successes_count, failures_count,
                    probation_successes, status, embedding, source_task_id, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (id) DO UPDATE SET
                    trigger_condition = EXCLUDED.trigger_condition,
                    strategy_lesson = EXCLUDED.strategy_lesson,
                    pitfall = EXCLUDED.pitfall,
                    confidence = EXCLUDED.confidence,
                    trust_score = EXCLUDED.trust_score,
                    probation_successes = EXCLUDED.probation_successes,
                    status = EXCLUDED.status,
                    embedding = EXCLUDED.embedding,
                    updated_at = EXCLUDED.updated_at;
            """,
                exp.id, exp.user_id, domain_val, exp.trigger_condition, exp.strategy_lesson, exp.pitfall,
                float(exp.confidence), float(exp.trust_score), int(exp.uses_count), int(exp.successes_count),
                int(exp.failures_count), prob_successes, status_val, exp.embedding, exp.source_task_id, created_at, updated_at
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
                    "SELECT trust_score, status, uses_count, successes_count, failures_count, probation_successes FROM experiences WHERE id = $1 FOR UPDATE",
                    experience_id
                )
                if not row:
                    raise ValueError(f"Experience not found: {experience_id}")

                old_trust = float(row["trust_score"])
                new_trust = max(0.0, min(1.0, float(new_trust)))
                delta = new_trust - old_trust
                current_status = row["status"]
                new_status = status or current_status

                # Enforce state machine transitions:
                # 1. Reject direct DEPRECATED -> ACTIVE transitions
                if current_status == ExperienceStatus.DEPRECATED.value and new_status == ExperienceStatus.ACTIVE.value:
                    raise ValueError(
                        f"Invalid state transition: Cannot transition directly from {current_status} to {new_status}. "
                        f"DEPRECATED experiences must transition through CANDIDATE probation first."
                    )

                # 2. Promote candidate only when quota is met, trust >= 0.70, and quarantine permits retrieval
                if current_status == ExperienceStatus.CANDIDATE.value and new_status == ExperienceStatus.ACTIVE.value:
                    quota = calculate_probation_quota(int(row["failures_count"]))
                    cur_probation = int(row["probation_successes"]) if "probation_successes" in row else 0
                    calc_successes = int(row["successes_count"]) + (1 if binary_outcome == 1 else 0)
                    calc_failures = int(row["failures_count"]) + (1 if binary_outcome == 0 else 0)
                    if cur_probation < quota:
                        raise ValueError(
                            f"Cannot promote CANDIDATE '{experience_id}' to ACTIVE: probation quota not met ({cur_probation}/{quota})."
                        )
                    if new_trust < settings.RELIABILITY_THRESHOLD:
                        raise ValueError(
                            f"Cannot promote CANDIDATE '{experience_id}' to ACTIVE: trust score {new_trust:.4f} < {settings.RELIABILITY_THRESHOLD:.2f}."
                        )
                    if should_quarantine(calc_successes, calc_failures, gamma=settings.QUARANTINE_GAMMA, threshold=settings.RELIABILITY_THRESHOLD):
                        raise ValueError(
                            f"Cannot promote CANDIDATE '{experience_id}' to ACTIVE: Bayesian quarantine policy forbids promotion."
                        )

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

    async def admin_recover_to_probation(
        self,
        experience_id: str,
        reason: str,
        actor_id: str = "system:admin_api_key",
        client_ref: Optional[str] = None,
    ) -> Experience:
        if not reason or len(reason.strip()) < 15:
            raise ValueError("A meaningful audit reason of at least 15 characters is required for recovery.")

        pool = await self._get_pool()
        now = datetime.now(timezone.utc)
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM experiences WHERE id = $1 FOR UPDATE",
                    experience_id,
                )
                if not row:
                    raise ValueError(f"Experience '{experience_id}' not found.")

                current_status = row["status"]
                if current_status != ExperienceStatus.DEPRECATED.value:
                    raise ValueError(
                        f"Experience '{experience_id}' is in status '{current_status}'. "
                        f"Only DEPRECATED memories can be recovered to CANDIDATE probation."
                    )

                await conn.execute("""
                    UPDATE experiences SET
                        status = $1,
                        probation_successes = 0,
                        updated_at = $2
                    WHERE id = $3
                """, ExperienceStatus.CANDIDATE.value, now, experience_id)

                old_trust = float(row["trust_score"])
                audit_reason = f"Administrative recovery to probation by {actor_id}: {reason.strip()}"
                if client_ref:
                    audit_reason += f" [CLIENT_REF: {client_ref.strip()}]"

                rec_id = str(uuid4())
                await conn.execute("""
                    INSERT INTO trust_history (id, experience_id, execution_id, old_trust, new_trust, delta, reason, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, rec_id, experience_id, f"admin_rec_{uuid4().hex[:8]}", old_trust, old_trust, 0.0, audit_reason, now)

                updated_row = await conn.fetchrow("SELECT * FROM experiences WHERE id = $1", experience_id)
                return self._record_to_experience(updated_row)

    async def record_probationary_probe(
        self,
        experience_id: str,
        outcome: EvaluationOutcome,
        execution_id: str,
        task_fingerprint: str,
        actor_id: str = "system:admin_api_key",
        client_ref: Optional[str] = None,
    ) -> Tuple[Experience, TrustHistoryRecord]:
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)
        async with pool.acquire() as conn:
            async with conn.transaction():
                # 1. Idempotency checks
                existing_exec = await conn.fetchrow(
                    "SELECT id FROM probation_task_fingerprints WHERE execution_id = $1",
                    execution_id,
                )
                if existing_exec:
                    raise ValueError(f"Duplicate execution ID '{execution_id}': cannot process probe twice.")

                existing_hist = await conn.fetchrow(
                    "SELECT id FROM trust_history WHERE execution_id = $1",
                    execution_id,
                )
                if existing_hist:
                    raise ValueError(f"Duplicate execution ID '{execution_id}': cannot process probe twice.")

                existing_fp = await conn.fetchrow(
                    "SELECT id FROM probation_task_fingerprints WHERE experience_id = $1 AND fingerprint = $2",
                    experience_id, task_fingerprint,
                )
                if existing_fp:
                    raise ValueError(
                        f"Duplicate task fingerprint '{task_fingerprint}' for experience '{experience_id}'. "
                        f"Repeated probe cannot mutate counters or increment probation quota."
                    )

                # 2. Row locking
                row = await conn.fetchrow(
                    "SELECT * FROM experiences WHERE id = $1 FOR UPDATE",
                    experience_id,
                )
                if not row:
                    raise ValueError(f"Experience '{experience_id}' not found.")

                if row["status"] != ExperienceStatus.CANDIDATE.value:
                    raise ValueError(
                        f"Experience '{experience_id}' is in status '{row['status']}'. "
                        f"Only CANDIDATE memories can undergo probationary validation."
                    )

                old_trust = float(row["trust_score"])
                cur_uses = int(row["uses_count"])
                cur_successes = int(row["successes_count"])
                cur_failures = int(row["failures_count"])
                cur_probation = int(row.get("probation_successes") or 0)

                # 3. Classify outcome
                details = outcome.details or {}
                is_inconclusive = (
                    details.get("status") == "inconclusive"
                    or details.get("error") in ("missing_test_code", "harness_error", "infrastructure_error", "invalid_setup", "provider_error")
                    or (bool(outcome.reason) and outcome.reason.strip().lower().startswith("inconclusive"))
                )

                if is_inconclusive:
                    new_trust = old_trust
                    delta = 0.0
                    new_status = ExperienceStatus.CANDIDATE.value
                    uses_inc = 0
                    success_inc = 0
                    failure_inc = 0
                    prob_inc = 0
                    audit_reason = f"Inconclusive probe evaluation ({details.get('error', 'unverified')}): trust and counters preserved"
                elif outcome.is_success:
                    new_trust = round((settings.ALPHA_SUCCESS * old_trust) + ((1.0 - settings.ALPHA_SUCCESS) * 1.0), 4)
                    delta = round(new_trust - old_trust, 4)
                    uses_inc = 1
                    success_inc = 1
                    failure_inc = 0
                    prob_inc = 1
                    new_probation = cur_probation + prob_inc
                    new_successes = cur_successes + success_inc

                    quota = calculate_probation_quota(cur_failures)
                    is_quota_met = new_probation >= quota
                    is_trust_admissible = new_trust >= settings.RELIABILITY_THRESHOLD
                    is_quarantine_permitted = not should_quarantine(
                        new_successes,
                        cur_failures,
                        gamma=settings.QUARANTINE_GAMMA,
                        threshold=settings.RELIABILITY_THRESHOLD,
                    )

                    if is_quota_met and is_trust_admissible and is_quarantine_permitted:
                        new_status = ExperienceStatus.ACTIVE.value
                        audit_reason = (
                            f"Probation verified success (R={outcome.reward:.2f}): promoted to ACTIVE "
                            f"(quota {new_probation}/{quota} met, trust {new_trust:.4f} >= {settings.RELIABILITY_THRESHOLD:.2f})"
                        )
                    else:
                        new_status = ExperienceStatus.CANDIDATE.value
                        reasons = []
                        if not is_quota_met:
                            reasons.append(f"quota {new_probation}/{quota}")
                        if not is_trust_admissible:
                            reasons.append(f"trust {new_trust:.4f} < {settings.RELIABILITY_THRESHOLD:.2f}")
                        if not is_quarantine_permitted:
                            reasons.append("quarantine policy")
                        audit_reason = (
                            f"Probation verified success (R={outcome.reward:.2f}): retained in CANDIDATE "
                            f"({', '.join(reasons)})"
                        )
                else:
                    new_trust = round(settings.BETA_FAILURE * old_trust, 4)
                    delta = round(new_trust - old_trust, 4)
                    new_status = ExperienceStatus.DEPRECATED.value
                    uses_inc = 1
                    success_inc = 0
                    failure_inc = 1
                    prob_inc = 0
                    audit_reason = f"Probation verified failure ({outcome.reason}): revoked to DEPRECATED"

                if client_ref:
                    audit_reason += f" [CLIENT_REF: {client_ref.strip()}]"

                # 4. Update experiences
                await conn.execute("""
                    UPDATE experiences SET
                        trust_score = $1,
                        status = $2,
                        uses_count = uses_count + $3,
                        successes_count = successes_count + $4,
                        failures_count = failures_count + $5,
                        probation_successes = probation_successes + $6,
                        updated_at = $7
                    WHERE id = $8
                """, new_trust, new_status, uses_inc, success_inc, failure_inc, prob_inc, now, experience_id)

                # 5. Idempotently record fingerprint
                if not is_inconclusive:
                    fp_id = str(uuid4())
                    await conn.execute("""
                        INSERT INTO probation_task_fingerprints (
                            id, experience_id, execution_id, fingerprint, outcome_reward,
                            is_success, actor_id, client_ref, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, fp_id, experience_id, execution_id, task_fingerprint, float(outcome.reward), 1 if outcome.is_success else 0, actor_id, client_ref, now)

                # 6. Append trust history
                rec_id = str(uuid4())
                await conn.execute("""
                    INSERT INTO trust_history (id, experience_id, execution_id, old_trust, new_trust, delta, reason, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, rec_id, experience_id, execution_id, old_trust, new_trust, delta, audit_reason, now)

                updated_row = await conn.fetchrow("SELECT * FROM experiences WHERE id = $1", experience_id)
                rec = TrustHistoryRecord(
                    id=rec_id,
                    experience_id=experience_id,
                    execution_id=execution_id,
                    old_trust=old_trust,
                    new_trust=new_trust,
                    delta=delta,
                    reason=audit_reason,
                    created_at=now.isoformat(),
                )
                return self._record_to_experience(updated_row), rec

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

    async def admin_recover_to_probation(
        self,
        experience_id: str,
        reason: str,
        actor_id: str = "system:admin_api_key",
        client_ref: Optional[str] = None,
    ) -> Experience:
        exp = await self.get_experience(experience_id)
        if not exp:
            raise ValueError(f"Experience '{experience_id}' not found.")
        if exp.status != ExperienceStatus.DEPRECATED:
            raise ValueError(
                f"Experience '{experience_id}' is in status '{exp.status.value}'. "
                f"Only DEPRECATED memories can be recovered to CANDIDATE probation."
            )
        audit_reason = f"Administrative recovery to probation by {actor_id}: {reason.strip()}"
        if client_ref:
            audit_reason += f" [CLIENT_REF: {client_ref.strip()}]"

        await self.update_trust(
            experience_id=experience_id,
            new_trust=exp.trust_score,
            status=ExperienceStatus.CANDIDATE.value,
            reason=audit_reason,
        )
        updated = await self.get_experience(experience_id)
        return updated or exp

    async def record_probationary_probe(
        self,
        experience_id: str,
        outcome: EvaluationOutcome,
        execution_id: str,
        task_fingerprint: str,
        actor_id: str = "system:admin_api_key",
        client_ref: Optional[str] = None,
    ) -> Tuple[Experience, TrustHistoryRecord]:
        raise NotImplementedError("Probationary probes on Supabase require server-side RPC transaction.")

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
            probation_successes=int(d.get("probation_successes", 0)),
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
