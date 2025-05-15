"""
Unit tests for the ExecutorAgent class.
"""
import pytest
import uuid
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, Mock, patch

from agents.executor_agent.domain.interfaces import TaskHandler, TaskPollerInterface, ResultStorageInterface
from agents.executor_agent.executor_agent import ExecutorAgent


class MockTaskHandler:
    """Mock task handler for testing."""
    
    def __init__(self, supported_types=None, capabilities=None):
        self._supported_types = supported_types or ["echo", "delay"]
        self._capabilities = capabilities or ["text_processing"]
    
    @property
    def supported_task_types(self) -> List[str]:
        return self._supported_types
    
    @property
    def capabilities(self) -> List[str]:
        return self._capabilities
    
    def can_handle_task(self, task_type: str, parameters: Dict[str, Any]) -> bool:
        return task_type in self._supported_types
    
    async def execute_task(self, task_id: uuid.UUID, task_type: str,
                     parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "echo":
            return {"message": parameters.get("message", "default")}
        elif task_type == "delay":
            await asyncio.sleep(0.1)  # Short delay for testing
            return {"status": "completed", "seconds": parameters.get("seconds", 0)}
        else:
            raise ValueError(f"Unsupported task: {task_type}")


class MockTaskPoller:
    """Mock task poller for testing."""
    
    def __init__(self, tasks=None):
        self.tasks = tasks or []
        self.current_index = 0
        self.claimed_tasks = set()
        self.status_updates = {}
    
    async def poll_for_tasks(self) -> Optional[Dict[str, Any]]:
        if not self.tasks or self.current_index >= len(self.tasks):
            return None
        
        task = self.tasks[self.current_index]
        self.current_index += 1
        return task
    
    async def claim_task(self, task_id: uuid.UUID) -> bool:
        task_id_str = str(task_id)
        for task in self.tasks:
            if task["id"] == task_id_str:
                self.claimed_tasks.add(task_id_str)
                return True
        return False
    
    async def update_task_status(self, task_id: uuid.UUID, status: str,
                           result: Optional[Dict[str, Any]] = None,
                           error: Optional[str] = None) -> bool:
        task_id_str = str(task_id)
        if task_id_str in self.claimed_tasks:
            self.status_updates[task_id_str] = {
                "status": status,
                "result": result,
                "error": error
            }
            return True
        return False


class MockResultStorage:
    """Mock result storage for testing."""
    
    def __init__(self):
        self.results = {}
    
    async def store_result(self, task_id: uuid.UUID, result: Dict[str, Any]) -> str:
        reference = f"result:{str(task_id)}"
        self.results[reference] = result
        return reference
    
    async def get_result(self, reference: str) -> Dict[str, Any]:
        return self.results.get(reference, {})


class TestExecutorAgent:
    """Tests for the ExecutorAgent class."""
    
    @pytest.fixture
    def sample_tasks(self):
        """Generate sample tasks for testing."""
        return [
            {
                "id": str(uuid.uuid4()),
                "task_type": "echo",
                "parameters": {"message": "Test message"},
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "task_type": "delay",
                "parameters": {"seconds": 1},
                "status": "pending"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_register_handler(self):
        """Test registering a task handler."""
        agent = ExecutorAgent(executor_id="test-executor")
        handler = MockTaskHandler()
        
        # Register the handler
        agent.register_handler(handler)
        
        # Verify that the handler's task types were registered
        assert "echo" in agent.supported_task_types
        assert "delay" in agent.supported_task_types
        
        # Verify that the handler's capabilities were registered
        assert "text_processing" in agent.capabilities
        
        # Verify that the handler was stored for each task type
        assert agent.registered_handlers["echo"] == handler
        assert agent.registered_handlers["delay"] == handler
    
    @pytest.mark.asyncio
    async def test_execution_cycle(self, sample_tasks):
        """Test the execution cycle of polling, claiming, and executing a task."""
        # Create mocks
        poller = MockTaskPoller(sample_tasks)
        handler = MockTaskHandler()
        storage = MockResultStorage()
        
        # Create agent with mocks
        agent = ExecutorAgent(
            executor_id="test-executor",
            task_poller=poller,
            result_storage=storage
        )
        agent.register_handler(handler)
        
        # Mock the _execution_cycle method to run just once
        original_cycle = agent._execution_cycle
        
        async def run_once():
            await original_cycle()
            agent.shutdown_requested = True
        
        agent._execution_cycle = run_once
        
        # Run the agent
        await agent.start()
        
        # Verify that the task was claimed
        assert sample_tasks[0]["id"] in poller.claimed_tasks
        
        # Verify that the task status was updated
        assert sample_tasks[0]["id"] in poller.status_updates
        assert poller.status_updates[sample_tasks[0]["id"]]["status"] == "completed"
        
        # Verify that a result was stored
        result_ref = f"result:{sample_tasks[0]['id']}"
        assert result_ref in storage.results
        assert "message" in storage.results[result_ref]
        assert storage.results[result_ref]["message"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_get_handler_for_task(self):
        """Test getting the appropriate handler for a task."""
        # Create agent with two handlers
        agent = ExecutorAgent(executor_id="test-executor")
        
        # Register handlers with different supported task types
        handler1 = MockTaskHandler(supported_types=["echo"], capabilities=["text"])
        handler2 = MockTaskHandler(supported_types=["delay"], capabilities=["time"])
        
        agent.register_handler(handler1)
        agent.register_handler(handler2)
        
        # Test getting handler for echo task
        handler = agent._get_handler_for_task("echo", {})
        assert handler == handler1
        
        # Test getting handler for delay task
        handler = agent._get_handler_for_task("delay", {})
        assert handler == handler2
        
        # Test getting handler for unknown task
        handler = agent._get_handler_for_task("unknown", {})
        assert handler is None
    
    @pytest.mark.asyncio
    async def test_metrics_update(self, sample_tasks):
        """Test that metrics are updated correctly."""
        # Create mocks
        poller = MockTaskPoller(sample_tasks[:1])  # Just one task to keep it simple
        handler = MockTaskHandler()
        
        # Create agent with mocks
        agent = ExecutorAgent(
            executor_id="test-executor",
            task_poller=poller
        )
        agent.register_handler(handler)
        
        # Initial metrics should be zero
        assert agent.metrics["tasks_processed"] == 0
        assert agent.metrics["tasks_succeeded"] == 0
        
        # Mock the _execution_cycle method to run just once
        original_cycle = agent._execution_cycle
        
        async def run_once():
            await original_cycle()
            agent.shutdown_requested = True
        
        agent._execution_cycle = run_once
        
        # Run the agent
        await agent.start()
        
        # Verify metrics were updated
        assert agent.metrics["tasks_processed"] == 1
        assert agent.metrics["tasks_succeeded"] == 1
        assert agent.metrics["tasks_failed"] == 0
        assert agent.metrics["avg_execution_time_ms"] > 0
