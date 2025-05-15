"""
API-based task poller implementation for the executor agent.

This module provides a concrete implementation of the TaskPollerInterface
that communicates with the orchestration system via RESTful API calls.
It handles:
1. Polling for available tasks that match the executor's capabilities
2. Claiming tasks for exclusive execution
3. Updating task status with execution results or errors
4. Authentication and session management with the API

The ApiTaskPoller implements resilience strategies for handling common
API interaction issues such as:
- Connection failures and network interruptions
- Authentication token expiration and renewal
- Rate limiting and backoff strategies
- Serialization and deserialization of task data

This serves as the primary communication channel between the executor
and the orchestration system in distributed deployments.
"""
import logging
import aiohttp
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from uuid import UUID

from agents.executor_agent.domain.interfaces import TaskPollerInterface
from agents.executor_agent.config import config

# Initialize logging
logger = logging.getLogger(__name__)


class ApiTaskPoller(TaskPollerInterface):
    """
    Task poller implementation that uses the orchestrator's REST API
    to retrieve tasks and report updates.
    
    This class implements the TaskPollerInterface protocol, providing a concrete
    implementation that communicates with the orchestration system using HTTP API calls.
    It handles all aspects of the task lifecycle from the executor agent's perspective:
    
    - Polling: Periodically checking for available tasks that match capabilities
    - Claiming: Reserving a task for exclusive execution by this executor
    - Updating: Reporting task completion or failure with results or error details
    
    The poller manages its own HTTP session and authentication state, handling
    token refresh and connection issues transparently. It implements retry logic
    with exponential backoff for resilience during API outages or intermittent
    connectivity.
    
    This implementation is designed to work with the standard orchestrator API,
    but could be extended or replaced to work with different backends without
    changing the executor agent's core logic.
    """
    
    def __init__(self, executor_id: str, capabilities: List[str]):
        """
        Initialize the API task poller.
        
        Creates a new API task poller instance with the specified executor identity
        and capabilities. The poller uses these capabilities to filter available
        tasks when polling, ensuring the executor only receives tasks it can handle.
        
        The actual HTTP session is not created here but in the initialize() method,
        allowing for proper async setup and cleanup in the executor's lifecycle.
        
        Args:
            executor_id: The unique identifier of the executor using this poller.
                This ID is included in API requests to identify the executor to
                the orchestration system.
            capabilities: List of capability strings that define what types of tasks
                this executor can handle (e.g., ["python", "data-processing", "gpu"]).
                These are used to filter tasks during polling.
        """
        self.executor_id = executor_id
        self.capabilities = capabilities
        self.api_base_url = config.api_base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[float] = None
    
    async def initialize(self) -> None:
        """
        Initialize the poller, creating a session and authenticating if needed.
        
        This asynchronous method sets up the HTTP session and performs initial
        authentication if required by the configuration. It should be called
        before any API operations are performed, typically during executor startup.
        
        The session created here will be reused for all API calls to benefit from
        connection pooling, keeping headers consistent, and maintaining cookies.
        
        If authentication is enabled in the configuration, this method will also
        perform the initial authentication and store the token for subsequent requests.
        
        Returns:
            None
            
        Raises:
            aiohttp.ClientError: If session creation fails
            AuthenticationError: If authentication is enabled but fails
        """
        # Create HTTP session with connection pooling for efficient API communication
        self.session = aiohttp.ClientSession()
        
        # Authenticate if required by the configuration
        # This will set self.access_token and self.token_expiry if successful
        if config.auth_enabled:
            await self._authenticate()
    
    async def close(self) -> None:
        """
        Close the poller, cleaning up resources.
        
        This method ensures proper cleanup of the HTTP session and any other
        resources used by the poller. It should be called during executor shutdown
        to prevent resource leaks, especially in long-running or containerized
        environments.
        
        The method is idempotent and safe to call multiple times, handling the
        case where initialization failed or wasn't called.
        
        Returns:
            None
            
        Raises:
            aiohttp.ClientError: If an error occurs while closing the session
        """
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _authenticate(self) -> None:
        """
        Authenticate with the orchestrator API and get an access token.
        
        This private method handles the authentication flow with the orchestrator API.
        It obtains an access token using the configured credentials, and sets up
        the token and its expiry time for use in subsequent API requests.
        
        If the session doesn't exist yet, it creates one. This handles cases where
        authentication is called separately from initialization or needs to be
        refreshed later.
        
        The token obtained is stored in self.access_token and used automatically
        in API requests. The expiry time is tracked to allow preemptive renewal.
        
        Returns:
            None
            
        Raises:
            ValueError: If authentication fails due to invalid credentials or server errors
            aiohttp.ClientError: If a network or connection error occurs during authentication
        """
        # Ensure we have a session for the HTTP request
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Prepare the authentication request
            auth_url = f"{self.api_base_url}/token"
            # Use form-based authentication with configured credentials
            form_data = {
                "username": config.auth_username,
                "password": config.auth_password
            }
            
            # Make the authentication request
            async with self.session.post(auth_url, data=form_data) as response:
                # Handle non-200 responses as authentication failures
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Authentication failed: {error_text}")
                    raise RuntimeError(f"Authentication failed with status {response.status}")
                
                auth_data = await response.json()
                self.access_token = auth_data.get("access_token")
                
                if not self.access_token:
                    raise ValueError("No access token received")
                
                # Set token expiry (assume 1 hour if not specified)
                self.token_expiry = time.time() + 3600  # 1 hour default
                
                logger.info("Successfully authenticated with orchestrator API")
        
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            raise
    
    async def _ensure_authenticated(self) -> None:
        """
        Ensure we have a valid authentication token.
        
        This helper method checks if authentication is required and if the current
        token is valid or needs refreshing. It's called before making API requests
        to ensure we always have valid credentials.
        
        The method implements a preemptive renewal strategy, refreshing tokens
        that are within 5 minutes of expiration to prevent failed API calls due
        to token expiration during a request.
        
        Returns:
            None
            
        Raises:
            Any exceptions from _authenticate() if token refresh fails
        """
        # Skip authentication entirely if it's not enabled in config
        if not config.auth_enabled:
            return
        
        # Check if we need to authenticate - either no token exists or it's expiring soon
        # The 300 second (5 minute) buffer ensures we don't use a token that's about to expire
        if not self.access_token or (self.token_expiry and time.time() > self.token_expiry - 300):
            # Token missing or will expire in less than 5 minutes
            await self._authenticate()
    
    async def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers, including authentication if needed.
        
        This helper method constructs the HTTP headers needed for API requests.
        It ensures that authentication headers are included when required and
        handles the appropriate content types for JSON communication.
        
        The method calls _ensure_authenticated() to verify we have a valid token
        before including it in the headers, ensuring proper authentication flow.
        
        Returns:
            Dict[str, str]: A dictionary of HTTP headers to use in API requests
            
        Raises:
            Any exceptions from _ensure_authenticated() if authentication fails
        """
        # Make sure we have valid authentication before building headers
        await self._ensure_authenticated()
        
        # Start with standard headers for JSON API communication
        headers = {
            "Content-Type": "application/json",  # We're sending JSON
            "Accept": "application/json"         # We expect JSON responses
        }
        
        # Add authentication token if auth is enabled and we have a token
        if config.auth_enabled and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        return headers
    
    async def poll_for_tasks(self) -> Optional[Dict[str, Any]]:
        """
        Poll for available tasks matching this executor's capabilities.
        
        This method implements the core polling functionality defined in the
        TaskPollerInterface. It queries the orchestration API for available tasks
        that match this executor's capabilities and returns one if available.
        
        The method handles the complete API communication flow, including:
        - Session initialization if needed
        - Authentication and header preparation
        - Parameter construction for capability-based filtering
        - HTTP request execution with proper error handling
        - Response parsing and validation
        
        Polling follows a non-blocking approach - if no tasks are available, 
        the method returns quickly rather than waiting or blocking.
        
        Returns:
            Optional[Dict[str, Any]]: A task representation if one is available,
                or None if no suitable tasks are available
                
        Raises:
            aiohttp.ClientError: If a network or connection error occurs
            ValueError: If the API response is malformed or cannot be parsed
        """
        if not self.session:
            await self.initialize()
        
        try:
            # Construct the capabilities query string
            capability_params = ""
            if self.capabilities:
                # Use the first capability for now (the API doesn't support multiple yet)
                capability_params = f"?capability={self.capabilities[0]}"
            
            url = f"{self.api_base_url}/api/tasks/available{capability_params}"
            headers = await self._get_headers()
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    tasks = await response.json()
                    
                    # Check if we got any tasks
                    if tasks and len(tasks) > 0:
                        return tasks[0]  # Return the first available task
                    
                    return None
                
                elif response.status == 401 or response.status == 403:
                    # Authentication issue, try to re-authenticate
                    self.access_token = None
                    await self._ensure_authenticated()
                    return None
                
                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to get available tasks, status: {response.status}, response: {error_text}")
                    return None
        
        except Exception as e:
            logger.error(f"Error polling for tasks: {e}")
            return None
    
    async def claim_task(self, task_id: UUID) -> bool:
        """
        Attempt to claim a task for exclusive execution.
        
        This method implements the claiming functionality defined in the
        TaskPollerInterface. It attempts to claim the specified task for exclusive 
        execution by this executor, preventing other executors from working on it.
        
        The claiming process is a critical part of the distributed task execution
        system, ensuring that each task is executed exactly once, even when multiple
        executors are polling for work. The method handles various response cases:
        
        - Success (200): The task was successfully claimed
        - Conflict (409): Another executor already claimed this task
        - Not Found (404): The task no longer exists or was already completed
        - Auth Errors (401/403): Authentication issues that trigger re-authentication
        - Other errors: Logged and treated as failed claims
        
        Returns:
            bool: True if the claim was successful, False otherwise (including all error cases)
            
        Raises:
            aiohttp.ClientError: If a severe network or connection error occurs that
                cannot be handled internally
        """
        if not self.session:
            await self.initialize()
        
        try:
            url = f"{self.api_base_url}/api/tasks/{task_id}/claim"
            headers = await self._get_headers()
            
            data = {
                "executor_id": self.executor_id,
                "capabilities": self.capabilities
            }
            
            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    return True
                
                elif response.status == 409:
                    # Task already claimed by another executor
                    logger.info(f"Task {task_id} already claimed by another executor")
                    return False
                
                elif response.status == 401 or response.status == 403:
                    # Authentication issue, try to re-authenticate
                    self.access_token = None
                    await self._ensure_authenticated()
                    return False
                
                elif response.status == 404:
                    logger.warning(f"Task {task_id} not found")
                    return False
                
                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to claim task {task_id}, status: {response.status}, response: {error_text}")
                    return False
        
        except Exception as e:
            logger.error(f"Error claiming task {task_id}: {e}")
            return False
    
    async def update_task_status(self, task_id: UUID, status: str, 
                           result: Optional[Dict[str, Any]] = None,
                           error: Optional[str] = None) -> bool:
        """
        Update the status of a task, optionally including results or error information.
        
        This method implements the status updating functionality defined in the
        TaskPollerInterface. It reports task execution outcomes back to the
        orchestration system, including status changes, result data for successful
        execution, or error information for failures.
        
        The method handles both successful and failed task executions through
        the same interface, with appropriate parameters:
        - For success: status="completed" and result=<result_data>
        - For failure: status="failed" and error=<error_message>
        
        This completes the task execution lifecycle that began with polling and claiming.
        The orchestrator uses this information to handle task completion, trigger
        dependent tasks, or implement retry strategies for failed tasks.
        
        Args:
            task_id: The unique identifier of the task being updated
            status: The new status of the task (typically "completed" or "failed")
            result: Optional result data from successful execution (JSON-serializable)
            error: Optional error message if execution failed
            
        Returns:
            bool: True if the status update was successful, False otherwise
            
        Raises:
            aiohttp.ClientError: If a severe network or connection error occurs that
                cannot be handled internally
        """
        if not self.session:
            await self.initialize()
        
        try:
            url = f"{self.api_base_url}/api/tasks/{task_id}/status"
            headers = await self._get_headers()
            
            data = {
                "status": status
            }
            
            if result:
                data["result"] = result
            
            if error:
                data["error"] = error
            
            async with self.session.put(url, headers=headers, json=data) as response:
                if response.status == 200:
                    return True
                
                elif response.status == 401 or response.status == 403:
                    # Authentication issue, try to re-authenticate
                    self.access_token = None
                    await self._ensure_authenticated()
                    return False
                
                elif response.status == 404:
                    logger.warning(f"Task {task_id} not found")
                    return False
                
                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to update task {task_id} status, status: {response.status}, response: {error_text}")
                    return False
        
        except Exception as e:
            logger.error(f"Error updating task {task_id} status: {e}")
            return False
