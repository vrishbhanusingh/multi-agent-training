"""
Base executor agent implementation that handles common functionality
such as task polling, claiming, execution, and result reporting.

The ExecutorAgent is the central component of the executor subsystem. It:
1. Manages the lifecycle of task execution, from polling to completion
2. Coordinates with the orchestrator through a task poller interface
3. Delegates actual task execution to specialized handlers
4. Tracks performance metrics and operational status
5. Handles failures and recovery gracefully
6. Provides a plugin architecture for extending functionality

This implementation is designed to be robust, handling various edge cases such as:
- Network interruptions during task polling or updating
- Task execution timeouts
- Graceful shutdown on system signals
- Comprehensive error handling and reporting

The agent operates asynchronously for optimal performance and responsiveness.
"""
import logging        # For structured logging throughout the executor
import asyncio        # For asynchronous operation and task management
import time           # For timestamps and duration measurements
import uuid           # For generating unique identifiers
from datetime import datetime, timedelta  # For timing and scheduling operations
from typing import Dict, List, Optional, Any, Set  # Type hints for better code safety
import signal         # For handling system signals (e.g., SIGTERM for graceful shutdown)
import sys            # For system-level interactions
import traceback      # For detailed error reporting

from agents.executor_agent.domain.interfaces import (
    TaskPollerInterface, TaskHandler, ExecutorStatus,
    ResultStorageInterface
)
from agents.executor_agent.config import config

# Initialize logging with the module name for better log filtering and identification
logger = logging.getLogger(__name__)  # Creates a logger specific to this module


class ExecutorAgent:
    """
    Base executor agent that polls for tasks, claims them,
    executes them using registered handlers, and reports results.
    
    The ExecutorAgent is the core operational component that bridges between
    the orchestration system and the actual task execution logic. It maintains
    its operational state, communicates with external systems, delegates task
    execution, and provides operational metrics.
    
    Key responsibilities:
    1. Task Lifecycle Management - Handles the entire task execution lifecycle
    2. Handler Registration - Maintains a registry of task handlers
    3. Task Polling - Actively checks for available tasks that match its capabilities
    4. Task Claiming - Ensures exclusive execution rights for tasks
    5. Task Execution - Delegates execution to specialized handlers
    6. Result Reporting - Updates task status and stores execution results
    7. Error Handling - Manages failures at multiple levels of the execution process
    8. Metrics Collection - Tracks performance and operational metrics
    
    The ExecutorAgent follows a plugin architecture where components like the task
    poller and task handlers can be swapped out or extended without modifying the
    core agent implementation. This enables easy customization for different
    environments and use cases.
    
    The agent is designed to be extensible through task handlers that implement
    specific business logic for different types of tasks, supporting a wide range
    of workloads from simple data processing to complex AI workflows.
    """
    
    def __init__(self, 
                 executor_id: Optional[str] = None, 
                 name: str = "ExecutorAgent",
                 task_poller: Optional[TaskPollerInterface] = None,
                 result_storage: Optional[ResultStorageInterface] = None):
        """
        Initialize a new executor agent with its essential components.
        
        This constructor sets up the agent's identity, communication channels,
        and initializes its operational state. It follows the dependency injection
        pattern for better testability and flexibility.
        
        Args:
            executor_id: Unique ID for this executor. If None, a UUID will be generated.
                This ID is used to identify the executor in logs and when communicating
                with the orchestrator.
            name: Human-readable name for this executor.
                Used primarily for logging and monitoring.
            task_poller: Component for polling and claiming tasks.
                This is the interface to the task source (e.g., API, queue).
                If None, the agent won't be able to poll for tasks until one is set.
            result_storage: Component for storing large task results.
                If None, results will be included directly in task updates
                rather than stored separately.
        """
        # Core identity
        self.executor_id = executor_id or str(uuid.uuid4())  # Ensure we always have a unique ID
        self.name = name  # Human-readable name for logging
        
        # Communication interfaces
        self.task_poller = task_poller  # Interface to task source (orchestrator)
        self.result_storage = result_storage  # Optional storage for large results
        
        # Operational state - tracks the agent's current processing status
        self.status = ExecutorStatus.IDLE  # Start in idle state, ready to poll for new tasks
        
        # Handler registry for task execution - maps task types to specialized handlers
        self.registered_handlers: Dict[str, TaskHandler] = {}  # Maps task types to handlers
        self.supported_task_types: Set[str] = set()  # Set of all task types this agent can process
        self.capabilities: Set[str] = set()  # Set of all capability tags from registered handlers
        
        # Task execution state - tracks what's currently being processed
        self.current_task: Optional[Dict[str, Any]] = None  # Task currently being executed, if any
        self.current_task_start_time: Optional[datetime] = None  # When current task execution started
        
        # Control flags - used to manage the agent's lifecycle
        self.shutdown_requested = False  # Flag to signal graceful shutdown
        
        # Performance metrics - tracks operational statistics for monitoring
        self.metrics = {
            "tasks_processed": 0,      # Total number of tasks processed (success + failure)
            "tasks_succeeded": 0,      # Number of successfully completed tasks
            "tasks_failed": 0,         # Number of failed tasks
            "avg_execution_time_ms": 0,  # Average execution time in milliseconds
            "total_execution_time_ms": 0  # Total execution time in milliseconds
        }
    
    def register_handler(self, handler: TaskHandler) -> None:
        """
        Register a task handler with this executor.
        
        This method adds a handler to the executor's registry, allowing it to process
        the task types supported by the handler. It also records the handler's capabilities
        to inform the task polling system about what this executor can do.
        
        The registry maps specific task types to the handlers that can process them,
        enabling efficient lookup when a task needs to be executed.
        
        Args:
            handler: The task handler to register. Must implement the TaskHandler protocol.
            
        Raises:
            TypeError: If the provided handler doesn't implement the required protocol
            ValueError: If there's a conflict with existing handlers (rare, as later
                       registrations override earlier ones for the same task type)
        """
        # Add task types from this handler to both the registry and supported types set
        for task_type in handler.supported_task_types:
            self.supported_task_types.add(task_type)  # Update the set of all supported types
            
            # Map this task type to this specific handler
            # Note: If multiple handlers support the same task type, the last one registered wins
            self.registered_handlers[task_type] = handler
        
        # Add capabilities from this handler to our capabilities set
        # These capabilities will be used by the orchestrator for task routing
        for capability in handler.capabilities:
            self.capabilities.add(capability)
        
        # Log the registration for monitoring and debugging
        logger.info(f"Registered handler for task types: {handler.supported_task_types}")
    
    async def start(self) -> None:
        """
        Start the executor agent's polling and execution loop.
        
        This is the main entry point for the agent's operation. It:
        1. Sets up signal handlers for graceful shutdown
        2. Starts a background task for metrics reporting
        3. Runs the main execution loop until shutdown is requested
        
        The execution loop continuously polls for tasks, executes them,
        and reports results, with appropriate error handling at each step.
        
        Returns:
            None: This method runs until shutdown is requested
            
        Raises:
            Exception: Any unhandled exceptions during startup (execution loop
                       exceptions are caught and logged)
        """
        logger.info(f"Starting executor agent {self.name} (ID: {self.executor_id})")
        
        # Register signal handlers for graceful shutdown on SIGINT (Ctrl+C) and SIGTERM
        self._setup_signal_handlers()
        
        # Start metrics reporting task as a background coroutine
        # This will periodically log metrics about the agent's performance
        metrics_task = asyncio.create_task(self._report_metrics_periodically())
        
        try:
            # Run the main execution loop until shutdown is requested
            while not self.shutdown_requested:
                # Execute one cycle of the poll-claim-execute workflow
                await self._execution_cycle()
                
                # If we didn't get or process a task, implement a backoff strategy
                # to avoid hammering the task source when no work is available
                if self.status == ExecutorStatus.IDLE:
                    # Wait before polling again, using the configured interval
                    # This prevents tight polling loops that waste resources
                    await asyncio.sleep(config.polling_interval)
        
        except Exception as e:
            # Catch and log any unexpected exceptions in the main loop
            # This prevents the agent from crashing completely on errors
            logger.error(f"Unexpected error in executor agent: {e}")
            logger.error(traceback.format_exc())
            logger.error(traceback.format_exc())
            self.status = ExecutorStatus.ERROR
        
        finally:
            # Cancel metrics reporting
            metrics_task.cancel()
            try:
                await metrics_task
            except asyncio.CancelledError:
                pass
            
            # Final shutdown
            logger.info(f"Executor agent {self.name} shutting down")
            self.status = ExecutorStatus.SHUTDOWN
    
    async def _execution_cycle(self) -> None:
        """
        Run one cycle of the executor's poll-claim-execute loop.
        
        This is the core operational method of the executor agent, implementing
        a complete workflow for task processing:
        1. Poll for an available task matching this executor's capabilities
        2. Attempt to claim the task for exclusive execution
        3. Execute the task using an appropriate handler
        4. Store the result (potentially in external storage)
        5. Update the task status with the orchestrator
        
        Each step has appropriate error handling and state management.
        The method is designed to execute exactly one task per call.
        """
        try:
            # PHASE 1: POLLING - Check for available tasks
            # Update status to indicate we're actively polling
            self.status = ExecutorStatus.POLLING
            
            # Poll for tasks, which may return None if no tasks are available
            task = await self._poll_for_task()
            
            # If no suitable task is available, return to idle state
            # This will trigger a backoff sleep in the main loop
            if not task:
                self.status = ExecutorStatus.IDLE
                return
            
            # PHASE 2: CLAIMING - Try to claim the task for exclusive execution
            # Convert string task ID to UUID for consistent handling
            task_id = uuid.UUID(task["id"])
            
            # Attempt to claim the task - this prevents other executors from working on it
            claimed = await self._claim_task(task_id)
            
            # If claiming failed (e.g., another executor claimed it first), go back to idle
            if not claimed:
                logger.info(f"Failed to claim task {task_id} - another executor may have claimed it")
                self.status = ExecutorStatus.IDLE
                return
            
            # PHASE 3: PREPARATION - Update internal state and prepare for execution
            # Store the current task and update the execution status
            self.current_task = task
            self.status = ExecutorStatus.EXECUTING
            logger.info(f"Starting execution of task {task_id} ({task.get('task_type', 'unknown')})")
            
            # Record the start time for metrics and timeout calculations
            start_time = datetime.now()
            self.current_task_start_time = start_time
            
            try:
                # PHASE 4: HANDLER SELECTION - Find the right handler for this task type
                # Extract the task type, defaulting to "generic" if not specified
                task_type = task.get("task_type", "generic")
                
                # Find a handler that can process this task type with these parameters
                # This uses the registry built during handler registration
                handler = self._get_handler_for_task(task_type, task.get("parameters", {}))
                
                # Fail early if no suitable handler is available
                if not handler:
                    raise ValueError(f"No handler available for task type: {task_type}")
                
                # Prepare execution context with metadata that might be useful for the handler
                # This provides the handler with information about the execution environment
                context = {
                    "executor_id": self.executor_id,  # ID of this executor instance
                    "start_time": start_time.isoformat(),  # When execution started (ISO format)
                    "upstream_results": task.get("upstream_results", {})  # Results from dependent tasks
                }
                
                # PHASE 5: EXECUTION - Actually run the task with a timeout
                # We use asyncio.wait_for to enforce a timeout on task execution
                # This prevents tasks from running indefinitely and blocking the executor
                result = await asyncio.wait_for(
                    # Call the handler's execute_task method with all necessary information
                    handler.execute_task(
                        task_id=task_id,  # Unique identifier for the task
                        task_type=task_type,  # Type of task to execute 
                        parameters=task.get("parameters", {}),  # Task-specific parameters
                        context=context  # Additional execution context
                    ),
                    # Use the configured timeout to prevent infinite execution
                    timeout=config.task_timeout
                )
                
                # PHASE 6: SUCCESS HANDLING - Process successful execution results
                # Calculate execution time for metrics and logging
                end_time = datetime.now()
                execution_time_ms = (end_time - start_time).total_seconds() * 1000
                
                # Update performance metrics with the successful execution
                self._update_metrics(succeeded=True, execution_time_ms=execution_time_ms)
                
                # PHASE 7: RESULT STORAGE - Handle large results if necessary
                # If we have a result storage mechanism configured and actual results to store
                if self.result_storage and result:
                    try:
                        # Store large results in external storage (e.g., file system, S3, database)
                        # and get back a reference that can be used to retrieve them later
                        result_reference = await self.result_storage.store_result(task_id, result)
                        
                        # Replace the full result with just a reference to save bandwidth
                        # and avoid potential size limitations in task status updates
                        result = {"result_reference": result_reference}
                    except Exception as storage_error:
                        # Log the storage error but continue with the inline result
                        # This ensures task completion even if result storage fails
                        logger.warning(f"Failed to store result in external storage: {storage_error}")
                        # The original result will be used as a fallback
                
                # PHASE 8: STATUS UPDATE - Report task completion to orchestrator
                # Update task status in the orchestration system with the result
                await self._update_task_status(task_id, "completed", result=result)
                
                # Log successful completion with timing information for monitoring
                logger.info(f"Task {task_id} completed successfully in {execution_time_ms:.2f}ms")
            
            # ERROR HANDLING - Handle different failure scenarios with appropriate responses
            
            except asyncio.TimeoutError:
                # Handle task timeout - this happens when a task exceeds its allowed execution time
                logger.error(f"Task {task_id} timed out after {config.task_timeout} seconds")
                
                # Report the timeout to the orchestrator with a descriptive error message
                await self._update_task_status(
                    task_id, 
                    "failed",  # Mark the task as failed due to timeout
                    error=f"Task execution timed out after {config.task_timeout} seconds"
                )
                
                # Update metrics to reflect task failure (without execution time)
                self._update_metrics(succeeded=False)
            
            except Exception as e:
                # Handle all other exceptions during task execution
                # Log the error with a full stack trace for debugging
                logger.error(f"Error executing task {task_id}: {e}")
                logger.error(traceback.format_exc())
                
                # Report the failure to the orchestrator with the error message
                await self._update_task_status(
                    task_id,
                    "failed",
                    error=f"Error during execution: {str(e)}"
                )
                
                # Update metrics to reflect task failure
                self._update_metrics(succeeded=False)
            
            finally:
                # PHASE 9: CLEANUP - Reset state regardless of success or failure
                # Clear the current task state to prepare for the next task
                self.current_task = None
                self.current_task_start_time = None
                
                # Return to idle state, ready for the next polling cycle
                self.status = ExecutorStatus.IDLE
        
        except Exception as e:
            # Handle errors in the execution cycle itself (not task-specific errors)
            # This catches issues with polling, claiming, or other agent operations
            logger.error(f"Error in execution cycle: {e}")
            logger.error(traceback.format_exc())
            
            # Set status to ERROR to indicate a problem with the agent itself
            self.status = ExecutorStatus.ERROR
            
            # Wait a bit before retrying to avoid tight error loops that could
            # overwhelm the system or flood logs with repeated errors
            await asyncio.sleep(5)
            
            # Attempt recovery by returning to idle state
            self.status = ExecutorStatus.IDLE
    
    async def _poll_for_task(self) -> Optional[Dict[str, Any]]:
        """
        Poll for an available task matching this executor's capabilities.
        
        This method delegates to the configured task poller to check for
        available tasks that this executor can process. It handles the case
        where no poller is configured and catches any exceptions during polling.
        
        Returns:
            Optional[Dict[str, Any]]: A task representation if one is available,
                or None if no suitable tasks are available or if polling failed.
        """
        # Verify that we have a task poller configured
        if not self.task_poller:
            logger.error("Cannot poll for tasks: no task poller configured")
            return None
        
        try:
            # Delegate to the configured task poller implementation
            # The poller should handle filtering based on this executor's capabilities
            return await self.task_poller.poll_for_tasks()
        except Exception as e:
            # Catch and log any errors during polling (e.g., connection errors)
            logger.error(f"Error polling for tasks: {e}")
            return None
    
    async def _claim_task(self, task_id: uuid.UUID) -> bool:
        """
        Attempt to claim a task for execution.
        
        This method delegates to the configured task poller to claim exclusive
        execution rights for a task. Claiming prevents multiple executors from
        working on the same task simultaneously.
        
        Args:
            task_id: The unique identifier of the task to claim
            
        Returns:
            bool: True if the claim was successful, False if the task could not
                be claimed or if claiming failed for any reason
        """
        # Verify that we have a task poller configured
        if not self.task_poller:
            logger.error("Cannot claim task: no task poller configured")
            return False
        
        try:
            # Delegate to the configured task poller implementation
            # This typically involves a call to the orchestrator API or message queue
            return await self.task_poller.claim_task(task_id)
        except Exception as e:
            # Catch and log any errors during claiming (e.g., connection errors)
            logger.error(f"Error claiming task {task_id}: {e}")
            return False
    
    async def _update_task_status(self, task_id: uuid.UUID, status: str,
                            result: Optional[Dict[str, Any]] = None,
                            error: Optional[str] = None) -> bool:
        """
        Update the status of a task, optionally including results or error information.
        
        This method is called after task execution (successful or not) to report
        the outcome back to the orchestration system. It handles both successful
        completion (with results) and failures (with error information).
        
        Args:
            task_id: The unique identifier of the task being updated
            status: The new status of the task (e.g., "completed", "failed")
            result: Optional result data from successful execution
            error: Optional error message if execution failed
            
        Returns:
            bool: True if the status update was successful, False otherwise
        """
        # Verify that we have a task poller configured
        if not self.task_poller:
            logger.error("Cannot update task status: no task poller configured")
            return False
        
        try:
            # Delegate to the configured task poller implementation
            # This typically involves a call to the orchestrator API or message queue
            return await self.task_poller.update_task_status(
                task_id=task_id,
                status=status,
                result=result,
                error=error
            )
        except Exception as e:
            logger.error(f"Error updating status for task {task_id}: {e}")
            return False
    
    def _get_handler_for_task(self, task_type: str, parameters: Dict[str, Any]) -> Optional[TaskHandler]:
        """
        Get an appropriate handler for the given task type and parameters.
        
        This method implements the handler selection logic, finding the best
        handler for a given task. It first tries an exact match on task type,
        and if that fails it tries to find any handler that can process the task
        based on its can_handle_task method.
        
        Args:
            task_type: The type of task to find a handler for
            parameters: The parameters of the task, used for more specific matching
            
        Returns:
            Optional[TaskHandler]: The appropriate handler if one is found, or None
                if no suitable handler is available
        """
        # STRATEGY 1: Try for an exact task type match first (most efficient)
        if task_type in self.registered_handlers:
            handler = self.registered_handlers[task_type]
            # Verify that the handler can process this specific task instance
            # by checking the parameters (not just the task type)
            if handler.can_handle_task(task_type, parameters):
                return handler
        
        # STRATEGY 2: If no direct match or the matched handler can't handle these parameters,
        # try to find any handler that can process this task based on its dynamic capabilities.
        # This allows for more flexible handler implementations that can accept tasks
        # beyond their primary task types.
        for handler_type, handler in self.registered_handlers.items():
            # Check if this handler can dynamically handle the task based on its parameters
            # even if it's not explicitly registered for this task type
            if handler.can_handle_task(task_type, parameters):
                return handler
        
        # STRATEGY 3: No suitable handler found after trying both strategies
        # The caller will need to handle this case by raising an appropriate error
        return None
    
    def _update_metrics(self, succeeded: bool, execution_time_ms: float = 0) -> None:
        """
        Update executor metrics after task execution.
        
        This method maintains running statistics about the executor's performance,
        which are useful for monitoring and diagnostics. It keeps track of both
        counts (tasks processed, succeeded, failed) and timing information.
        
        Args:
            succeeded: Whether the task completed successfully
            execution_time_ms: The time taken to execute the task in milliseconds.
                Only provided for successful executions.
        """
        # Always increment the total tasks processed counter
        self.metrics["tasks_processed"] += 1
        
        # Update appropriate success/failure counters
        if succeeded:
            self.metrics["tasks_succeeded"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        # Only update timing metrics if we have a valid execution time
        # (failed tasks typically won't provide this)
        if execution_time_ms > 0:
            # Add this execution time to the total
            self.metrics["total_execution_time_ms"] += execution_time_ms
            
            # Recalculate the running average execution time
            # Only successful tasks are included in the average
            if self.metrics["tasks_succeeded"] > 0:
                self.metrics["avg_execution_time_ms"] = (
                    self.metrics["total_execution_time_ms"] / self.metrics["tasks_succeeded"]
                )
    
    async def _report_metrics_periodically(self) -> None:
        """
        Periodically report metrics about this executor's performance.
        
        This method runs as a separate background task, regularly logging
        the executor's current performance metrics for monitoring and
        diagnostics. This helps track the executor's throughput, success rate,
        and average execution time over long periods of operation.
        
        The reporting interval is controlled by the config.metrics_interval setting.
        The method gracefully handles cancelation during shutdown.
        """
        while not self.shutdown_requested:
            try:
                # Skip initial reporting until we have some data to report
                # This avoids cluttering logs with empty metrics
                if self.metrics["tasks_processed"] > 0:
                    logger.info(f"Executor metrics: {self.metrics}")
                
                # Wait for the configured interval before the next report
                await asyncio.sleep(config.metrics_interval)
            
            # Handle cancelation during shutdown cleanly
            except asyncio.CancelledError:
                break
            
            # Catch any other exceptions to keep the background task running
            except Exception as e:
                logger.error(f"Error reporting metrics: {e}")
                # Still maintain the reporting interval even after errors
                await asyncio.sleep(config.metrics_interval)
    
    def _setup_signal_handlers(self) -> None:
        """
        Set up signal handlers for graceful shutdown.
        
        This method configures the executor to respond properly to system signals
        like SIGINT (Ctrl+C) and SIGTERM (termination request). When these signals
        are received, the executor will initiate a graceful shutdown rather than
        abruptly terminating, which helps ensure:
        
        1. Currently executing tasks can complete
        2. Resources are properly released
        3. Status updates are sent for any in-progress work
        4. Metrics and state are properly reported
        
        This is particularly important in containerized environments where
        SIGTERM is sent before a container is stopped.
        """
        def signal_handler(sig, frame):
            """Inner function that handles the actual signal."""
            logger.info(f"Received termination signal {sig}, initiating shutdown")
            # Set the flag that will cause the main loop to exit gracefully
            self.shutdown_requested = True
        
        # Register handlers for the common termination signals
        signal.signal(signal.SIGINT, signal_handler)   # Handles Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Handles termination requests
    
    def shutdown(self) -> None:
        """
        Request a graceful shutdown of this executor.
        
        This method provides a programmatic way to initiate a graceful shutdown,
        as an alternative to using system signals. It sets the shutdown_requested
        flag, which will cause the main execution loop to exit after any current
        task is completed.
        
        This is useful in scenarios where the executor needs to be shut down
        from within the application (e.g., based on some application logic)
        rather than through external signals.
        
        Note: This method only requests shutdown; it does not block waiting for
        the shutdown to complete. For that, you would need to await the start()
        method which will only return after shutdown is complete.
        """
        logger.info("Shutdown requested programmatically")
        self.shutdown_requested = True
