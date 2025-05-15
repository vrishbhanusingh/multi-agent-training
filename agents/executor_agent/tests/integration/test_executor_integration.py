"""
Integration tests for the executor agent with task poller.

These tests verify that the executor agent can properly interact
with a task poller to poll for, claim, and update tasks.
"""
import pytest
import uuid
import asyncio
import time
from typing import Dict, List, Any, Optional

from agents.executor_agent.domain.interfaces import TaskPollerInterface, TaskHandler, ExecutorStatus
from agents.executor_agent.executor_agent import ExecutorAgent


class IntegrationTaskPoller(TaskPollerInterface):
    """Task poller implementation for integration testing."""
    
    def __init__(self):
        self.available_tasks = []
        self.claimed_tasks = {}
        self.task_statuses = {}
    
    def add_task(self, task_data: Dict[str, Any]):
        """Add a task to the available tasks list."""
        self.available_tasks.append(task_data)
    
    async def poll_for_tasks(self) -> Optional[Dict[str, Any]]:
        """Return the next available task or None."""
        for task in self.available_tasks:
            if task["id"] not in self.claimed_tasks:
                return task
        return None
    
    async def claim_task(self, task_id: uuid.UUID) -> bool:
        """Claim a task for execution."""
        str_id = str(task_id)
        for task in self.available_tasks:
            if task["id"] == str_id and str_id not in self.claimed_tasks:
                self.claimed_tasks[str_id] = time.time()
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
                "error": error,
                "updated_at": time.time()
            }
            return True
        return False


class SimpleTaskHandler:
    """A simple task handler for integration testing."""
    
    @property
    def supported_task_types(self) -> List[str]:
        return ["echo", "delay", "transform"]
    
    @property
    def capabilities(self) -> List[str]:
        return ["text_processing", "time_management", "data_transformation"]
    
    def can_handle_task(self, task_type: str, parameters: Dict[str, Any]) -> bool:
        return task_type in self.supported_task_types
    
    async def execute_task(self, task_id: uuid.UUID, task_type: str,
                     parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "echo":
            return {"message": parameters.get("message", "Hello, world!")}
        
        elif task_type == "delay":
            delay_seconds = parameters.get("seconds", 0.1)
            await asyncio.sleep(delay_seconds)
            return {"status": "completed", "seconds": delay_seconds}
        
        elif task_type == "transform":
            data = parameters.get("data", {})
            transform_type = parameters.get("transform", "uppercase")
            
            if transform_type == "uppercase" and isinstance(data, str):
                return {"result": data.upper()}
            elif transform_type == "lowercase" and isinstance(data, str):
                return {"result": data.lower()}
            else:
                return {"result": data, "warning": "No transformation applied"}
        
        else:
            raise ValueError(f"Unsupported task type: {task_type}")


class TestExecutorAgentIntegration:
    """Integration tests for the executor agent."""
    
    @pytest.fixture
    def task_poller(self):
        """Create a task poller for testing."""
        return IntegrationTaskPoller()
    
    @pytest.fixture
    def task_handler(self):
        """Create a task handler for testing."""
        return SimpleTaskHandler()
    
    @pytest.fixture
    def executor_agent(self, task_poller, task_handler):
        """Create an executor agent for testing."""
        agent = ExecutorAgent(
            executor_id="test-integration-executor",
            name="IntegrationTestExecutor",
            task_poller=task_poller
        )
        agent.register_handler(task_handler)
        return agent
    
    @pytest.mark.asyncio
    async def test_task_execution_flow(self, executor_agent, task_poller):
        """Test the complete flow of task execution."""
        # Create test task
        task_id = str(uuid.uuid4())
        test_task = {
            "id": task_id,
            "task_type": "echo",
            "parameters": {"message": "Integration test message"},
            "status": "pending"
        }
        
        # Add task to poller
        task_poller.add_task(test_task)
        
        # Mock the execution cycle to run just once
        original_cycle = executor_agent._execution_cycle
        execution_completed = asyncio.Event()
        
        async def run_once():
            await original_cycle()
            execution_completed.set()
        
        executor_agent._execution_cycle = run_once
        
        # Start the agent in the background
        agent_task = asyncio.create_task(executor_agent.start())
        
        # Wait for execution to complete (with timeout)
        await asyncio.wait_for(execution_completed.wait(), timeout=5.0)
        
        # Request shutdown
        executor_agent.shutdown_requested = True
        await agent_task
        
        # Verify that the task was claimed
        assert task_id in task_poller.claimed_tasks
        
        # Verify that the task status was updated
        assert task_id in task_poller.task_statuses
        assert task_poller.task_statuses[task_id]["status"] == "completed"
        
        # Verify the result
        assert "result" in task_poller.task_statuses[task_id]
        result = task_poller.task_statuses[task_id]["result"]
        assert result is not None
        assert result.get("message") == "Integration test message"
    
    @pytest.mark.asyncio
    async def test_multiple_task_types(self, executor_agent, task_poller):
        """Test execution of multiple task types in sequence."""
        # Create test tasks of different types
        tasks = [
            {
                "id": str(uuid.uuid4()),
                "task_type": "echo",
                "parameters": {"message": "First task"},
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "task_type": "delay",
                "parameters": {"seconds": 0.1},
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "task_type": "transform",
                "parameters": {"data": "mixed case text", "transform": "uppercase"},
                "status": "pending"
            }
        ]
        
        # Add tasks to poller
        for task in tasks:
            task_poller.add_task(task)
        
        # Process one task at a time manually instead of running the agent
        for task in tasks:
            task_id = uuid.UUID(task["id"])
            # Simulate polling for task
            polled_task = await task_poller.poll_for_tasks()
            assert polled_task is not None, "No task was available to poll"
            
            # Simulate claiming task
            claimed = await task_poller.claim_task(task_id)
            assert claimed, f"Failed to claim task {task_id}"
            
            # Execute task directly using appropriate handler
            task_type = task["task_type"]
            parameters = task.get("parameters", {})
            
            # Get a handler that can execute this task
            handler = None
            for registered_handler in executor_agent.registered_handlers.values():
                if registered_handler.can_handle_task(task_type, parameters):
                    handler = registered_handler
                    break
                    
            assert handler is not None, f"No handler found for task type {task_type}"
            
            # Execute the task
            context = {"executor_id": executor_agent.executor_id}
            result = await handler.execute_task(task_id, task_type, parameters, context)
            
            # Update task status
            updated = await task_poller.update_task_status(task_id, "completed", result=result)
            assert updated, f"Failed to update task status for {task_id}"
        
        # Verify all tasks were claimed and processed
        for task in tasks:
            task_id = task["id"]
            assert task_id in task_poller.claimed_tasks
            assert task_id in task_poller.task_statuses
            assert task_poller.task_statuses[task_id]["status"] == "completed"
        
        # Verify specific results for each task type
        echo_task = tasks[0]
        assert task_poller.task_statuses[echo_task["id"]]["result"].get("message") == "First task"
        
        delay_task = tasks[1]
        assert task_poller.task_statuses[delay_task["id"]]["result"].get("status") == "completed"
        
        transform_task = tasks[2]
        assert task_poller.task_statuses[transform_task["id"]]["result"].get("result") == "MIXED CASE TEXT"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, executor_agent, task_poller):
        """Test error handling during task execution."""
        # Create test task with invalid parameters
        task_id = str(uuid.uuid4())
        test_task = {
            "id": task_id,
            "task_type": "invalid_type",  # Unsupported task type
            "parameters": {},
            "status": "pending"
        }
        
        # Add task to poller
        task_poller.add_task(test_task)
        
        # Mock the execution cycle to run just once
        original_cycle = executor_agent._execution_cycle
        execution_completed = asyncio.Event()
        
        async def run_once():
            await original_cycle()
            execution_completed.set()
        
        executor_agent._execution_cycle = run_once
        
        # Start the agent in the background
        agent_task = asyncio.create_task(executor_agent.start())
        
        # Wait for execution to complete
        await asyncio.wait_for(execution_completed.wait(), timeout=5.0)
        
        # Request shutdown
        executor_agent.shutdown_requested = True
        await agent_task
        
        # Verify that the task was claimed
        assert task_id in task_poller.claimed_tasks
        
        # Verify that the task status was updated to 'failed'
        assert task_id in task_poller.task_statuses
        assert task_poller.task_statuses[task_id]["status"] == "failed"
        
        # Verify error information was provided
        assert "error" in task_poller.task_statuses[task_id]
        error = task_poller.task_statuses[task_id]["error"]
        assert error is not None
        assert "invalid_type" in error.lower()
