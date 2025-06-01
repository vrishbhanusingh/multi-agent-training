"""
Main module for the orchestrator agent.
This module initializes all components and starts the agent.
"""
import logging
import os
from typing import Dict, Optional


from agents.orchestrator_agent.controllers.api import app
from agents.orchestrator_agent.domain.interfaces import QueryServiceInterface, DAGPlannerInterface, DAGStorageInterface, TaskDispatcherInterface
from agents.orchestrator_agent.services.query_service import QueryService
from agents.orchestrator_agent.services.dag_planner import AdaptiveDagPlanner
from agents.orchestrator_agent.repositories.postgres_dag_storage import PostgresDAGStorage
from agents.orchestrator_agent.services.task_dispatcher import TaskDispatcher

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service container for dependency injection
class ServiceContainer:
    """Container for services to facilitate dependency injection."""
    
    _instance = None
    
    def __new__(cls):
        """Implement this class as a singleton."""
        if cls._instance is None:
            cls._instance = super(ServiceContainer, cls).__new__(cls)
            cls._instance._initialize_services()
        return cls._instance
    
    def _initialize_services(self):
        """Initialize all services."""
        logger.info("Initializing services")
        
        # Get configuration from environment variables
        postgres_url = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@postgres:5432/orchestrator")
        
        try:
            # Initialize repositories
            self.dag_storage: DAGStorageInterface = PostgresDAGStorage(postgres_url)
            # Initialize services
            self.dag_planner: DAGPlannerInterface = AdaptiveDagPlanner()
            self.query_service: QueryServiceInterface = QueryService(dag_storage=self.dag_storage, dag_planner=self.dag_planner)
            self.task_dispatcher: TaskDispatcherInterface = TaskDispatcher(self.dag_storage)
            logger.info("Services initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise


# Initialize the service container
services = ServiceContainer()

def get_query_service() -> QueryServiceInterface:
    """Get the query service instance for dependency injection."""
    return services.query_service

def get_dag_planner() -> DAGPlannerInterface:
    """Get the DAG planner instance for dependency injection."""
    return services.dag_planner

def get_dag_storage() -> DAGStorageInterface:
    """Get the DAG storage instance for dependency injection."""
    return services.dag_storage

def get_task_dispatcher() -> TaskDispatcherInterface:
    """Get the task dispatcher instance for dependency injection."""
    return services.task_dispatcher


# Export the FastAPI app for uvicorn
# When running with uvicorn, we use: uvicorn agents.orchestrator_agent:app
