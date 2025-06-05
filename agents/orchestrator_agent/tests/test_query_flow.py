#!/usr/bin/env python
"""
Test script to simulate a query flow and print detailed logs at each step.
This script creates a test query, generates a DAG, and prints the query and DAG details.
"""

import logging
import sys
import uuid
from datetime import datetime
import json

from agents.orchestrator_agent.domain.models import Query
from agents.orchestrator_agent.services.query_service import QueryService
from agents.orchestrator_agent.services.dag_planner import AdaptiveDagPlanner
from agents.orchestrator_agent.services.repositories.postgres_dag_storage import PostgresDAGStorage

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting test query flow simulation")

    # Initialize components
    dag_storage = PostgresDAGStorage()
    dag_planner = AdaptiveDagPlanner()
    query_service = QueryService(dag_storage=dag_storage, dag_planner=dag_planner)

    # Create a test query
    test_query_content = "Extract data from database sales and transform it by filtering by date."
    test_user_id = "test_user"
    test_meta = {"test": True, "timestamp": datetime.now().isoformat()}

    logger.info("\n===== Creating test query =====\n")
    logger.info(f"Query content: {test_query_content}")
    query = query_service.create_query(
        content=test_query_content,
        user_id=test_user_id,
        meta=test_meta
    )

    logger.info("\n===== Query Created =====\n")
    logger.info(json.dumps(query.to_dict(), indent=2))

    # Retrieve the query to verify persistence
    logger.info("\n===== Retrieving Query from Storage =====\n")
    retrieved_query = query_service.get_query(query.id)
    logger.info(json.dumps(retrieved_query.to_dict(), indent=2))

    # Get the DAG associated with the query
    if query.dag_id:
        logger.info("\n===== Generated DAG =====\n")
        dag = dag_storage.get_dag(query.dag_id)
        logger.info(json.dumps(dag.to_dict(), indent=2))
    else:
        logger.warning("No DAG associated with the query.")

    logger.info("\n===== Test query flow simulation completed =====\n")


if __name__ == "__main__":
    main() 