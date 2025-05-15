"""
Interfaces defining the contracts for services in the executor agent.
Following clean architecture principles, this separates the interface from implementation.

This module contains the core abstractions used throughout the executor agent system:
1. ExecutorStatus - Enumeration of all possible agent states
2. TaskHandler - Protocol defining how task handlers should be implemented
3. TaskPollerInterface - Abstract base class for task polling services
4. ResultStorageInterface - Abstract base class for result storage mechanisms

These abstractions allow the executor agent to be extended with new functionality
without changing the core logic, promoting a modular and maintainable architecture.
Each interface represents a clear contract that implementations must fulfill,
enabling dependency inversion and easier testing.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Protocol, runtime_checkable
from uuid import UUID


class ExecutorStatus(Enum):
    """
    Enum representing the possible operational states of an executor agent.
    
    These states are used for monitoring, logging, and coordinating behavior
    across the executor agent's lifecycle.
    
    States:
        IDLE: The executor is waiting for tasks but not actively polling
        POLLING: The executor is actively checking for new tasks
        EXECUTING: The executor is currently processing a task
        ERROR: The executor has encountered an error requiring attention
        SHUTDOWN: The executor is in the process of shutting down or has shut down
    """
    IDLE = "idle"         # Waiting for next polling cycle
    POLLING = "polling"   # Actively checking for new tasks
    EXECUTING = "executing"  # Processing a task
    ERROR = "error"       # Encountered an error
    SHUTDOWN = "shutdown"  # Shutting down or terminated


@runtime_checkable
class TaskHandler(Protocol):
    """
    Protocol defining the contract for task handlers that can execute specific task types.
    
    Task handlers are responsible for implementing the actual business logic needed
    to process different types of tasks. The executor agent uses this protocol to
    determine which handler to use for a given task, and to execute tasks in a
    standardized way.
    
    This is defined as a Protocol (rather than ABC) to allow for structural subtyping,
    making it easier to integrate existing classes as handlers without explicit inheritance.
    The @runtime_checkable decorator allows isinstance() checks against this protocol.
    """
    
    @property
    def supported_task_types(self) -> List[str]:
        """
        Get the task types supported by this handler.
        
        Returns:
            List[str]: A list of task type identifiers (e.g., ["echo", "transform", "analyze"]) 
                that this handler can process. The executor uses this to route tasks to 
                the appropriate handler.
        """
        ...
    
    @property
    def capabilities(self) -> List[str]:
        """
        Get the capabilities provided by this handler.
        
        Returns:
            List[str]: A list of capability identifiers (e.g., ["text_processing", 
                "image_analysis"]) that describe what this handler can do. These are
                used for matching tasks to executors at the orchestration level.
        """
        ...
    
    def can_handle_task(self, task_type: str, parameters: Dict[str, Any]) -> bool:
        """
        Check if this handler can execute the given task type with the provided parameters.
        
        This allows for more fine-grained control than just checking the task type.
        For example, a handler might support the "transform" task type but only for
        certain parameter combinations.
        
        Args:
            task_type: The type of task to be executed
            parameters: The parameters for the task execution
            
        Returns:
            bool: True if this handler can execute the task, False otherwise
        """
        ...
    
    async def execute_task(self, task_id: UUID, task_type: str, 
                     parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the task and return the result.
        
        This is the core method that actually performs the task's work.
        
        Args:
            task_id: Unique identifier for the task
            task_type: The type of task to be executed
            parameters: The parameters for the task execution
            context: Additional context information that might be needed for execution
                    (e.g., executor_id, upstream_results, timestamps)
            
        Returns:
            Dict[str, Any]: The result of the task execution
            
        Raises:
            ValueError: If the task type or parameters are invalid
            Exception: Any exception that occurs during task execution
        """
        ...


class TaskPollerInterface(ABC):
    """
    Abstract interface for retrieving tasks from the orchestrator.
    
    The TaskPoller is responsible for the communication between the executor agent
    and the orchestration system. It handles:
    1. Polling for available tasks that match the executor's capabilities
    2. Claiming tasks for execution to prevent other executors from working on them
    3. Updating task status and results after execution
    
    This interface abstracts away the details of how tasks are communicated, allowing
    for different implementations (e.g., HTTP API, message queue, direct database).
    """
    
    @abstractmethod
    async def poll_for_tasks(self) -> Optional[Dict[str, Any]]:
        """
        Poll for available tasks matching this executor's capabilities.
        
        This method is called periodically by the executor agent to check
        if there are any new tasks that this executor can work on.
        
        Returns:
            Optional[Dict[str, Any]]: A task representation if one is available,
                or None if no suitable tasks are available. The task should include
                at minimum: id, task_type, parameters, and status.
                
        Raises:
            ConnectionError: If unable to connect to the task source
            Exception: For any other issues that prevent polling
        """
        pass
    
    @abstractmethod
    async def claim_task(self, task_id: UUID) -> bool:
        """
        Attempt to claim a task for execution.
        
        Claiming a task signifies that this executor is taking responsibility
        for executing it, preventing other executors from working on the same task.
        
        Args:
            task_id: The unique identifier of the task to claim
            
        Returns:
            bool: True if the claim was successful, False if the task was already
                claimed by another executor or is no longer available
                
        Raises:
            ConnectionError: If unable to connect to the task source
            Exception: For any other issues that prevent claiming
        """
        pass
    
    @abstractmethod
    async def update_task_status(self, task_id: UUID, status: str, 
                           result: Optional[Dict[str, Any]] = None,
                           error: Optional[str] = None) -> bool:
        """
        Update the status of a task, optionally including results or error information.
        
        This method is called after a task has been executed (successfully or not)
        to report the outcome back to the orchestration system.
        
        Args:
            task_id: The unique identifier of the task to update
            status: The new status of the task (e.g., "completed", "failed")
            result: Optional result data from successful execution
            error: Optional error message if execution failed
            
        Returns:
            bool: True if the update was successful, False otherwise
            
        Raises:
            ConnectionError: If unable to connect to the task source
            Exception: For any other issues that prevent updating
        """
        pass


class ResultStorageInterface(ABC):
    """
    Abstract interface for storing task execution results.
    
    This interface allows the executor agent to store large task results
    in external storage systems and reference them by ID rather than
    including full results in task status updates. This is particularly
    important for tasks that generate large outputs (e.g., files, images,
    extensive text, or complex data structures).
    
    Implementations of this interface could store results in:
    - Local file system
    - Cloud object storage (S3, GCS, etc.)
    - Database (SQL or NoSQL)
    - Specialized storage services (e.g., Supabase)
    """
    
    @abstractmethod
    async def store_result(self, task_id: UUID, result: Dict[str, Any]) -> str:
        """
        Store task execution results in a specialized storage system.
        
        Args:
            task_id: The unique identifier of the task whose result is being stored
            result: The result data to store
            
        Returns:
            str: A reference ID or URL that can be used to retrieve the result.
                 This reference is what will be included in task status updates
                 instead of the full result data.
                 
        Raises:
            StorageError: If the result could not be stored
            ConnectionError: If unable to connect to the storage system
            Exception: For any other issues that prevent storing the result
        """
        pass
    
    @abstractmethod
    async def get_result(self, reference: str) -> Dict[str, Any]:
        """
        Retrieve task execution results by reference ID or URL.
        
        Args:
            reference: The reference ID or URL returned by store_result
            
        Returns:
            Dict[str, Any]: The retrieved result data
            
        Raises:
            KeyError: If the reference does not exist
            StorageError: If the result could not be retrieved
            ConnectionError: If unable to connect to the storage system
            Exception: For any other issues that prevent retrieving the result
        """
        pass
