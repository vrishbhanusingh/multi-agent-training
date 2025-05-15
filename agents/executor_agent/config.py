"""
Configuration for the executor agent.
Loads settings from environment variables with sensible defaults.

This module provides configuration management for the executor agent, centralizing
all configurable parameters in a single place. It supports both local development
and production deployment by allowing all settings to be overridden via environment
variables while providing sensible defaults.

The configuration is organized into logical sections:
1. Agent identification and core settings
2. API connection to orchestrator service
3. RabbitMQ messaging system integration
4. Task polling behavior and timeouts
5. Task execution parameters and capabilities
6. Result storage options for large task outputs
7. Monitoring, metrics, and operational parameters
8. Logging configuration

Usage:
    from agents.executor_agent.config import config
    
    # Access configuration parameters
    polling_interval = config.polling_interval
    api_url = config.api_base_url
"""
import logging
import os
from typing import Dict, Any


class ExecutorConfig:
    """
    Configuration for the executor agent.
    
    This class encapsulates all configurable aspects of the executor agent,
    loading values from environment variables with sensible defaults for local
    development. It provides proper typing and validation of configuration values
    and ensures configuration is accessible throughout the application.
    """
    
    def __init__(self):
        """
        Initialize configuration with values from environment variables.
        
        Reads all configuration from environment variables, applying appropriate
        type conversions and providing default values where needed. The environment
        variables follow a consistent naming convention and are grouped by functional
        area for better organization.
        """
        # Agent configuration - Core identity parameters
        # EXECUTOR_NAME: Human-readable identifier for this executor instance
        self.agent_name = os.environ.get("EXECUTOR_NAME", "ExecutorAgent")
        # EXECUTOR_ID: Unique identifier for this executor, auto-generated if None
        self.agent_id = os.environ.get("EXECUTOR_ID", None)  # Will be auto-generated if None
        
        # Connection settings for orchestrator API
        # ORCHESTRATOR_API_URL: Base URL of the orchestrator service API
        self.api_base_url = os.environ.get("ORCHESTRATOR_API_URL", "http://localhost:8000")
        # AUTH_ENABLED: Whether authentication is required for API calls (true/false)
        self.auth_enabled = os.environ.get("AUTH_ENABLED", "true").lower() == "true"
        # AUTH_USERNAME: Username for basic authentication with orchestrator API
        self.auth_username = os.environ.get("AUTH_USERNAME", "executor")
        # AUTH_PASSWORD: Password for basic authentication with orchestrator API
        self.auth_password = os.environ.get("AUTH_PASSWORD", "executor_password")
        
        # RabbitMQ settings for asynchronous messaging
        # RABBITMQ_ENABLED: Whether to use RabbitMQ for event communication (true/false)
        self.rabbitmq_enabled = os.environ.get("RABBITMQ_ENABLED", "true").lower() == "true"
        # RABBITMQ_HOST: Hostname or IP address of RabbitMQ server
        self.rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
        # RABBITMQ_PORT: TCP port for RabbitMQ connections (default: 5672)
        self.rabbitmq_port = int(os.environ.get("RABBITMQ_PORT", "5672"))
        # RABBITMQ_USER: Username for authenticating with RabbitMQ
        self.rabbitmq_user = os.environ.get("RABBITMQ_USER", "guest")
        # RABBITMQ_PASSWORD: Password for authenticating with RabbitMQ
        self.rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD", "guest")
        # RABBITMQ_VHOST: Virtual host to use on the RabbitMQ server
        self.rabbitmq_vhost = os.environ.get("RABBITMQ_VHOST", "/")
        
        # Task polling settings - Controls how frequently the agent checks for new tasks
        # POLLING_INTERVAL: Initial time between task poll attempts in seconds
        self.polling_interval = float(os.environ.get("POLLING_INTERVAL", "2.0"))
        # POLLING_BACKOFF_FACTOR: Multiplier for exponential backoff when no tasks are available
        self.polling_backoff_factor = float(os.environ.get("POLLING_BACKOFF_FACTOR", "1.5"))
        # POLLING_MAX_INTERVAL: Maximum time between polls in seconds, regardless of backoff
        self.polling_max_interval = float(os.environ.get("POLLING_MAX_INTERVAL", "60.0"))
        
        # Task execution settings - Parameters controlling task execution behavior
        # TASK_TIMEOUT: Maximum time in seconds a task can run before being considered failed
        self.task_timeout = float(os.environ.get("TASK_TIMEOUT", "300.0"))  # 5 minutes default
        # MAX_CONCURRENT_TASKS: Maximum number of tasks that can be executed simultaneously
        self.max_concurrent_tasks = int(os.environ.get("MAX_CONCURRENT_TASKS", "1"))
        # CAPABILITIES: Comma-separated list of capabilities this executor supports
        # These capabilities are advertised to the orchestrator for task matching
        self.capabilities = os.environ.get("CAPABILITIES", "").split(",")
        self.capabilities = [c.strip() for c in self.capabilities if c.strip()]
        
        # Storage settings for large results - Controls where task outputs are stored
        # RESULT_STORAGE_ENABLED: Whether to use external storage for large task results
        self.result_storage_enabled = os.environ.get("RESULT_STORAGE_ENABLED", "false").lower() == "true"
        # RESULT_STORAGE_TYPE: Storage backend type ('local', 'supabase', etc.)
        self.result_storage_type = os.environ.get("RESULT_STORAGE_TYPE", "local")  # "local", "supabase", etc.
        # RESULT_STORAGE_PATH: File path for local storage or relative path for remote storage
        self.result_storage_path = os.environ.get("RESULT_STORAGE_PATH", "./results")
        
        # Supabase storage configuration (when result_storage_type is "supabase")
        # SUPABASE_URL: Base URL for Supabase instance
        self.supabase_url = os.environ.get("SUPABASE_URL", "")
        # SUPABASE_KEY: API key for authenticating with Supabase
        self.supabase_key = os.environ.get("SUPABASE_KEY", "")
        # SUPABASE_BUCKET: Storage bucket name for task results in Supabase
        self.supabase_bucket = os.environ.get("SUPABASE_BUCKET", "task-results")
        
        # Metrics and monitoring - Configuration for operational telemetry
        # METRICS_INTERVAL: How often (in seconds) to report performance metrics
        self.metrics_interval = float(os.environ.get("METRICS_INTERVAL", "60.0"))  # 1 minute default
        # HEARTBEAT_INTERVAL: How often (in seconds) to send heartbeat signals to orchestrator
        self.heartbeat_interval = float(os.environ.get("HEARTBEAT_INTERVAL", "30.0"))  # 30 seconds default
        
        # Logging configuration
        # LOG_LEVEL: Minimum severity level for log messages (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        # Convert string log level to Python logging module constant, falling back to INFO
        self.log_level = getattr(logging, log_level, logging.INFO)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to a dictionary, with sensitive values masked.
        
        Returns:
            Dict[str, Any]: A dictionary containing all configuration parameters,
                with sensitive values like passwords and API keys masked for 
                security when logging or displaying the configuration.
        """
        # Create a dictionary from all instance attributes
        config_dict = {k: v for k, v in self.__dict__.items()}
        
        # Mask sensitive values to prevent leaking secrets in logs or debug output
        sensitive_keys = ["auth_password", "rabbitmq_password", "supabase_key"]
        for key in sensitive_keys:
            if key in config_dict and config_dict[key]:
                config_dict[key] = "********"
        
        return config_dict


# Create a global config instance that can be imported and used throughout the application
# This follows the singleton pattern to ensure consistent configuration throughout the app
config = ExecutorConfig()
