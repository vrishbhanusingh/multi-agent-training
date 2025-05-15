"""
Service implementation for query handling.

This module implements the `QueryServiceInterface` and is responsible for managing the full lifecycle of user queries in the orchestrator agent. Its main responsibilities include:

1. **Query Creation**: Accepts user queries (natural language or structured), validates them, and persists them in the database.
2. **DAG Generation and Linking**: Invokes the DAG planner to generate a workflow DAG from the query and links the query to the resulting DAG.
3. **Query State Management**: Tracks the status of queries (pending, processing, completed, failed) and updates state transitions in persistent storage.
4. **Metadata and User Management**: Stores and manages metadata and user associations for queries, supporting multi-user environments and auditability.
5. **ORM Integration**: Provides a SQLAlchemy ORM model for queries, supporting efficient database operations and migrations.

**Design Notes:**
- The service is designed for extensibility, supporting new query types, metadata fields, and workflow patterns as the system evolves.
- It is thread-safe and suitable for use in concurrent API environments.
- Logging is used for all major actions to support observability and debugging.

This service is central to the orchestrator's ability to translate user intent into executable workflows and to track the progress of those workflows through the system.
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List
from uuid import UUID
import json

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB

from agents.orchestrator_agent.domain.interfaces import QueryServiceInterface, DAGPlannerInterface, DAGStorageInterface
from agents.orchestrator_agent.domain.models import Query, DAG
from agents.orchestrator_agent.repositories.postgres_dag_storage import Base
from agents.orchestrator_agent.config import config

# Initialize logging
logger = logging.getLogger(__name__)

# Define ORM model for queries
class QueryModel(Base):
    """SQLAlchemy model for storing queries."""
    __tablename__ = "queries"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    content = Column(Text, nullable=False)
    user_id = Column(String, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)
    dag_id = Column(PostgresUUID(as_uuid=True), nullable=True)

class QueryService(QueryServiceInterface):
    """Implementation of the query service interface using PostgreSQL."""
    
    def __init__(self, dag_storage: DAGStorageInterface = None, dag_planner: DAGPlannerInterface = None):
        """Initialize the query service with optional DAG storage and planner."""
        logger.info("Initializing QueryService")
        self.dag_storage = dag_storage
        self.dag_planner = dag_planner
        
        # We'll reuse the session management from DAGStorage
        # In a real implementation, we might have a separate session factory
    
    def create_query(self, content: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Query:
        """Create a new query from user input."""
        logger.info(f"Creating query with user_id: {user_id}")
        
        # Create the query domain object
        query = Query(content=content, user_id=user_id, metadata=metadata)
        
        if self.dag_storage:
            try:
                # Store in database using the session_scope from DAGStorage
                with self.dag_storage.session_scope() as session:
                    query_model = QueryModel(
                        id=query.id,
                        content=query.content,
                        user_id=query.user_id,
                        metadata=query.metadata,
                        created_at=query.created_at,
                        updated_at=query.updated_at,
                        status=query.status,
                        dag_id=query.dag_id
                    )
                    session.add(query_model)
                    
                    logger.debug(f"Query {query.id} saved to database")
                    
                    # If we have a DAG planner, automatically generate a DAG
                    if self.dag_planner:
                        try:
                            # Generate a DAG from the query
                            dag = self.dag_planner.create_dag_from_query(query)
                            
                            # Save the DAG
                            if self.dag_storage.save_dag(dag):
                                # Link query to DAG
                                query.dag_id = dag.id
                                query_model.dag_id = dag.id
                                query_model.status = "processing"
                                query.status = "processing"
                                
                                logger.info(f"Generated DAG {dag.id} for query {query.id}")
                        except Exception as e:
                            logger.error(f"Error generating DAG for query {query.id}: {e}")
                            query_model.status = "error"
                            query.status = "error"
            
            except Exception as e:
                logger.error(f"Error saving query to database: {e}")
                # Continue with the in-memory query object even if DB storage fails
        
        return query
    
    def get_query(self, query_id: UUID) -> Optional[Query]:
        """Get a query by ID."""
        logger.info(f"Getting query: {query_id}")
        
        if not self.dag_storage:
            logger.warning("No DAG storage available, can't retrieve query")
            return None
        
        try:
            with self.dag_storage.session_scope() as session:
                query_model = session.query(QueryModel).filter(QueryModel.id == query_id).first()
                
                if not query_model:
                    logger.warning(f"Query {query_id} not found")
                    return None
                
                # Convert to domain object
                query = Query(
                    id=query_model.id,
                    content=query_model.content,
                    user_id=query_model.user_id,
                    metadata=query_model.metadata,
                    created_at=query_model.created_at,
                    updated_at=query_model.updated_at,
                    status=query_model.status,
                    dag_id=query_model.dag_id
                )
                
                return query
        
        except Exception as e:
            logger.error(f"Error retrieving query {query_id}: {e}")
            return None
    
    def get_all_queries(self, status: Optional[str] = None, limit: int = 100) -> List[Query]:
        """Get all queries, optionally filtered by status."""
        logger.info(f"Getting all queries with status: {status}")
        
        if not self.dag_storage:
            logger.warning("No DAG storage available, can't retrieve queries")
            return []
        
        try:
            with self.dag_storage.session_scope() as session:
                query = session.query(QueryModel)
                
                if status:
                    query = query.filter(QueryModel.status == status)
                
                query = query.order_by(QueryModel.created_at.desc()).limit(limit)
                query_models = query.all()
                
                # Convert to domain objects
                queries = []
                for qm in query_models:
                    query = Query(
                        id=qm.id,
                        content=qm.content,
                        user_id=qm.user_id,
                        metadata=qm.metadata,
                        created_at=qm.created_at,
                        updated_at=qm.updated_at,
                        status=qm.status,
                        dag_id=qm.dag_id
                    )
                    queries.append(query)
                
                return queries
        
        except Exception as e:
            logger.error(f"Error retrieving queries: {e}")
            return []
    
    def update_query_status(self, query_id: UUID, status: str) -> bool:
        """Update the status of a query."""
        logger.info(f"Updating query {query_id} status to: {status}")
        
        if not self.dag_storage:
            logger.warning("No DAG storage available, can't update query")
            return False
        
        try:
            with self.dag_storage.session_scope() as session:
                query_model = session.query(QueryModel).filter(QueryModel.id == query_id).first()
                
                if not query_model:
                    logger.warning(f"Query {query_id} not found")
                    return False
                
                query_model.status = status
                query_model.updated_at = datetime.now()
                
                logger.debug(f"Updated query {query_id} status to {status}")
                return True
        
        except Exception as e:
            logger.error(f"Error updating query {query_id} status: {e}")
            return False
    
    def link_query_to_dag(self, query_id: UUID, dag_id: UUID) -> bool:
        """Link a query to a generated DAG."""
        logger.info(f"Linking query {query_id} to DAG {dag_id}")
        
        if not self.dag_storage:
            logger.warning("No DAG storage available, can't link query to DAG")
            return False
        
        try:
            with self.dag_storage.session_scope() as session:
                query_model = session.query(QueryModel).filter(QueryModel.id == query_id).first()
                
                if not query_model:
                    logger.warning(f"Query {query_id} not found")
                    return False
                
                # Check if DAG exists
                if self.dag_storage:
                    dag = self.dag_storage.get_dag(dag_id)
                    if not dag:
                        logger.warning(f"DAG {dag_id} not found")
                        return False
                
                # Update the query
                query_model.dag_id = dag_id
                query_model.updated_at = datetime.now()
                
                logger.debug(f"Linked query {query_id} to DAG {dag_id}")
                return True
        
        except Exception as e:
            logger.error(f"Error linking query {query_id} to DAG {dag_id}: {e}")
            return False
    
    def delete_query(self, query_id: UUID) -> bool:
        """Delete a query by ID."""
        logger.info(f"Deleting query: {query_id}")
        
        if not self.dag_storage:
            logger.warning("No DAG storage available, can't delete query")
            return False
        
        try:
            with self.dag_storage.session_scope() as session:
                query_model = session.query(QueryModel).filter(QueryModel.id == query_id).first()
                
                if not query_model:
                    logger.warning(f"Query {query_id} not found")
                    return False
                
                session.delete(query_model)
                
                logger.debug(f"Deleted query {query_id}")
                return True
        
        except Exception as e:
            logger.error(f"Error deleting query {query_id}: {e}")
            return False
