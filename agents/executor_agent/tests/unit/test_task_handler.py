"""
Unit tests for TaskHandler implementation.
"""
import pytest
import uuid
from typing import Dict, List, Any
from unittest.mock import AsyncMock

from agents.executor_agent.domain.interfaces import TaskHandler


class SimpleTaskHandler:
    """A simple implementation of the TaskHandler protocol for testing."""
    
    @property
    def supported_task_types(self) -> List[str]:
        return ["echo", "delay"]
    
    @property
    def capabilities(self) -> List[str]:
        return ["text_processing", "time_management"]
    
    def can_handle_task(self, task_type: str, parameters: Dict[str, Any]) -> bool:
        return task_type in self.supported_task_types
    
    async def execute_task(self, task_id: uuid.UUID, task_type: str,
                     parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "echo":
            return {"message": parameters.get("message", "Hello, world!")}
        elif task_type == "delay":
            return {"status": "delayed", "seconds": parameters.get("seconds", 1)}
        else:
            raise ValueError(f"Unsupported task type: {task_type}")


class TestTaskHandler:
    """Tests for the TaskHandler protocol implementation."""
    
    def test_protocol_conformance(self):
        """Test that our implementation conforms to the TaskHandler protocol."""
        handler = SimpleTaskHandler()
        # This will raise a TypeError if the class doesn't implement the protocol
        assert isinstance(handler, TaskHandler)
    
    def test_supported_task_types(self):
        """Test that the handler returns the correct supported task types."""
        handler = SimpleTaskHandler()
        assert "echo" in handler.supported_task_types
        assert "delay" in handler.supported_task_types
        assert len(handler.supported_task_types) == 2
    
    def test_capabilities(self):
        """Test that the handler returns the correct capabilities."""
        handler = SimpleTaskHandler()
        assert "text_processing" in handler.capabilities
        assert "time_management" in handler.capabilities
        assert len(handler.capabilities) == 2
    
    def test_can_handle_task(self):
        """Test that the handler correctly identifies tasks it can handle."""
        handler = SimpleTaskHandler()
        assert handler.can_handle_task("echo", {})
        assert handler.can_handle_task("delay", {"seconds": 5})
        assert not handler.can_handle_task("unknown_task", {})
    
    @pytest.mark.asyncio
    async def test_execute_echo_task(self):
        """Test executing an echo task."""
        handler = SimpleTaskHandler()
        task_id = uuid.uuid4()
        parameters = {"message": "Test message"}
        context = {"executor_id": "test_executor"}
        
        result = await handler.execute_task(task_id, "echo", parameters, context)
        
        assert "message" in result
        assert result["message"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_execute_delay_task(self):
        """Test executing a delay task."""
        handler = SimpleTaskHandler()
        task_id = uuid.uuid4()
        parameters = {"seconds": 3}
        context = {"executor_id": "test_executor"}
        
        result = await handler.execute_task(task_id, "delay", parameters, context)
        
        assert "status" in result
        assert result["status"] == "delayed"
        assert result["seconds"] == 3
    
    @pytest.mark.asyncio
    async def test_execute_unsupported_task(self):
        """Test that executing an unsupported task raises an error."""
        handler = SimpleTaskHandler()
        task_id = uuid.uuid4()
        parameters = {}
        context = {"executor_id": "test_executor"}
        
        with pytest.raises(ValueError):
            await handler.execute_task(task_id, "unsupported", parameters, context)
