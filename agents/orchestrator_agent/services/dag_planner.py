"""
Service implementation for DAG planning.

This module provides the core logic for transforming user queries into executable Directed Acyclic Graphs (DAGs) of tasks. It implements the `DAGPlannerInterface` and is responsible for:

1. **Query Analysis**: Uses pattern matching and heuristics to infer the required workflow structure from natural language or structured queries.
2. **DAG Construction**: Builds a DAG object with nodes (tasks) and edges (dependencies) that represent the required computation or data flow.
3. **Task Typing and Routing**: Assigns task types (extraction, transformation, analysis, etc.) based on query content, enabling downstream task handler selection.
4. **Validation**: Ensures the generated DAG is valid (acyclic, all dependencies resolvable, etc.) before submission to storage and dispatch.
5. **Extensibility**: The planner is designed to be easily extended with new task types, patterns, and planning strategies as the system evolves.

**Design Notes:**
- The planner uses regular expressions and keyword matching to map user intent to workflow structure.
- It is stateless and thread-safe, suitable for use in concurrent API environments.
- Logging is used extensively for traceability and debugging of DAG generation.

This service is a critical part of the orchestrator's ability to translate high-level user requests into concrete, distributed computation.
"""
import logging
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from uuid import UUID

from agents.orchestrator_agent.domain.interfaces import DAGPlannerInterface
from agents.orchestrator_agent.domain.models import DAG, Query, Task, TaskStatus
from agents.orchestrator_agent.config import config

# Initialize logging
logger = logging.getLogger(__name__)

class AdaptiveDagPlanner(DAGPlannerInterface):
    """
    An implementation of the DAG planner that creates appropriate workflows based on query analysis.
    This planner can create different DAG structures based on query content and requirements.
    """
    
    def __init__(self, enable_logging: bool = True):
        """Initialize the planner with optional logging."""
        self.enable_logging = enable_logging
        
        # Task type patterns - these would be more comprehensive in a real implementation
        self.task_patterns = {
            "extraction": [
                r"extract", r"collect", r"gather", r"scrape", r"fetch", r"retrieve",
                r"data source", r"database", r"api", r"file"
            ],
            "transformation": [
                r"transform", r"convert", r"change", r"modify", r"restructure",
                r"format", r"normalize", r"clean", r"preprocess", r"filter"
            ],
            "analysis": [
                r"analyze", r"calculate", r"compute", r"determine", r"evaluate",
                r"assess", r"compare", r"statistics", r"metrics", r"insights"
            ],
            "generation": [
                r"generate", r"create", r"produce", r"write", r"output",
                r"report", r"summary", r"visualization", r"chart", r"graph"
            ],
            "notification": [
                r"notify", r"alert", r"send", r"email", r"message", r"notification"
            ],
            "integration": [
                r"integrate", r"connect", r"interface", r"sync", r"push to",
                r"external service", r"third-party", r"api post", r"webhook"
            ]
        }
        
        # Capabilities required for each task type
        self.task_capabilities = {
            "extraction": ["data_source_access", "http_client"],
            "transformation": ["data_processing"],
            "analysis": ["data_analysis", "computation"],
            "generation": ["content_generation", "templating"],
            "notification": ["notification_service", "email_service"],
            "integration": ["api_client", "webhook_sender"]
        }
        
        # Default timeouts for each task type (in seconds)
        self.task_timeouts = {
            "extraction": 600,    # 10 minutes
            "transformation": 300,   # 5 minutes
            "analysis": 1200,     # 20 minutes
            "generation": 900,    # 15 minutes
            "notification": 120,  # 2 minutes
            "integration": 300    # 5 minutes
        }
    
    def _detect_task_types(self, query_text: str) -> Set[str]:
        """Detect required task types from query content."""
        query_text = query_text.lower()
        detected_types = set()
        
        # Check for each task type
        for task_type, patterns in self.task_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_text, re.IGNORECASE):
                    detected_types.add(task_type)
                    break
        
        # If nothing was detected, default to a basic workflow
        if not detected_types:
            detected_types = {"extraction", "transformation", "generation"}
        
        return detected_types
    
    def _estimate_task_complexity(self, task_type: str, query_text: str) -> int:
        """Estimate task complexity on a scale of 1-10."""
        # This is a simplified implementation
        # A real implementation would use more sophisticated analysis
        
        # Base complexity by task type
        base_complexity = {
            "extraction": 3,
            "transformation": 4,
            "analysis": 6,
            "generation": 5,
            "notification": 2,
            "integration": 4
        }.get(task_type, 3)
        
        # Adjust based on query complexity
        query_length_factor = min(len(query_text) / 500, 2)  # Length factor (max 2)
        
        # Detect complex indicators in query
        complexity_indicators = [
            "complex", "advanced", "sophisticated", "detailed", "comprehensive",
            "deep", "thorough", "extensive", "multi", "all"
        ]
        
        complexity_bonus = sum(1 for word in complexity_indicators 
                               if re.search(fr"\b{word}\b", query_text, re.IGNORECASE))
        
        # Calculate final complexity (capped at 10)
        complexity = base_complexity + (query_length_factor * 0.5) + (complexity_bonus * 0.5)
        return min(round(complexity), 10)
    
    def _get_task_parameters(self, task_type: str, query: Query) -> Dict[str, Any]:
        """Generate appropriate parameters for each task type."""
        # Basic parameters that all tasks get
        params = {
            "query_id": str(query.id),
            "query_content": query.content,
            "created_at": datetime.now().isoformat()
        }
        
        # Add task-specific parameters
        if task_type == "extraction":
            # Attempt to identify data sources mentioned in the query
            sources = []
            source_patterns = [
                (r"database\s+(\w+)", "database"),
                (r"api\s+(\w+)", "api"),
                (r"file\s+(\w+\.\w+)", "file")
            ]
            
            for pattern, source_type in source_patterns:
                matches = re.findall(pattern, query.content, re.IGNORECASE)
                for match in matches:
                    sources.append({"type": source_type, "name": match})
            
            params["detected_sources"] = sources or None
        
        elif task_type == "transformation":
            # Detect any specific transformation methods mentioned
            transform_types = []
            transform_patterns = [
                r"filter\s+by",
                r"group\s+by",
                r"sort\s+by",
                r"join\s+with",
                r"aggregate"
            ]
            
            for pattern in transform_patterns:
                if re.search(pattern, query.content, re.IGNORECASE):
                    transform_types.append(pattern.split()[0])
            
            params["transform_types"] = transform_types or None
        
        # Add meta from the query
        if hasattr(query, "meta") and query.meta:
            params["meta"] = query.meta
        
        return params
    
    def _create_dag_structure(self, query: Query, task_types: Set[str]) -> Tuple[DAG, Dict[str, Task]]:
        """Create an appropriate DAG structure with the detected task types."""
        # Create a new DAG
        dag = DAG(
            name=f"DAG for Query {query.id}",
            description=f"Generated from query: {query.content[:100]}..."
        )
        
        # Dictionary to store tasks by type
        tasks_by_type = {}
        
        # Create tasks for each detected type
        for task_type in task_types:
            complexity = self._estimate_task_complexity(task_type, query.content)
            parameters = self._get_task_parameters(task_type, query)
            timeout = self.task_timeouts.get(task_type, 3600)  # Default 1 hour
            
            task = Task(
                name=f"{task_type.capitalize()} Task",
                description=f"Perform {task_type} operations for query: {query.content[:50]}...",
                task_type=task_type,
                parameters=parameters,
                estimated_complexity=complexity,
                required_capabilities=self.task_capabilities.get(task_type, []),
                status=TaskStatus.PENDING,
                timeout_seconds=timeout
            )
            
            # Add task to DAG
            dag.add_task(task)
            tasks_by_type[task_type] = task
            
            if self.enable_logging:
                logger.debug(f"Created {task_type} task with complexity {complexity}")
        
        return dag, tasks_by_type
    
    def create_dag_from_query(self, query: Query) -> DAG:
        """Generate a DAG based on the given query."""
        logger.info(f"Creating DAG for query: {query.id}")
        
        # Detect task types from query content
        task_types = self._detect_task_types(query.content)
        if self.enable_logging:
            logger.info(f"Detected task types: {task_types}")
        
        # Create DAG and tasks
        dag, tasks = self._create_dag_structure(query, task_types)
        
        # Set up dependencies based on detected task types
        self._create_dependencies(dag, tasks, task_types)
        
        # Validate the DAG
        if not dag.validate():
            logger.error(f"Generated DAG for query {query.id} has cycles or other validation issues")
            raise ValueError(f"Invalid DAG generated for query {query.id}")
        
        return dag
    
    def _create_dependencies(self, dag: DAG, tasks: Dict[str, Task], task_types: Set[str]) -> None:
        """Create dependencies between tasks based on logical relationships."""
        # Standard processing pipeline: extraction -> transformation -> analysis -> generation
        standard_flow = ["extraction", "transformation", "analysis", "generation"]
        
        # Find tasks that are in our standard flow
        flow_tasks = [task_type for task_type in standard_flow if task_type in tasks]
        
        # Create the standard pipeline dependencies
        for i in range(len(flow_tasks) - 1):
            upstream = flow_tasks[i]
            downstream = flow_tasks[i + 1]
            
            if upstream in tasks and downstream in tasks:
                dag.add_dependency(tasks[upstream].id, tasks[downstream].id)
                if self.enable_logging:
                    logger.debug(f"Added dependency: {upstream} -> {downstream}")
        
        # Special handling: notification and integration usually come last
        for special_type in ["notification", "integration"]:
            if special_type in tasks:
                # Find the last task in our standard flow
                if flow_tasks:
                    last_standard_task = flow_tasks[-1]
                    if last_standard_task in tasks:
                        dag.add_dependency(tasks[last_standard_task].id, tasks[special_type].id)
                        if self.enable_logging:
                            logger.debug(f"Added dependency: {last_standard_task} -> {special_type}")
    
    def validate_dag(self, dag: DAG) -> bool:
        """Validate a DAG for correctness (no cycles, etc.)."""
        logger.info(f"Validating DAG: {dag.id}")
        
        # First, use the built-in cycle detection
        if not dag.validate():
            logger.error(f"DAG {dag.id} failed validation: contains cycles")
            return False
        
        # Check for isolated tasks (no dependencies)
        isolated_tasks = []
        for task_id, task in dag.tasks.items():
            if not task._upstream_tasks and not task._downstream_tasks:
                isolated_tasks.append(task_id)
        
        if isolated_tasks:
            logger.warning(f"DAG {dag.id} contains {len(isolated_tasks)} isolated tasks")
            # This is a warning but not a validation failure
        
        # Check for orphaned dependencies (pointing to non-existent tasks)
        for task_id, task in dag.tasks.items():
            for upstream_id in task._upstream_tasks:
                if upstream_id not in dag.tasks:
                    logger.error(f"DAG {dag.id} has task {task_id} with non-existent upstream dependency {upstream_id}")
                    return False
            
            for downstream_id in task._downstream_tasks:
                if downstream_id not in dag.tasks:
                    logger.error(f"DAG {dag.id} has task {task_id} with non-existent downstream dependency {downstream_id}")
                    return False
        
        # If all checks passed, the DAG is valid
        logger.info(f"DAG {dag.id} successfully validated")
        return True
