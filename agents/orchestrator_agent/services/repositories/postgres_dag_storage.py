"""
PostgreSQL implementation of the DAG storage interface.
This module provides a PostgreSQL-based implementation for storing DAGs, tasks, and their relationships.
"""
import json
import logging
import time
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Generator, Tuple
from uuid import UUID
import uuid

from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.pool import QueuePool

from agents.orchestrator_agent.domain.interfaces import DAGStorageInterface
from agents.orchestrator_agent.domain.models import DAG, Task, TaskStatus
from agents.orchestrator_agent.config import config

# Initialize logging
logger = logging.getLogger(__name__)

# SQLAlchemy setup
Base = declarative_base()


# Database models
class DAGModel(Base):
    """SQLAlchemy model for DAG storage."""
    __tablename__ = "dags"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    name = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    version = Column(Integer, default=1)
    
    tasks = relationship("TaskModel", back_populates="dag", cascade="all, delete-orphan")


class TaskModel(Base):
    """SQLAlchemy model for Task storage."""
    __tablename__ = "tasks"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    dag_id = Column(PostgresUUID(as_uuid=True), ForeignKey("dags.id"))
    name = Column(String(255))
    description = Column(Text)
    task_type = Column(String(50))
    parameters = Column(JSONB)
    estimated_complexity = Column(Integer, default=1)
    required_capabilities = Column(JSONB)
    status = Column(String(20), default="pending")
    assigned_to = Column(String(255), nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    timeout_seconds = Column(Integer, default=3600)
    
    dag = relationship("DAGModel", back_populates="tasks")


class TaskDependency(Base):
    """ORM model for task dependencies."""
    __tablename__ = "task_dependencies"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upstream_task_id = Column(PostgresUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    downstream_task_id = Column(PostgresUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)


class PostgresDAGStorage(DAGStorageInterface):

    def health_check(self) -> bool:
        """Check the health of the PostgreSQL connection."""
        try:
            with self.session_scope() as session:
                # Simple query to check DB connection
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgresDAGStorage health check failed: {e}")
            return False
    """PostgreSQL implementation of the DAG storage interface."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """Initialize the storage with a database connection string."""
        logger.info("Initializing PostgreSQL DAG storage")
        
        # Use provided connection string or get from config
        self.connection_string = connection_string or config.postgres_connection_string
        
        # Create engine with connection pooling
        self.engine = create_engine(
            self.connection_string,
            poolclass=QueuePool,
            pool_size=config.postgres_pool_size,
            max_overflow=config.postgres_max_overflow,
            pool_timeout=config.postgres_pool_timeout,
            pool_pre_ping=True  # Check connection validity before using from pool
        )
        
        # Create schema if it doesn't exist
        self._create_schema()
        
        # Create session factory
        self.Session = sessionmaker(bind=self.engine)
        
        logger.info("PostgreSQL DAG storage initialized successfully")
    
    def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        retries = 5
        retry_delay = 5
        
        for attempt in range(retries):
            try:
                logger.info("Creating database schema if not exists")
                Base.metadata.create_all(self.engine)
                logger.info("Database schema created successfully")
                return
            except OperationalError as e:
                if attempt < retries - 1:
                    logger.warning(f"Database connection failed, retrying in {retry_delay} seconds... ({e})")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to create database schema after {retries} attempts: {e}")
                    raise
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Session error, rolling back: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def _handle_db_error(self, operation: str, error: Exception) -> Tuple[bool, str]:
        """Handle database errors with appropriate logging and response."""
        error_message = str(error)
        
        if isinstance(error, IntegrityError):
            logger.error(f"Integrity error during {operation}: {error_message}")
            return False, f"Data integrity error: {error_message}"
        elif isinstance(error, OperationalError):
            logger.error(f"Database operational error during {operation}: {error_message}")
            return False, f"Database connection error: {error_message}"
        else:
            logger.error(f"Unexpected error during {operation}: {error_message}")
            return False, f"Database error: {error_message}"
    
    def save_dag(self, dag: DAG) -> bool:
        """Save a DAG to storage."""
        logger.info(f"Saving DAG: {dag.id}")
        
        try:
            with self.session_scope() as session:
                # Create DAG model
                dag_model = DAGModel(
                    id=dag.id,
                    name=dag.name,
                    description=dag.description,
                    created_at=dag.created_at,
                    updated_at=dag.updated_at
                )
                
                # Add tasks
                for task in dag.tasks.values():
                    task_model = TaskModel(
                        id=task.id,
                        dag_id=dag.id,
                        name=task.name,
                        description=task.description,
                        task_type=task.task_type,
                        parameters=task.parameters,
                        estimated_complexity=task.estimated_complexity,
                        required_capabilities=task.required_capabilities,
                        status=task.status.value,  # Convert enum to string value
                        assigned_to=task.assigned_to,
                        created_at=task.created_at,
                        updated_at=task.updated_at,
                        result=task.result,
                        error=task.error,
                        timeout_seconds=task.timeout_seconds
                    )
                    dag_model.tasks.append(task_model)
                
                # Add to session and commit
                session.add(dag_model)
                logger.debug(f"Successfully saved DAG {dag.id}")
                return True
        
        except Exception as e:
            success, _ = self._handle_db_error(f"saving DAG {dag.id}", e)
            return success
    
    def get_dag(self, dag_id: UUID) -> Optional[DAG]:
        """Get a DAG by ID."""
        logger.info(f"Getting DAG: {dag_id}")
        
        try:
            with self.session_scope() as session:
                # Get DAG from database
                dag_model = session.query(DAGModel).filter(DAGModel.id == dag_id).first()
                
                if not dag_model:
                    logger.warning(f"DAG {dag_id} not found")
                    return None
                
                # Create DAG domain object
                dag = DAG(
                    id=dag_model.id,
                    name=dag_model.name,
                    description=dag_model.description,
                    created_at=dag_model.created_at,
                    updated_at=dag_model.updated_at,
                    version=dag_model.version
                )
                
                # Get tasks
                task_models = session.query(TaskModel).filter(TaskModel.dag_id == dag_id).all()
                
                for task_model in task_models:
                    task = Task(
                        id=task_model.id,
                        name=task_model.name,
                        description=task_model.description,
                        task_type=task_model.task_type,
                        parameters=task_model.parameters,
                        estimated_complexity=task_model.estimated_complexity,
                        required_capabilities=task_model.required_capabilities,
                        status=TaskStatus(task_model.status),
                        assigned_to=task_model.assigned_to,
                        created_at=task_model.created_at,
                        updated_at=task_model.updated_at,
                        result=task_model.result,
                        error=task_model.error,
                        timeout_seconds=task_model.timeout_seconds
                    )
                    dag.add_task(task)
                
                # Get dependencies
                task_ids = [task_model.id for task_model in task_models]
                
                if task_ids:  # Only query if we have tasks
                    dependencies = session.query(TaskDependency).filter(
                        TaskDependency.upstream_task_id.in_(task_ids)
                    ).all()
                    
                    for dep in dependencies:
                        if dep.upstream_task_id in dag.tasks and dep.downstream_task_id in dag.tasks:
                            dag.add_dependency(dep.upstream_task_id, dep.downstream_task_id)
                
                logger.debug(f"Successfully retrieved DAG {dag_id} with {len(task_models)} tasks")
                return dag
        
        except Exception as e:
            self._handle_db_error(f"getting DAG {dag_id}", e)
            return None
    
    def update_task_status(self, dag_id: UUID, task_id: UUID, status: TaskStatus) -> bool:
        """Update the status of a task within a DAG."""
        logger.info(f"Updating task {task_id} status to {status.value} in DAG {dag_id}")
        
        try:
            with self.session_scope() as session:
                # Get task from database
                task_model = (
                    session.query(TaskModel)
                    .filter(TaskModel.id == task_id)
                    .filter(TaskModel.dag_id == dag_id)
                    .first()
                )
                
                if not task_model:
                    logger.warning(f"Task {task_id} not found in DAG {dag_id}")
                    return False
                
                # Update status
                task_model.status = status.value
                
                # If task is completed, check for downstream tasks that might become ready
                if status == TaskStatus.COMPLETED:
                    self._update_downstream_tasks(session, task_id)
                
                logger.debug(f"Successfully updated task {task_id} status to {status.value}")
                return True
        
        except Exception as e:
            success, _ = self._handle_db_error(f"updating task {task_id} status", e)
            return success
    
    def _update_downstream_tasks(self, session: Session, completed_task_id: UUID) -> None:
        """Update downstream tasks after a task completes."""
        try:
            # Find downstream tasks
            dependencies = session.query(TaskDependency).filter(
                TaskDependency.upstream_task_id == completed_task_id
            ).all()
            
            for dep in dependencies:
                # Check if all upstream tasks for this downstream task are completed
                downstream_task = session.query(TaskModel).filter(
                    TaskModel.id == dep.downstream_task_id
                ).first()
                
                if not downstream_task or downstream_task.status != TaskStatus.PENDING.value:
                    continue
                
                # Find all upstream dependencies for this task
                upstream_dependencies = session.query(TaskDependency).filter(
                    TaskDependency.downstream_task_id == dep.downstream_task_id
                ).all()
                
                # Check if all upstream tasks are completed
                all_completed = True
                for upstream_dep in upstream_dependencies:
                    upstream_task = session.query(TaskModel).filter(
                        TaskModel.id == upstream_dep.upstream_task_id
                    ).first()
                    
                    if not upstream_task or upstream_task.status != TaskStatus.COMPLETED.value:
                        all_completed = False
                        break
                
                # If all upstream tasks are completed, mark this task as ready
                if all_completed:
                    logger.info(f"Task {dep.downstream_task_id} is now ready (all dependencies completed)")
                    downstream_task.status = TaskStatus.READY.value
        
        except Exception as e:
            logger.error(f"Error updating downstream tasks: {e}")
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status."""
        logger.info(f"Getting tasks with status: {status.value}")
        
        try:
            with self.session_scope() as session:
                # Get tasks from database
                task_models = session.query(TaskModel).filter(TaskModel.status == status.value).all()
                
                # Convert to domain objects
                tasks = []
                for task_model in task_models:
                    task = Task(
                        id=task_model.id,
                        name=task_model.name,
                        description=task_model.description,
                        task_type=task_model.task_type,
                        parameters=task_model.parameters,
                        estimated_complexity=task_model.estimated_complexity,
                        required_capabilities=task_model.required_capabilities,
                        status=TaskStatus(task_model.status),
                        assigned_to=task_model.assigned_to,
                        created_at=task_model.created_at,
                        updated_at=task_model.updated_at,
                        result=task_model.result,
                        error=task_model.error,
                        timeout_seconds=task_model.timeout_seconds
                    )
                    tasks.append(task)
                
                logger.debug(f"Retrieved {len(tasks)} tasks with status {status.value}")
                return tasks
        
        except Exception as e:
            self._handle_db_error(f"getting tasks by status {status.value}", e)
            return []
    
    def get_ready_tasks(self) -> List[Task]:
        """Get all tasks that are ready to be executed."""
        logger.info("Getting ready tasks")
        
        try:
            with self.session_scope() as session:
                # Get tasks from database that are in READY status
                task_models = session.query(TaskModel).filter(TaskModel.status == TaskStatus.READY.value).all()
                
                # Convert to domain objects
                tasks = []
                for task_model in task_models:
                    task = Task(
                        id=task_model.id,
                        name=task_model.name,
                        description=task_model.description,
                        task_type=task_model.task_type,
                        parameters=task_model.parameters,
                        estimated_complexity=task_model.estimated_complexity,
                        required_capabilities=task_model.required_capabilities,
                        status=TaskStatus(task_model.status),
                        assigned_to=task_model.assigned_to,
                        created_at=task_model.created_at,
                        updated_at=task_model.updated_at,
                        result=task_model.result,
                        error=task_model.error,
                        timeout_seconds=task_model.timeout_seconds
                    )
                    
                    # Add task to the list
                    tasks.append(task)
                
                logger.debug(f"Retrieved {len(tasks)} ready tasks")
                return tasks
        
        except Exception as e:
            self._handle_db_error("getting ready tasks", e)
            return []
