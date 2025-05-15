"""
Interfaces defining the contracts for services in the orchestrator agent.
Following the clean architecture principles, this separates the interface from implementation.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from uuid import UUID

from agents.orchestrator_agent.domain.models import DAG, Query, Task, TaskStatus

class QueryServiceInterface(ABC):
    """Interface for query-related operations."""
    
    @abstractmethod
    def create_query(self, content: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Query:
        """Create a new query from user input."""
        pass
    
    @abstractmethod
    def get_query(self, query_id: UUID) -> Optional[Query]:
        """Get a query by ID."""
        pass
    
    @abstractmethod
    def update_query_status(self, query_id: UUID, status: str) -> bool:
        """Update the status of a query."""
        pass
    
    @abstractmethod
    def link_query_to_dag(self, query_id: UUID, dag_id: UUID) -> bool:
        """Link a query to a generated DAG."""
        pass


class DAGPlannerInterface(ABC):
    """Interface for DAG planning operations."""
    
    @abstractmethod
    def create_dag_from_query(self, query: Query) -> DAG:
        """Generate a DAG based on the given query."""
        pass
    
    @abstractmethod
    def validate_dag(self, dag: DAG) -> bool:
        """Validate a DAG for correctness (no cycles, etc.)."""
        pass


class DAGStorageInterface(ABC):
    """Interface for DAG persistence operations."""
    
    @abstractmethod
    def save_dag(self, dag: DAG) -> bool:
        """Save a DAG to storage."""
        pass
    
    @abstractmethod
    def get_dag(self, dag_id: UUID) -> Optional[DAG]:
        """Get a DAG by ID."""
        pass
    
    @abstractmethod
    def update_task_status(self, dag_id: UUID, task_id: UUID, status: TaskStatus) -> bool:
        """Update the status of a task within a DAG."""
        pass
    
    @abstractmethod
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status."""
        pass
    
    @abstractmethod
    def get_ready_tasks(self) -> List[Task]:
        """Get all tasks that are ready to be executed."""
        pass


class TaskDispatcherInterface(ABC):
    """Interface for task dispatch operations."""
    
    @abstractmethod
    def get_available_tasks(self, executor_capabilities: Optional[List[str]] = None) -> List[Task]:
        """Get tasks that are ready to be executed, optionally filtered by required capabilities."""
        pass
    
    @abstractmethod
    def assign_task(self, task_id: UUID, executor_id: str) -> bool:
        """Assign a task to a specific executor."""
        pass
    
    @abstractmethod
    def update_task_status(self, task_id: UUID, status: TaskStatus, result: Optional[Dict[str, Any]] = None, 
                          error: Optional[str] = None) -> bool:
        """Update the status of a task, optionally including results or error information."""
        pass
    
    @abstractmethod
    def reassign_failed_tasks(self) -> List[Task]:
        """Find tasks that failed or timed out and mark them for reassignment."""
        pass
