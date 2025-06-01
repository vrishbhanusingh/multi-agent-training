#!/usr/bin/env python
"""
Orchestrator Agent main application entry point.

This module is responsible for bootstrapping the orchestrator agent service, which acts as the central coordinator in a distributed multi-agent system. It performs the following high-level responsibilities:

1. **Component Initialization**: Instantiates all core services, including DAG storage, DAG planning, task dispatching, message queue client, and query management.
2. **API Server Startup**: Launches the FastAPI-based REST API server, exposing endpoints for workflow submission, task polling, and system monitoring.
3. **Background Maintenance**: Starts background threads for health checks and task reassignment, ensuring system robustness and fault tolerance.
4. **Signal Handling & Graceful Shutdown**: Registers handlers for SIGINT/SIGTERM to ensure all resources (threads, DB, MQ) are cleanly released on shutdown.
5. **Error Handling & Logging**: Provides comprehensive logging and error management to support observability and operational debugging.

**Architecture Overview:**
- The orchestrator agent is the central authority for workflow (DAG) management, task assignment, and system health in the multi-agent platform.
- It interacts with a PostgreSQL database for persistent DAG and task storage, and with RabbitMQ for distributing tasks to executor agents.
- The agent exposes a REST API for external clients and agents to submit queries, poll for tasks, and monitor system state.
- Background workers ensure that failed or timed-out tasks are detected and reassigned, and that the health of all critical services is continuously monitored.

**Key Components:**
- `OrchestratorAgent`: Main class managing the lifecycle of all components.
- `PostgresDAGStorage`: Handles persistent storage of DAGs and tasks.
- `AdaptiveDagPlanner`: Generates DAGs from user queries.
- `RabbitMQClient`: Publishes tasks to executors and manages MQ connections.
- `TaskDispatcher`: Assigns tasks to executors and manages task state.
- `QueryService`: Manages the lifecycle of user queries and links them to DAGs.
- `FastAPI app`: Exposes the REST API for orchestration and monitoring.

This file is the canonical entry point for running the orchestrator agent as a service, either directly or in a containerized environment.
"""
import logging
import sys
import time
import threading
import signal
import uvicorn
from typing import Optional

from fastapi import FastAPI

from agents.orchestrator_agent.controllers.api import app
from agents.orchestrator_agent.repositories.postgres_dag_storage import PostgresDAGStorage
from agents.orchestrator_agent.services.dag_planner import AdaptiveDagPlanner
from agents.orchestrator_agent.services.query_service import QueryService
from agents.orchestrator_agent.services.rabbitmq_client import RabbitMQClient
from agents.orchestrator_agent.services.task_dispatcher import TaskDispatcher
from agents.orchestrator_agent.config import config

# Set up logging
logging.basicConfig(
    level=config.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"orchestrator_agent_{time.strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Main orchestrator agent class that initializes, manages, and coordinates all core components.

    This class is responsible for the full lifecycle of the orchestrator service, including:
    - Instantiating and wiring together all service components (DAG storage, planner, MQ, dispatcher, query service)
    - Starting and stopping background maintenance threads (task reassignment, health checks)
    - Managing the FastAPI server lifecycle
    - Handling system signals for graceful shutdown
    - Ensuring robust error handling and logging throughout the agent

    **Component Relationships:**
    - `dag_storage` is the persistent backend for DAGs and tasks, used by all other services
    - `dag_planner` generates DAGs from user queries, used by the query service
    - `rabbitmq_client` is the message queue interface for task distribution
    - `task_dispatcher` assigns tasks to executors and manages their state
    - `query_service` manages user queries and links them to DAGs
    - Background threads ensure system health and task reliability

    The orchestrator agent is designed for extensibility and operational robustness, supporting hot restarts, live health monitoring, and automatic recovery from common failure modes.
    """

    def __init__(self):
        """
        Initialize the orchestrator agent and all its core components.

        This constructor sets up the entire orchestration stack, including persistent storage, DAG planning, message queue, task dispatching, and query management. It also prepares background worker threads and the shutdown event for lifecycle management.

        All components are instantiated here to ensure tight integration and shared configuration.
        """
        logger.info("Initializing Orchestrator Agent")

        # Persistent DAG and task storage (PostgreSQL-backed)
        self.dag_storage = PostgresDAGStorage()
        # DAG planner for workflow generation from queries
        self.dag_planner = AdaptiveDagPlanner()
        # RabbitMQ client for task distribution to executors
        self.rabbitmq_client = RabbitMQClient()
        # Query service for managing user queries and linking to DAGs
        self.query_service = QueryService(
            dag_storage=self.dag_storage,
            dag_planner=self.dag_planner
        )
        # Task dispatcher for assigning and tracking tasks
        self.task_dispatcher = TaskDispatcher(
            dag_storage=self.dag_storage,
            rabbitmq_client=self.rabbitmq_client
        )

        # Background maintenance threads
        self.task_reassignment_thread: Optional[threading.Thread] = None  # Handles failed/timed-out task reassignment
        self.health_check_thread: Optional[threading.Thread] = None        # Monitors health of DB and MQ
        self.shutdown_event = threading.Event()  # Used to signal threads to stop

    def start(self):
        """
        Start the orchestrator agent and all its components.

        This method performs the full startup sequence:
        1. Initializes the database schema (ensures all tables/indices exist)
        2. Initializes RabbitMQ connections and exchanges
        3. Starts background maintenance workers (task reassignment, health checks)
        4. Registers signal handlers for graceful shutdown (SIGINT/SIGTERM)
        5. Launches the FastAPI server for external API access

        All errors are logged and trigger a full shutdown to avoid partial operation.
        """
        logger.info("Starting Orchestrator Agent")

        try:
            # Step 1: Database schema is initialized by PostgresDAGStorage if needed
            logger.info("Database schema initialization handled by PostgresDAGStorage")

            # Step 2: RabbitMQ connection is initialized in RabbitMQClient.__init__
            logger.info("RabbitMQ client already initialized in constructor")

            # Step 3: Start background maintenance workers
            self.start_background_workers()

            # Step 4: Register signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self.handle_shutdown_signal)
            signal.signal(signal.SIGTERM, self.handle_shutdown_signal)

            # Step 5: Start the FastAPI server (blocking call)
            logger.info(f"Starting API server on {config.api_host}:{config.api_port}")
            uvicorn.run(
                app,
                host=config.api_host,
                port=config.api_port,
                log_level=config.log_level.lower()
            )

        except Exception as e:
            logger.error(f"Error starting Orchestrator Agent: {e}")
            self.shutdown()
            raise

    def start_background_workers(self):
        """
        Start background threads for maintenance tasks (task reassignment, health checks).

        This method launches daemon threads that run in the background to:
        - Periodically check for failed or timed-out tasks and reassign them
        - Continuously monitor the health of the database and RabbitMQ connections

        These threads are signaled to stop via the shutdown_event when the agent is shutting down.
        """
        logger.info("Starting background workers")
        
        # Task reassignment worker
        self.task_reassignment_thread = threading.Thread(
            target=self.task_reassignment_worker,
            daemon=True
        )
        self.task_reassignment_thread.start()
        
        # Health check worker
        self.health_check_thread = threading.Thread(
            target=self.health_check_worker,
            daemon=True
        )
        self.health_check_thread.start()
    
    def task_reassignment_worker(self):
        """
        Background worker that periodically checks for failed or timed-out tasks and reassigns them.

        This thread runs in a loop, waking up at a configurable interval to:
        - Query the task dispatcher for any tasks that have failed or timed out
        - Attempt to reassign those tasks to available executors
        - Log the number of tasks reassigned for observability

        The worker is resilient to errors: exceptions are logged and the thread sleeps briefly before retrying, preventing tight error loops.
        """
        logger.info("Task reassignment worker started")

        while not self.shutdown_event.is_set():
            try:
                # Check for failed or timed out tasks and attempt reassignment
                reassigned_tasks = self.task_dispatcher.reassign_failed_tasks()

                if reassigned_tasks:
                    logger.info(f"Reassigned {len(reassigned_tasks)} failed or timed out tasks")

                # Sleep for a configurable interval before next check
                self.shutdown_event.wait(config.task_reassignment_interval)

            except Exception as e:
                logger.error(f"Error in task reassignment worker: {e}")
                # Sleep a bit to avoid tight loop in case of persistent errors
                time.sleep(5)
    
    def health_check_worker(self):
        """
        Background worker that periodically checks the health of connected services (DB, RabbitMQ).

        This thread runs in a loop, performing the following at each interval:
        - Checks the health of the PostgreSQL database connection
        - Checks the health of the RabbitMQ connection
        - Logs the health status for monitoring and alerting

        If any service is unhealthy, a warning is logged. The worker is resilient to errors and will continue running after exceptions.
        """
        logger.info("Health check worker started")

        while not self.shutdown_event.is_set():
            try:
                # Check database connection health
                db_healthy = self.dag_storage.health_check()

                # Check RabbitMQ connection health
                rmq_healthy = self.rabbitmq_client.health_check()

                # Log health status for observability
                if db_healthy and rmq_healthy:
                    logger.debug("All services healthy")
                else:
                    logger.warning(f"Health check issues - DB: {db_healthy}, RabbitMQ: {rmq_healthy}")

                # Sleep for a configurable interval before next check
                self.shutdown_event.wait(config.health_check_interval)

            except Exception as e:
                logger.error(f"Error in health check worker: {e}")
                # Sleep a bit to avoid tight loop in case of persistent errors
                time.sleep(5)
    
    def handle_shutdown_signal(self, sig, frame):
        """
        Handle shutdown signals (SIGINT, SIGTERM) for graceful termination.

        This method is registered as the signal handler for SIGINT and SIGTERM. When triggered, it:
        - Logs the received signal
        - Initiates the orchestrator agent's shutdown sequence

        This ensures that all resources are released and background threads are stopped cleanly.
        """
        logger.info(f"Received shutdown signal: {sig}")
        self.shutdown()
    
    def shutdown(self):
        """
        Gracefully shut down the orchestrator agent and all its components.

        This method performs a full, orderly shutdown of the orchestrator service:
        - Signals all background threads to stop via the shutdown_event
        - Waits for maintenance threads to finish (with timeout)
        - Closes RabbitMQ and database connections, handling errors
        - Logs the completion of the shutdown process

        This ensures that no resources are leaked and that the system can be safely restarted or stopped.
        """
        logger.info("Shutting down Orchestrator Agent")

        # Signal threads to stop
        self.shutdown_event.set()

        # Wait for background threads to finish (with timeout)
        if self.task_reassignment_thread and self.task_reassignment_thread.is_alive():
            self.task_reassignment_thread.join(timeout=5)

        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5)

        # Close RabbitMQ connections
        try:
            self.rabbitmq_client.close()
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")

        # Close database connections
        try:
            self.dag_storage.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")

        logger.info("Orchestrator Agent shutdown complete")


if __name__ == "__main__":
    orchestrator = OrchestratorAgent()
    orchestrator.start()
