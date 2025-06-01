"""
Domain models for the orchestrator agent.
These models form the core business logic of the DAG-based workflow system.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from uuid import UUID, uuid4

class TaskStatus(Enum):
    """Enum representing the possible states of a task in the DAG."""
    PENDING = "pending"
    READY = "ready"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """Represents an atomic unit of work in the system."""
    
    def __init__(
        self,
        id: UUID = None,
        name: str = "",
        description: str = "",
        task_type: str = "generic",
        parameters: Dict[str, Any] = None,
        estimated_complexity: int = 1,
        required_capabilities: List[str] = None,
        status: TaskStatus = TaskStatus.PENDING,
        assigned_to: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        timeout_seconds: int = 3600,
    ):
        """Initialize a new Task."""
        self.id = id if id else uuid4()
        self.name = name
        self.description = description
        self.task_type = task_type
        self.parameters = parameters or {}
        self.estimated_complexity = estimated_complexity
        self.required_capabilities = required_capabilities or []
        self.status = status
        self.assigned_to = assigned_to
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.result = result
        self.error = error
        self.timeout_seconds = timeout_seconds
        # Internal tracking of dependency relationships
        self._upstream_tasks: Set[UUID] = set()
        self._downstream_tasks: Set[UUID] = set()

    def add_upstream_task(self, task_id: UUID) -> None:
        """Add a task as a dependency for this task."""
        self._upstream_tasks.add(task_id)
    
    def add_downstream_task(self, task_id: UUID) -> None:
        """Add a task that depends on this task."""
        self._downstream_tasks.add(task_id)
    
    def is_ready(self) -> bool:
        """Check if this task is ready to be executed (all dependencies completed)."""
        return not self._upstream_tasks and self.status == TaskStatus.PENDING
    
    def update_status(self, new_status: TaskStatus) -> None:
        """Update the task status and the updated_at timestamp."""
        self.status = new_status
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "parameters": self.parameters,
            "estimated_complexity": self.estimated_complexity,
            "required_capabilities": self.required_capabilities,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "result": self.result,
            "error": self.error,
            "timeout_seconds": self.timeout_seconds,
            "upstream_tasks": [str(task_id) for task_id in self._upstream_tasks],
            "downstream_tasks": [str(task_id) for task_id in self._downstream_tasks]
        }


class DAG:
    """Represents a Directed Acyclic Graph of tasks forming a workflow."""
    
    def __init__(
        self,
        id: UUID = None,
        name: str = "",
        description: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        version: int = 1
    ):
        """Initialize a new DAG."""
        self.id = id if id else uuid4()
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.version = version
        self.tasks: Dict[UUID, Task] = {}
    
    def add_task(self, task: Task) -> None:
        """Add a task to the DAG."""
        self.tasks[task.id] = task
        self.updated_at = datetime.now()
    
    def add_dependency(self, upstream_task_id: UUID, downstream_task_id: UUID) -> None:
        """Create a dependency relationship between two tasks."""
        if upstream_task_id not in self.tasks or downstream_task_id not in self.tasks:
            raise ValueError("Both tasks must be in the DAG")
        
        # Add bidirectional reference
        self.tasks[upstream_task_id].add_downstream_task(downstream_task_id)
        self.tasks[downstream_task_id].add_upstream_task(upstream_task_id)
        self.updated_at = datetime.now()
    
    def get_ready_tasks(self) -> List[Task]:
        """Get all tasks that are ready to be executed."""
        return [task for task in self.tasks.values() if task.is_ready()]
    
    def update_task_status(self, task_id: UUID, status: TaskStatus) -> None:
        """Update a task's status and potentially mark downstream tasks as ready."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not in DAG")
        
        task = self.tasks[task_id]
        task.update_status(status)
        
        # If task completed, remove it as a dependency from downstream tasks
        if status == TaskStatus.COMPLETED:
            for downstream_id in task._downstream_tasks:
                if downstream_id in self.tasks:
                    downstream_task = self.tasks[downstream_id]
                    downstream_task._upstream_tasks.remove(task_id)
    
    def validate(self) -> bool:
        """Validate the DAG for circular dependencies."""
        # Implementation of cycle detection algorithm
        # Simple DFS-based implementation
        visited = set()
        temp_visited = set()
        
        def has_cycle(node_id):
            """DFS helper to detect cycles."""
            if node_id in temp_visited:
                return True
            if node_id in visited:
                return False
            
            temp_visited.add(node_id)
            task = self.tasks[node_id]
            
            for downstream_id in task._downstream_tasks:
                if downstream_id in self.tasks and has_cycle(downstream_id):
                    return True
            
            temp_visited.remove(node_id)
            visited.add(node_id)
            return False
        
        for task_id in self.tasks:
            if task_id not in visited and has_cycle(task_id):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DAG to dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "tasks": [task.to_dict() for task in self.tasks.values()]
        }


class Query:
    """Represents a user query/request that generates a workflow."""
    
    def __init__(
        self,
        id: UUID = None,
        content: str = "",
        user_id: Optional[str] = None,
        meta: Dict[str, Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        status: str = "pending",
        dag_id: Optional[UUID] = None
    ):
        """Initialize a new Query."""
        self.id = id if id else uuid4()
        self.content = content
        self.user_id = user_id
        self.meta = meta or {}
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.status = status
        self.dag_id = dag_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary representation."""
        return {
            "id": str(self.id),
            "content": self.content,
            "user_id": self.user_id,
            "meta": self.meta,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "dag_id": str(self.dag_id) if self.dag_id else None
        }
