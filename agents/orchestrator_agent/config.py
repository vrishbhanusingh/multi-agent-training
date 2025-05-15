"""
Configuration module for the orchestrator agent.

This module provides a centralized, extensible, and environment-aware configuration system for the orchestrator agent. It is responsible for:

1. **Loading configuration from environment variables**: All critical settings (database, message queue, API, JWT, logging) are loaded from environment variables, with sensible defaults for local development and containerized deployment.
2. **Providing a single source of truth**: The `Config` class exposes all configuration values as attributes, ensuring consistency across the codebase.
3. **Supporting runtime introspection and logging**: The configuration can be converted to a dictionary (with sensitive values masked) for logging and debugging.
4. **Type safety and validation**: All configuration values are parsed and cast to the correct types, with fallback defaults to prevent startup failures.
5. **Singleton pattern**: A single `config` instance is created and used throughout the orchestrator agent, ensuring all components share the same configuration state.

**Key Configuration Areas:**
- **PostgreSQL**: Connection details, pooling, and timeouts for DAG/task storage
- **RabbitMQ**: Connection, authentication, and queue/exchange naming for task distribution
- **API Server**: Host, port, worker count, and timeouts for the FastAPI server
- **JWT**: Secret key, algorithm, and expiration for authentication
- **Logging**: Log level and format for all agent logs

This module is designed for extensibility: new configuration options can be added as needed, and the `to_dict`/`log_config` methods ensure that configuration state is always observable for debugging and support.
"""
import os
import logging
from typing import Dict, Any, Optional

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """Configuration for the orchestrator agent."""
    
    def __init__(self):
        """Initialize with default values and environment variables."""
        # Database configuration
        self.postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_user = os.getenv("POSTGRES_USER", "postgres")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        self.postgres_db = os.getenv("POSTGRES_DB", "orchestrator")
        self.postgres_pool_size = int(os.getenv("POSTGRES_POOL_SIZE", "10"))
        self.postgres_max_overflow = int(os.getenv("POSTGRES_MAX_OVERFLOW", "20"))
        self.postgres_pool_timeout = int(os.getenv("POSTGRES_POOL_TIMEOUT", "30"))
        
        # RabbitMQ configuration
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "admin")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "admin")
        self.rabbitmq_vhost = os.getenv("RABBITMQ_VHOST", "/")
        self.rabbitmq_exchange = os.getenv("RABBITMQ_EXCHANGE", "orchestrator")
        self.rabbitmq_queue_prefix = os.getenv("RABBITMQ_QUEUE_PREFIX", "tasks")
        self.rabbitmq_connection_attempts = int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "5"))
        self.rabbitmq_retry_delay = int(os.getenv("RABBITMQ_RETRY_DELAY", "5"))
        
        # API configuration
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.api_debug = os.getenv("API_DEBUG", "False").lower() == "true"
        self.api_workers = int(os.getenv("API_WORKERS", "4"))
        self.api_timeout = int(os.getenv("API_TIMEOUT", "60"))
        
        # JWT configuration
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-in-production")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_minutes = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))
        
        # Logging configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_format = os.getenv(
            "LOG_FORMAT", 
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # Set log level
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format=self.log_format
        )
    
    @property
    def postgres_connection_string(self) -> str:
        """Get the PostgreSQL connection string."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary."""
        return {
            "postgres": {
                "host": self.postgres_host,
                "port": self.postgres_port,
                "user": self.postgres_user,
                "database": self.postgres_db,
                "pool_size": self.postgres_pool_size,
                "max_overflow": self.postgres_max_overflow,
                "pool_timeout": self.postgres_pool_timeout,
            },
            "rabbitmq": {
                "host": self.rabbitmq_host,
                "port": self.rabbitmq_port,
                "user": self.rabbitmq_user,
                "vhost": self.rabbitmq_vhost,
                "exchange": self.rabbitmq_exchange,
                "queue_prefix": self.rabbitmq_queue_prefix,
                "connection_attempts": self.rabbitmq_connection_attempts,
                "retry_delay": self.rabbitmq_retry_delay,
            },
            "api": {
                "host": self.api_host,
                "port": self.api_port,
                "debug": self.api_debug,
                "workers": self.api_workers,
                "timeout": self.api_timeout,
            },
            "logging": {
                "level": self.log_level,
            }
        }
    
    def log_config(self) -> None:
        """Log the configuration (with sensitive information masked)."""
        config_dict = self.to_dict()
        
        # Mask sensitive information
        if "postgres" in config_dict and "password" in config_dict["postgres"]:
            config_dict["postgres"]["password"] = "********"
        if "rabbitmq" in config_dict and "password" in config_dict["rabbitmq"]:
            config_dict["rabbitmq"]["password"] = "********"
        if hasattr(self, "jwt_secret_key"):
            config_dict["jwt"] = {"secret_key": "********"}
        
        logger.info(f"Configuration: {config_dict}")


# Create a singleton instance
config = Config()
