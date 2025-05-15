"""
Unit tests for the TaskPollerInterface implementation.
"""
import pytest
import uuid
from typing import Dict, List, Optional, Any
import asyncio
from unittest.mock import patch, AsyncMock

from agents.executor_agent.domain.interfaces import TaskPollerInterface


class MockTaskPoller(TaskPollerInterface):
    """Mock implementation of TaskPollerInterface for testing."""
    
    def __init__(self, available_tasks=None):
        """Initialize with optional predefined tasks."""
        self.available_tasks = available_tasks or []
        self.claimed_tasks = set()
        self.task_statuses = {}
    
    async def poll_for_tasks(self) -> Optional[Dict[str, Any]]:
        """Return the next available task or None."""
        for task in self.available_tasks:
            task_id = task["id"]
            if task_id not in self.claimed_tasks:
                return task
        return None
    
    async def claim_task(self, task_id: uuid.UUID) -> bool:
        """Claim a task for execution."""
        str_id = str(task_id)
        for task in self.available_tasks:
            if task["id"] == str_id and str_id not in self.claimed_tasks:
                self.claimed_tasks.add(str_id)
                return True
        return False
    
    async def update_task_status(self, task_id: uuid.UUID, status: str,
                           result: Optional[Dict[str, Any]] = None,
                           error: Optional[str] = None) -> bool:
        """Update the status of a task."""
        str_id = str(task_id)
        if str_id in self.claimed_tasks:
            self.task_statuses[str_id] = {
                "status": status,
                "result": result,
                "error": error
            }
            return True
        return False


class TestTaskPoller:
    """Tests for TaskPoller implementation."""
    
    @pytest.fixture
    def sample_tasks(self):
        """Generate sample tasks for testing."""
        return [
            {
                "id": str(uuid.uuid4()),
                "task_type": "echo",
                "parameters": {"message": "Hello, world!"},
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "task_type": "delay",
                "parameters": {"seconds": 5},
                "status": "pending"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_poll_for_tasks(self, sample_tasks):
        """Test polling for available tasks."""
        poller = MockTaskPoller(sample_tasks)
        
        # First poll should return the first task
        task = await poller.poll_for_tasks()
        assert task is not None
        assert task["id"] == sample_tasks[0]["id"]
        
        # Claim the first task
        task_id = uuid.UUID(task["id"])
        claimed = await poller.claim_task(task_id)
        assert claimed is True
        
        # Next poll should return the second task
        task = await poller.poll_for_tasks()
        assert task is not None
        assert task["id"] == sample_tasks[1]["id"]
        
        # Claim the second task
        task_id = uuid.UUID(task["id"])
        claimed = await poller.claim_task(task_id)
        assert claimed is True
        
        # No more tasks available
        task = await poller.poll_for_tasks()
        assert task is None
    
    @pytest.mark.asyncio
    async def test_claim_task(self, sample_tasks):
        """Test claiming a task."""
        poller = MockTaskPoller(sample_tasks)
        
        # Claim a task by ID
        task_id = uuid.UUID(sample_tasks[0]["id"])
        claimed = await poller.claim_task(task_id)
        assert claimed is True
        
        # Try to claim the same task again
        claimed = await poller.claim_task(task_id)
        assert claimed is False
        
        # Try to claim a non-existent task
        claimed = await poller.claim_task(uuid.uuid4())
        assert claimed is False
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, sample_tasks):
        """Test updating task status."""
        poller = MockTaskPoller(sample_tasks)
        
        # Claim a task first
        task_id = uuid.UUID(sample_tasks[0]["id"])
        claimed = await poller.claim_task(task_id)
        assert claimed is True
        
        # Update the status
        result = {"message": "Task completed"}
        updated = await poller.update_task_status(task_id, "completed", result=result)
        assert updated is True
        
        # Verify the status was updated
        assert poller.task_statuses[str(task_id)]["status"] == "completed"
        assert poller.task_statuses[str(task_id)]["result"] == result
        
        # Try to update a non-claimed task
        non_claimed_id = uuid.UUID(sample_tasks[1]["id"])
        updated = await poller.update_task_status(non_claimed_id, "completed")
        assert updated is False
        
        # Try to update a non-existent task
        updated = await poller.update_task_status(uuid.uuid4(), "completed")
        assert updated is False
