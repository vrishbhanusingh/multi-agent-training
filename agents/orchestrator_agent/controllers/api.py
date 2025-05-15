"""
REST API controllers for the orchestrator agent.

This module defines the FastAPI application and all HTTP endpoints for the orchestrator agent. It is responsible for:

1. **API Initialization**: Sets up the FastAPI app, middleware (CORS, security), and OpenAPI documentation.
2. **Endpoint Definition**: Exposes endpoints for query submission, DAG inspection, task polling, status updates, and system health.
3. **Dependency Injection**: Wires up all service dependencies (query service, DAG planner, storage, dispatcher, MQ) for use in endpoint handlers.
4. **Authentication and Authorization**: Integrates JWT-based authentication for secure access to protected endpoints.
5. **Error Handling and Response Formatting**: Provides consistent error responses and logging for all API operations.
6. **Background Task Management**: Supports background processing for long-running or asynchronous operations.

**Design Notes:**
- The API is designed for extensibility, supporting new endpoints and authentication schemes as needed.
- All endpoints are documented with OpenAPI and use Pydantic models for request/response validation.
- Logging is used for all major actions and errors to support observability and debugging.

This module is the main integration point for external clients, agents, and monitoring tools to interact with the orchestrator agent.
"""
import logging
from typing import Dict, Any, List, Optional, Union
from uuid import UUID
from datetime import datetime, timedelta
import json

from fastapi import FastAPI, HTTPException, Depends, status, Header, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import jwt
from jwt.exceptions import PyJWTError

from agents.orchestrator_agent.domain.interfaces import (
    QueryServiceInterface, DAGPlannerInterface, 
    DAGStorageInterface, TaskDispatcherInterface
)
from agents.orchestrator_agent.domain.models import TaskStatus, Query, DAG, Task
from agents.orchestrator_agent.services.query_service import QueryService
from agents.orchestrator_agent.services.dag_planner import AdaptiveDagPlanner
from agents.orchestrator_agent.repositories.postgres_dag_storage import PostgresDAGStorage
from agents.orchestrator_agent.services.task_dispatcher import TaskDispatcher
from agents.orchestrator_agent.services.rabbitmq_client import RabbitMQClient
from agents.orchestrator_agent.config import config

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize services
dag_storage = PostgresDAGStorage()
dag_planner = AdaptiveDagPlanner()
rabbitmq_client = RabbitMQClient()
query_service = QueryService(dag_storage=dag_storage, dag_planner=dag_planner)
task_dispatcher = TaskDispatcher(dag_storage=dag_storage, rabbitmq_client=rabbitmq_client)

# Initialize FastAPI app
app = FastAPI(
    title="Orchestrator Agent API",
    description="API for DAG-based workflow orchestration",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT authentication setup
SECRET_KEY = config.jwt_secret_key
ALGORITHM = config.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = config.jwt_expiration_minutes

class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: Optional[str] = None
    exp: Optional[int] = None

class User(BaseModel):
    """User model."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

# Simplified user database for demo purposes
# In production, this would be a proper database
USERS_DB = {
    "test_user": {
        "username": "test_user",
        "full_name": "Test User",
        "email": "test@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False,
    },
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "hashed_password": "fakehashedsecretadmin",
        "disabled": False,
    },
}

def verify_password(plain_password, hashed_password):
    """Verify password against hashed version."""
    # In a real implementation, this would use proper password hashing
    return plain_password + "fakehashed" == hashed_password

def get_user(username: str):
    """Get user from database."""
    if username in USERS_DB:
        user_data = USERS_DB[username]
        return User(**user_data)

def authenticate_user(username: str, password: str):
    """Authenticate user with username and password."""
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, USERS_DB[username]["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
        
        token_data = TokenPayload(sub=username, exp=payload.get("exp"))
    except PyJWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.sub)
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Get current active user."""
    if USERS_DB[current_user.username].get("disabled", False):
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user

# Service dependencies
def get_query_service() -> QueryServiceInterface:
    """Get query service instance."""
    return query_service

def get_dag_storage() -> DAGStorageInterface:
    """Get DAG storage instance."""
    return dag_storage

def get_dag_planner() -> DAGPlannerInterface:
    """Get DAG planner instance."""
    return dag_planner

def get_task_dispatcher() -> TaskDispatcherInterface:
    """Get task dispatcher instance."""
    return task_dispatcher


# Pydantic models for request/response validation
class QueryRequest(BaseModel):
    """Model for query submission."""
    content: str = Field(..., description="The query content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    sync: bool = Field(False, description="Whether to wait for DAG generation before responding")


class QueryResponse(BaseModel):
    """Model for query response."""
    query_id: str = Field(..., description="The ID of the submitted query")
    status: str = Field(..., description="The status of the query")
    dag_id: Optional[str] = Field(None, description="The ID of the generated DAG, if available")
    created_at: Optional[str] = Field(None, description="The creation timestamp")
    updated_at: Optional[str] = Field(None, description="The last update timestamp")
    
    @validator('query_id', 'dag_id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v and isinstance(v, UUID):
            return str(v)
        return v


class QueryListResponse(BaseModel):
    """Model for listing multiple queries."""
    queries: List[QueryResponse]
    total: int = Field(..., description="Total number of queries")


class TaskModel(BaseModel):
    """Model for task representation."""
    id: str = Field(..., description="The ID of the task")
    name: str = Field(..., description="The name of the task")
    description: str = Field(..., description="The description of the task")
    task_type: str = Field(..., description="The type of the task")
    parameters: Dict[str, Any] = Field(..., description="The parameters for the task")
    status: str = Field(..., description="The status of the task")
    assigned_to: Optional[str] = Field(None, description="The executor assigned to this task")
    estimated_complexity: int = Field(..., description="The estimated complexity of the task")
    required_capabilities: List[str] = Field(default_factory=list, description="The capabilities required to execute this task")
    created_at: Optional[str] = Field(None, description="The creation timestamp")
    updated_at: Optional[str] = Field(None, description="The last update timestamp")
    result: Optional[Dict[str, Any]] = Field(None, description="The result of task execution")
    error: Optional[str] = Field(None, description="Error message if the task failed")
    upstream_tasks: List[str] = Field(default_factory=list, description="IDs of tasks that this task depends on")
    downstream_tasks: List[str] = Field(default_factory=list, description="IDs of tasks that depend on this task")
    
    @validator('id', 'upstream_tasks', 'downstream_tasks', pre=True)
    def convert_uuid_list(cls, v):
        if isinstance(v, list):
            return [str(item) if isinstance(item, UUID) else item for item in v]
        elif v and isinstance(v, UUID):
            return str(v)
        return v


class DAGResponse(BaseModel):
    """Model for DAG response."""
    id: str = Field(..., description="The ID of the DAG")
    name: str = Field(..., description="The name of the DAG")
    description: str = Field(..., description="The description of the DAG")
    created_at: str = Field(..., description="The creation timestamp")
    updated_at: str = Field(..., description="The last update timestamp")
    version: int = Field(..., description="The version of the DAG")
    tasks: List[TaskModel] = Field(..., description="The tasks in the DAG")
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v and isinstance(v, UUID):
            return str(v)
        return v


class TaskStatusRequest(BaseModel):
    """Model for updating task status."""
    status: str = Field(..., description="The new status of the task")
    result: Optional[Dict[str, Any]] = Field(None, description="The result of the task execution")
    error: Optional[str] = Field(None, description="Error message if the task failed")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = [s.value for s in TaskStatus]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class TaskClaimRequest(BaseModel):
    """Model for claiming a task."""
    executor_id: str = Field(..., description="The ID of the executor claiming the task")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities of the executor")


class ExecutorRegistrationRequest(BaseModel):
    """Model for executor registration."""
    executor_id: str = Field(..., description="Unique ID for this executor")
    name: str = Field(..., description="Human-readable name for this executor")
    capabilities: List[str] = Field(..., description="List of capabilities this executor provides")
    max_concurrent_tasks: int = Field(1, description="Maximum number of tasks this executor can run concurrently")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional executor metadata")


class HealthResponse(BaseModel):
    """Model for health check response."""
    status: str
    version: str
    components: Dict[str, Dict[str, str]]


# Authentication routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Get access token using username and password."""
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    components_status = {
        "database": {"status": "unknown"},
        "rabbitmq": {"status": "unknown"}
    }
    
    # Check database connection
    try:
        with dag_storage.session_scope() as session:
            session.execute("SELECT 1")
            components_status["database"] = {"status": "healthy"}
    except Exception as e:
        components_status["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Check RabbitMQ connection
    try:
        rmq_status = rabbitmq_client.health_check()
        components_status["rabbitmq"] = rmq_status
    except Exception as e:
        components_status["rabbitmq"] = {"status": "unhealthy", "error": str(e)}
    
    overall_status = "healthy" if all(c["status"] == "healthy" for c in components_status.values()) else "degraded"
    
    return {
        "status": overall_status,
        "version": "1.0.0",
        "components": components_status
    }


@app.post("/api/queries", response_model=QueryResponse)
async def create_query(
    query: QueryRequest,
    background_tasks: BackgroundTasks,
    query_service: QueryServiceInterface = Depends(get_query_service),
    current_user: User = Depends(get_current_active_user)
):
    """Submit a new query to generate a DAG workflow."""
    try:
        logger.info(f"Received query: {query.content}")
        
        # Create metadata with user information
        metadata = query.metadata or {}
        metadata["user"] = {
            "username": current_user.username,
            "email": current_user.email
        }
        
        # Create the query
        created_query = query_service.create_query(
            content=query.content,
            user_id=current_user.username,
            metadata=metadata
        )
        
        # If sync is True, wait for DAG generation
        # Otherwise, handle it asynchronously
        if query.sync:
            # Process synchronously (the create_query method already generates the DAG if dag_planner was provided)
            pass
        else:
            # For async processing, the DAG has already been scheduled for generation
            pass
        
        return {
            "query_id": str(created_query.id),
            "status": created_query.status,
            "dag_id": str(created_query.dag_id) if created_query.dag_id else None,
            "created_at": created_query.created_at.isoformat() if created_query.created_at else None,
            "updated_at": created_query.updated_at.isoformat() if created_query.updated_at else None
        }
    
    except Exception as e:
        logger.error(f"Error creating query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create query: {str(e)}"
        )


@app.get("/api/queries/{query_id}", response_model=QueryResponse)
async def get_query(
    query_id: UUID,
    query_service: QueryServiceInterface = Depends(get_query_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get the status of a submitted query."""
    try:
        logger.info(f"Getting query status for: {query_id}")
        
        # Get the query
        query = query_service.get_query(query_id)
        
        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query {query_id} not found"
            )
        
        return {
            "query_id": str(query.id),
            "status": query.status,
            "dag_id": str(query.dag_id) if query.dag_id else None,
            "created_at": query.created_at.isoformat() if query.created_at else None,
            "updated_at": query.updated_at.isoformat() if query.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get query: {str(e)}"
        )


@app.get("/api/queries/{query_id}/dag", response_model=DAGResponse)
async def get_query_dag(
    query_id: UUID,
    query_service: QueryServiceInterface = Depends(get_query_service),
    dag_storage: DAGStorageInterface = Depends(get_dag_storage),
    current_user: User = Depends(get_current_active_user)
):
    """Get the DAG generated for a specific query."""
    try:
        logger.info(f"Getting DAG for query: {query_id}")
        
        # Get the query to find the associated DAG
        query = query_service.get_query(query_id)
        
        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query {query_id} not found"
            )
        
        if not query.dag_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No DAG associated with query {query_id}"
            )
        
        # Get the DAG
        dag = dag_storage.get_dag(query.dag_id)
        
        if not dag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DAG {query.dag_id} not found"
            )
        
        # Convert domain model to response model
        tasks = []
        for task_id, task in dag.tasks.items():
            tasks.append({
                "id": str(task.id),
                "name": task.name,
                "description": task.description,
                "task_type": task.task_type,
                "parameters": task.parameters,
                "status": task.status.value,
                "assigned_to": task.assigned_to,
                "estimated_complexity": task.estimated_complexity,
                "required_capabilities": task.required_capabilities,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "result": task.result,
                "error": task.error,
                "upstream_tasks": [str(t) for t in task._upstream_tasks],
                "downstream_tasks": [str(t) for t in task._downstream_tasks]
            })
        
        return {
            "id": str(dag.id),
            "name": dag.name,
            "description": dag.description,
            "created_at": dag.created_at.isoformat(),
            "updated_at": dag.updated_at.isoformat(),
            "version": dag.version,
            "tasks": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174002",
                    "name": "Task A",
                    "description": "First task",
                    "task_type": "processing",
                    "parameters": {"input": "value"},
                    "status": "pending",
                    "estimated_complexity": 3,
                    "upstream_tasks": [],
                    "downstream_tasks": ["123e4567-e89b-12d3-a456-426614174003"]
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174003",
                    "name": "Task B",
                    "description": "Second task",
                    "task_type": "processing",
                    "parameters": {"input": "value"},
                    "status": "pending",
                    "estimated_complexity": 2,
                    "upstream_tasks": ["123e4567-e89b-12d3-a456-426614174002"],
                    "downstream_tasks": []
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error getting DAG: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DAG: {str(e)}"
        )


@app.get("/api/tasks/available", response_model=List[TaskModel])
async def get_available_tasks(
    capability: Optional[str] = None,
    task_dispatcher: TaskDispatcherInterface = Depends(get_task_dispatcher),
    current_user: User = Depends(get_current_active_user)
):
    """Get tasks that are available for execution, optionally filtered by capability."""
    try:
        capabilities = [capability] if capability else None
        logger.info(f"Getting available tasks with capabilities: {capabilities}")
        
        # Get available tasks
        tasks = task_dispatcher.get_available_tasks(capabilities)
        
        # Convert domain models to response models
        task_models = []
        for task in tasks:
            task_models.append({
                "id": str(task.id),
                "name": task.name,
                "description": task.description,
                "task_type": task.task_type,
                "parameters": task.parameters,
                "status": task.status.value,
                "assigned_to": task.assigned_to,
                "estimated_complexity": task.estimated_complexity,
                "required_capabilities": task.required_capabilities,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "result": task.result,
                "error": task.error,
                "upstream_tasks": [str(t) for t in task._upstream_tasks],
                "downstream_tasks": [str(t) for t in task._downstream_tasks]
            })
        
        return task_models
    
    except Exception as e:
        logger.error(f"Error getting available tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available tasks: {str(e)}"
        )


@app.put("/api/tasks/{task_id}/status")
async def update_task_status(
    task_id: UUID,
    task_update: TaskStatusRequest,
    task_dispatcher: TaskDispatcherInterface = Depends(get_task_dispatcher),
    current_user: User = Depends(get_current_active_user)
):
    """Update the status of a task, optionally with results or error information."""
    try:
        logger.info(f"Updating task {task_id} status to {task_update.status}")
        
        # Convert string status to enum
        try:
            task_status = TaskStatus(task_update.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task status: {task_update.status}"
            )
        
        # Update task status
        success = task_dispatcher.update_task_status(
            task_id=task_id,
            status=task_status,
            result=task_update.result,
            error=task_update.error
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found or could not be updated"
            )
        
        return {"status": "success", "task_id": str(task_id)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task status: {str(e)}"
        )


@app.get("/api/dags/{dag_id}")
async def get_dag(
    dag_id: UUID,
    current_user: Dict = Depends(get_current_user)
):
    """Get information about a specific DAG."""
    try:
        # TODO: Implement actual DAG service integration
        # Placeholder implementation
        logger.info(f"Getting DAG: {dag_id}")
        
        # For now, return mock response
        return {
            "id": str(dag_id),
            "name": "Sample DAG",
            "description": "Sample DAG",
            "created_at": "2023-05-15T10:00:00Z",
            "updated_at": "2023-05-15T10:02:00Z",
            "version": 1,
            "tasks": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174002",
                    "name": "Task A",
                    "description": "First task",
                    "task_type": "processing",
                    "parameters": {"input": "value"},
                    "status": "pending",
                    "estimated_complexity": 3,
                    "upstream_tasks": [],
                    "downstream_tasks": ["123e4567-e89b-12d3-a456-426614174003"]
                },
                {
                    "id": "123e4567-e89b-12d3-a456-426614174003",
                    "name": "Task B",
                    "description": "Second task",
                    "task_type": "processing",
                    "parameters": {"input": "value"},
                    "status": "pending",
                    "estimated_complexity": 2,
                    "upstream_tasks": ["123e4567-e89b-12d3-a456-426614174002"],
                    "downstream_tasks": []
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error getting DAG: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DAG: {str(e)}"
        )


# Additional routes to be implemented:
# - Authentication routes
# - Admin routes for DAG management
# - Monitoring and metrics endpoints
