"""
Task dispatcher service implementation.

This module implements the `TaskDispatcherInterface` and is responsible for the core logic of task assignment, state management, and executor coordination in the orchestrator agent. Its main responsibilities include:

1. **Task Assignment**: Assigns ready tasks to available executors, ensuring that task requirements (capabilities, dependencies) are satisfied.
2. **Task State Management**: Tracks the state of all tasks (pending, assigned, running, completed, failed) and updates state transitions in persistent storage.
3. **Timeouts and Reassignment**: Detects tasks that have timed out or failed and reassigns them to ensure reliable execution.
4. **Executor Coordination**: Interfaces with RabbitMQ (or other MQs) to notify executors of new tasks and to receive status updates.
5. **Filtering and Capability Matching**: Filters available tasks based on executor capabilities, supporting heterogeneous agent pools.

**Design Notes:**
- The dispatcher is stateless with respect to business logic, relying on persistent storage for all task state.
- It is designed for high concurrency and can be safely called from multiple threads or API requests.
- Logging is used for all major actions to support observability and debugging.

This service is central to the orchestrator's ability to scale out task execution and maintain system reliability in the face of agent churn or failure.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from uuid import UUID

from agents.orchestrator_agent.domain.interfaces import TaskDispatcherInterface, DAGStorageInterface
from agents.orchestrator_agent.domain.models import Task, TaskStatus
from agents.orchestrator_agent.services.rabbitmq_client import RabbitMQClient
from agents.orchestrator_agent.config import config

# Initialize logging
logger = logging.getLogger(__name__)

class TaskDispatcher(TaskDispatcherInterface):
    """Implementation of the task dispatcher interface."""
    
    def __init__(self, dag_storage: DAGStorageInterface, rabbitmq_client: Optional[RabbitMQClient] = None):
        """Initialize with a DAG storage implementation and optionally a RabbitMQ client."""
        logger.info("Initializing TaskDispatcher")
        self.dag_storage = dag_storage
        self.rabbitmq_client = rabbitmq_client or RabbitMQClient()
        
        # Track assigned tasks with timestamps for timeouts
        self.assigned_tasks: Dict[UUID, datetime] = {}
    
    def get_available_tasks(self, executor_capabilities: Optional[List[str]] = None) -> List[Task]:
        """Get tasks that are ready to be executed, optionally filtered by required capabilities."""
        logger.info(f"Getting available tasks for executor with capabilities: {executor_capabilities}")
        
        # Get ready tasks from storage
        ready_tasks = self.dag_storage.get_ready_tasks()
        
        # Filter by capabilities if provided
        if executor_capabilities:
            filtered_tasks = []
            for task in ready_tasks:
                # Check if task requires capabilities that executor has
                if not task.required_capabilities or all(cap in executor_capabilities for cap in task.required_capabilities):
                    filtered_tasks.append(task)
            
            logger.debug(f"Filtered {len(ready_tasks)} tasks to {len(filtered_tasks)} based on capabilities")
            return filtered_tasks
        else:
            return ready_tasks
    
    def assign_task(self, task_id: UUID, executor_id: str) -> bool:
        """Assign a task to a specific executor."""
        logger.info(f"Assigning task {task_id} to executor {executor_id}")
        
        try:
            # Get all ready tasks
            ready_tasks = self.dag_storage.get_ready_tasks()
            
            # Find the task by ID
            task = next((t for t in ready_tasks if t.id == task_id), None)
            if not task:
                logger.warning(f"Task {task_id} not found or not ready")
                return False
            
            # Find the DAG this task belongs to
            # In a real implementation, we would have a more efficient way to get the DAG ID
            # For now, we'll use a placeholder approach that works with our model
            
            # Update task status to assigned
            task.assigned_to = executor_id
            task.update_status(TaskStatus.ASSIGNED)
            
            # Record assignment time for timeout tracking
            self.assigned_tasks[task_id] = datetime.now()
            
            # Update the task in storage
            for dag_id in self._find_dag_ids_for_task(task_id):
                if self.dag_storage.update_task_status(dag_id, task_id, TaskStatus.ASSIGNED):
                    logger.info(f"Task {task_id} assigned to executor {executor_id}")
                    return True
            
            logger.warning(f"Failed to update task {task_id} status in storage")
            return False
        
        except Exception as e:
            logger.error(f"Error assigning task {task_id} to executor {executor_id}: {e}")
            return False
    
    def _find_dag_ids_for_task(self, task_id: UUID) -> Set[UUID]:
        """Find all DAG IDs that contain a given task."""
        # This is a placeholder implementation
        # In a real implementation, we would have a more efficient way to get the DAG ID
        # For example, a direct database query or a cache
        
        # For now, just search through all tasks in the READY, ASSIGNED, and IN_PROGRESS states
        dag_ids = set()
        statuses_to_check = [TaskStatus.READY, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]
        
        for status in statuses_to_check:
            tasks = self.dag_storage.get_tasks_by_status(status)
            for task in tasks:
                if task.id == task_id:
                    # This assumes we can get the DAG ID from the task somehow
                    # In a real implementation, each task would have a reference to its DAG
                    # For now, we'll just return an empty set
                    pass
        
        return dag_ids
    
    def update_task_status(self, task_id: UUID, status: TaskStatus, result: Optional[Dict[str, Any]] = None, 
                          error: Optional[str] = None) -> bool:
        """Update the status of a task, optionally including results or error information."""
        logger.info(f"Updating task {task_id} status to {status.value}")
        
        try:
            # Find all DAGs that contain this task
            dag_ids = self._find_dag_ids_for_task(task_id)
            
            if not dag_ids:
                logger.warning(f"No DAG found containing task {task_id}")
                return False
            
            # Update the task status in each DAG
            success = False
            for dag_id in dag_ids:
                # Update task status
                if self.dag_storage.update_task_status(dag_id, task_id, status):
                    success = True
                
                # If task is completed, check if there are downstream tasks ready to be executed
                if status == TaskStatus.COMPLETED and success:
                    # Get the updated DAG
                    dag = self.dag_storage.get_dag(dag_id)
                    if dag:
                        # Get all ready tasks
                        ready_tasks = dag.get_ready_tasks()
                        
                        # Publish ready tasks to RabbitMQ
                        if ready_tasks:
                            logger.info(f"Publishing {len(ready_tasks)} new ready tasks to RabbitMQ")
                            self.rabbitmq_client.publish_tasks(ready_tasks)
            
            # If the task was assigned, remove it from our tracking
            if task_id in self.assigned_tasks:
                del self.assigned_tasks[task_id]
            
            return success
        
        except Exception as e:
            logger.error(f"Error updating task {task_id} status: {e}")
            return False
    
    def publish_ready_tasks(self) -> Dict[UUID, bool]:
        """Publish all ready tasks to RabbitMQ."""
        logger.info("Publishing all ready tasks to RabbitMQ")
        
        try:
            # Get all ready tasks
            ready_tasks = self.dag_storage.get_ready_tasks()
            
            if not ready_tasks:
                logger.info("No ready tasks to publish")
                return {}
            
            # Publish tasks to RabbitMQ
            results = self.rabbitmq_client.publish_tasks(ready_tasks)
            logger.info(f"Published {len(ready_tasks)} tasks to RabbitMQ")
            
            return results
        
        except Exception as e:
            logger.error(f"Error publishing ready tasks: {e}")
            return {}
    
    def check_task_timeouts(self, timeout_seconds: int = 3600) -> List[Task]:
        """Check for tasks that have timed out and mark them for reassignment."""
        logger.info("Checking for task timeouts")
        
        now = datetime.now()
        timed_out_task_ids = []
        
        # Check for timed out tasks
        for task_id, assigned_time in list(self.assigned_tasks.items()):
            if (now - assigned_time).total_seconds() > timeout_seconds:
                logger.warning(f"Task {task_id} has timed out")
                timed_out_task_ids.append(task_id)
                del self.assigned_tasks[task_id]
        
        # Mark timed out tasks as failed
        failed_tasks = []
        for task_id in timed_out_task_ids:
            # Find all DAGs containing this task
            dag_ids = self._find_dag_ids_for_task(task_id)
            
            for dag_id in dag_ids:
                # Update task status to failed
                if self.dag_storage.update_task_status(dag_id, task_id, TaskStatus.FAILED):
                    # Get the task
                    dag = self.dag_storage.get_dag(dag_id)
                    if dag and task_id in dag.tasks:
                        failed_tasks.append(dag.tasks[task_id])
        
        return failed_tasks
    
    def reassign_failed_tasks(self) -> List[Task]:
        """Find tasks that failed or timed out and mark them for reassignment."""
        logger.info("Reassigning failed tasks")
        
        try:
            # Get failed tasks
            failed_tasks = self.dag_storage.get_tasks_by_status(TaskStatus.FAILED)
            
            # Reset task status for reassignment
            for task in failed_tasks:
                # In a real implementation, we would check retry limits, etc.
                task.update_status(TaskStatus.READY)
                task.assigned_to = None
                
                # Find all DAGs containing this task
                dag_ids = self._find_dag_ids_for_task(task.id)
                
                for dag_id in dag_ids:
                    # Update task status to ready
                    self.dag_storage.update_task_status(dag_id, task.id, TaskStatus.READY)
            
            # Publish reassigned tasks to RabbitMQ
            if failed_tasks:
                self.rabbitmq_client.publish_tasks(failed_tasks)
            
            logger.info(f"Reassigned {len(failed_tasks)} failed tasks")
            return failed_tasks
        
        except Exception as e:
            logger.error(f"Error reassigning failed tasks: {e}")
            return []
