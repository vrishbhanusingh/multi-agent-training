"""
Generic task handler implementation for the executor agent.

This module provides a concrete implementation of the TaskHandler protocol 
for handling basic data processing and utility tasks. It serves as:

1. A functional handler for simple utility operations
2. A fallback for tasks that don't require specialized handling
3. A reference implementation for developing more specialized handlers

The GenericTaskHandler supports several basic task types:
- echo: Simply returns the input parameters (useful for testing)
- delay: Waits for a specified time before completing
- transform_data: Performs basic data transformations on input

These basic operations allow the system to be tested and provide building
blocks for more complex workflows. The handler is designed to be robust
against malformed inputs and unexpected situations, with proper validation
and error handling.
"""
import logging
import json
import asyncio
from typing import Dict, List, Any
from uuid import UUID

from agents.executor_agent.domain.interfaces import TaskHandler

# Initialize logging
logger = logging.getLogger(__name__)


class GenericTaskHandler:
    """
    Generic task handler that can handle a variety of basic task types.
    
    This handler serves multiple purposes:
    1. It provides functional implementations for simple utility tasks
    2. It serves as a fallback for tasks that don't require specialized handling
    3. It demonstrates a complete implementation of the TaskHandler protocol
    
    The handler is stateless by design, with all task-specific state contained
    within the task parameters and context. This makes it suitable for use in
    distributed environments and simplifies scaling.
    
    The implementation follows a pattern of task-specific execution methods
    that are dispatched based on the task_type. This provides clear separation
    of concerns and makes it easy to add support for new task types.
    """
    
    @property
    def supported_task_types(self) -> List[str]:
        """
        Get the task types supported by this handler.
        
        This property is part of the TaskHandler protocol and is used by the
        ExecutorAgent to determine which task types this handler can process.
        The list is used during handler registration to populate the task type
        registry in the executor.
        
        The supported task types are:
        - "generic": A catch-all type for basic operations
        - "echo": Returns input data, useful for testing/debugging
        - "delay": Waits for a specified duration
        - "transform_data": Performs basic data transformations
        
        Returns:
            List[str]: The list of task type identifiers this handler supports
        """
        return [
            "generic",     # General-purpose handler for basic tasks
            "echo",        # Simply returns the input (for testing)
            "delay",       # Waits for a specified time before completing
            "transform_data"  # Performs basic data transformations
        ]
    
    @property
    def capabilities(self) -> List[str]:
        """
        Get the capabilities provided by this handler.
        
        This property is part of the TaskHandler protocol and is used by the
        ExecutorAgent to advertise its capabilities to the orchestrator. These
        capability tags are used during task polling to filter available tasks,
        ensuring executors only receive tasks they can handle.
        
        Capabilities are more general than task types and represent broader
        categories of functionality. A handler typically supports multiple
        task types within a capability area.
        
        The capabilities are:
        - "data_processing": Ability to transform, filter, and manipulate data
        - "basic_computation": Ability to perform simple computational operations
        
        Returns:
            List[str]: The list of capability tags for this handler
        """
        return [
            "data_processing",    # Ability to transform and manipulate data
            "basic_computation"   # Ability to perform basic computational operations
        ]
    
    def can_handle_task(self, task_type: str, parameters: Dict[str, Any]) -> bool:
        """
        Check if this handler can execute the given task type with the provided parameters.
        
        This method is part of the TaskHandler protocol and is called by the
        ExecutorAgent to determine if this handler can process a specific task
        instance. It goes beyond just checking the task type and can examine
        the specific parameters to make a more informed decision.
        
        For the GenericTaskHandler, the implementation is simple - it just checks
        if the task type is in the supported_task_types list. More specialized
        handlers might implement more complex logic that examines the parameters
        to determine compatibility.
        
        Args:
            task_type: The type identifier for the task
            parameters: The task-specific parameters
            
        Returns:
            bool: True if this handler can process this task, False otherwise
        """
        # This simple implementation just checks if the task type is supported
        # A more sophisticated handler might check parameter values or formats
        return task_type in self.supported_task_types
    
    async def execute_task(self, task_id: UUID, task_type: str, 
                     parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the task and return the result.
        
        This is the main method of the TaskHandler protocol, responsible for
        actually executing the task. It implements a dispatcher pattern that
        routes the task to the appropriate handler method based on the task_type.
        
        The method validates inputs, performs the task-specific operation,
        and returns the results in a standardized format. It handles errors
        gracefully and ensures consistent return structures.
        
        Args:
            task_id: The unique identifier of the task
            task_type: The type of task to execute
            parameters: Task-specific parameters that control execution
            context: Additional execution context from the executor
                
        Returns:
            Dict[str, Any]: The task execution result as a JSON-serializable dict
                
        Raises:
            ValueError: If the task type is unsupported or parameters are invalid
            RuntimeError: If task execution fails due to internal errors
        """
        # Log the start of task execution for tracking and debugging
        logger.info(f"Executing {task_type} task with ID {task_id}")
        
        # Select appropriate execution method based on task type
        if task_type == "echo":
            return await self._execute_echo_task(parameters)
        elif task_type == "delay":
            return await self._execute_delay_task(parameters)
        elif task_type == "transform_data":
            return await self._execute_transform_data_task(parameters, context)
        else:
            # Generic fallback
            return await self._execute_generic_task(parameters, context)
    
    async def _execute_echo_task(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an echo task that simply returns its input parameters."""
        message = parameters.get("message", "Echo task completed")
        data = parameters.get("data")
        
        return {
            "message": message,
            "data": data,
            "task_type": "echo"
        }
    
    async def _execute_delay_task(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a delay task that waits for a specified amount of time."""
        delay_seconds = float(parameters.get("delay_seconds", 5))
        logger.info(f"Delay task: sleeping for {delay_seconds} seconds")
        
        await asyncio.sleep(delay_seconds)
        
        return {
            "message": f"Delayed for {delay_seconds} seconds",
            "delay_seconds": delay_seconds,
            "task_type": "delay"
        }
    
    async def _execute_transform_data_task(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a data transformation task."""
        # Get inputs - either from parameters or from upstream results
        input_data = parameters.get("data")
        transformation_type = parameters.get("transformation", "identity")
        
        # If input_data not provided directly, check if we have a reference to upstream result
        if not input_data and "upstream_source" in parameters:
            upstream_source = parameters["upstream_source"]
            upstream_results = context.get("upstream_results", {})
            
            if upstream_source in upstream_results:
                input_data = upstream_results[upstream_source].get("data")
        
        # If still no input data, use a default empty structure
        if input_data is None:
            if transformation_type in ["filter", "map", "sort"]:
                # List transformations start with empty list
                input_data = []
            else:
                # Default to empty dict
                input_data = {}
        
        # Apply the transformation
        result_data = None
        
        if transformation_type == "filter" and isinstance(input_data, list):
            # Filter items using a simple expression
            filter_expr = parameters.get("filter_expr", "True")
            try:
                # Basic security: restrict the allowed variables and functions
                result_data = [
                    item for item in input_data
                    if eval(filter_expr, {"__builtins__": {}}, {"item": item})
                ]
            except Exception as e:
                logger.error(f"Error in filter transformation: {e}")
                result_data = input_data
                transformation_type = "error"
        
        elif transformation_type == "map" and isinstance(input_data, list):
            # Map items using a simple expression
            map_expr = parameters.get("map_expr", "item")
            try:
                # Basic security: restrict the allowed variables and functions
                result_data = [
                    eval(map_expr, {"__builtins__": {}}, {"item": item})
                    for item in input_data
                ]
            except Exception as e:
                logger.error(f"Error in map transformation: {e}")
                result_data = input_data
                transformation_type = "error"
        
        elif transformation_type == "sort" and isinstance(input_data, list):
            # Sort items
            sort_key = parameters.get("sort_key")
            reverse = parameters.get("reverse", False)
            
            if sort_key:
                try:
                    result_data = sorted(input_data, key=lambda x: x.get(sort_key), reverse=reverse)
                except Exception as e:
                    logger.error(f"Error in sort transformation: {e}")
                    result_data = input_data
                    transformation_type = "error"
            else:
                try:
                    result_data = sorted(input_data, reverse=reverse)
                except Exception as e:
                    logger.error(f"Error in sort transformation: {e}")
                    result_data = input_data
                    transformation_type = "error"
        
        elif transformation_type == "aggregate" and isinstance(input_data, list):
            # Aggregate items
            agg_type = parameters.get("aggregate_type", "sum")
            agg_field = parameters.get("aggregate_field")
            
            if agg_field:
                values = [item.get(agg_field) for item in input_data if agg_field in item]
            else:
                values = input_data
            
            try:
                if agg_type == "sum":
                    result_data = sum(values)
                elif agg_type == "avg":
                    result_data = sum(values) / len(values) if values else None
                elif agg_type == "min":
                    result_data = min(values) if values else None
                elif agg_type == "max":
                    result_data = max(values) if values else None
                elif agg_type == "count":
                    result_data = len(values)
                else:
                    result_data = values
                    transformation_type = "identity"
            except Exception as e:
                logger.error(f"Error in aggregate transformation: {e}")
                result_data = values
                transformation_type = "error"
        
        else:
            # Default identity transformation
            result_data = input_data
            transformation_type = "identity"
        
        return {
            "data": result_data,
            "transformation_type": transformation_type,
            "task_type": "transform_data"
        }
    
    async def _execute_generic_task(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a generic task."""
        logger.info("Executing generic task")
        
        # For a generic task, we just return the input parameters
        return {
            "message": "Generic task completed",
            "parameters_received": parameters,
            "task_type": "generic"
        }
