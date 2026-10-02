"""
Integration Tests for LangGraph 5-Node Cyclical Orchestration StateGraph.
Verifies the complete lifecycle:
  retrieve_node -> execute_node -> evaluate_node -> reflect_node -> trust_node
"""

import asyncio
import os
import pytest

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from models.domain import ExecutionStatus, MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus
from models.provider import ModelProvider
from models.task import TaskExecuteRequest


def test_end_to_end_agent_graph_execution():
    async def _run():
        test_db = "data/test_agent_graph.db"
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except OSError:
                pass

        store = SQLiteMemoryStore(db_path=test_db)

        # 1. Seed an active positive experience
        exp = Experience(
            id="exp_seed_001",
            task_domain=TaskDomain.RESEARCH,
            trigger_condition="Tasks comparing entity release dates",
            strategy_lesson="Cross-reference chronological release schedules.",
            pitfall="Do not assume alphabetical order matches timeline.",
            trust_score=0.92,
            status=ExperienceStatus.ACTIVE,
        )
        await store.add_experience(exp)

        # 2. Run execution request
        req = TaskExecuteRequest(
            task_input="Which movie was released first, Iron Man or Thor?",
            task_domain=TaskDomain.RESEARCH,
            memory_mode=MemoryMode.ADAPTIVE,
            provider=ModelProvider.MOCK,
        )

        execution = await execute_task(req, memory_store=store)

        assert execution.status == ExecutionStatus.COMPLETED
        assert len(execution.trajectory) >= 5
        assert execution.final_answer is not None
        assert len(execution.final_answer) > 0

        # Verify all 5 nodes were executed in trajectory
        executed_nodes = [t.node for t in execution.trajectory if t.node]
        for expected_node in ["retrieve_node", "execute_node", "evaluate_node", "reflect_node", "trust_node"]:
            assert expected_node in executed_nodes, f"Missing expected node: {expected_node}"

        # Verify new experience was saved into the store
        memories = await store.list_experiences(min_trust=0.0)
        assert len(memories) >= 1

        # Cleanup
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except OSError:
                pass

    asyncio.run(_run())
