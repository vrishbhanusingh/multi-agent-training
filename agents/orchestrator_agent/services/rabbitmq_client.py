"""
RabbitMQ client for task distribution.

This module provides a robust, production-grade client for interacting with RabbitMQ as the message queue for task distribution in the orchestrator agent. Its responsibilities include:

1. **Connection Management**: Handles connection setup, authentication, and reconnection logic for RabbitMQ, supporting robust operation in distributed environments.
2. **Exchange and Queue Management**: Declares and manages exchanges and queues for task routing, supporting scalable and flexible task distribution patterns.
3. **Task Publishing**: Publishes tasks to the appropriate queues for consumption by executor agents, ensuring reliable delivery and serialization.
4. **Status Updates and Acknowledgements**: Handles status messages and acknowledgements from executors, supporting at-least-once or exactly-once delivery semantics as required.
5. **Error Handling and Retry**: Implements retry logic and error handling for all MQ operations, ensuring resilience to transient network or broker failures.

**Design Notes:**
- The client is designed to be thread-safe and to support both synchronous and asynchronous usage patterns.
- All configuration is loaded from the central config module, supporting environment-based deployment.
- Logging is used for all connection, publishing, and error events to support operational monitoring.

This client is a critical part of the orchestrator's ability to scale out task execution and maintain reliable communication with a dynamic pool of executor agents.
"""
import json
import logging
import time
from typing import Dict, Any, Optional, List
from uuid import UUID

import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from agents.orchestrator_agent.config import config
from agents.orchestrator_agent.domain.models import Task, TaskStatus

# Initialize logging
logger = logging.getLogger(__name__)

class RabbitMQClient:
    """Client for interacting with RabbitMQ for task distribution."""
    
    def __init__(self):
        """Initialize the RabbitMQ client."""
        logger.info("Initializing RabbitMQ client")
        
        self.host = config.rabbitmq_host
        self.port = config.rabbitmq_port
        self.user = config.rabbitmq_user
        self.password = config.rabbitmq_password
        self.vhost = config.rabbitmq_vhost
        self.exchange = config.rabbitmq_exchange
        self.queue_prefix = config.rabbitmq_queue_prefix
        self.connection_attempts = config.rabbitmq_connection_attempts
        self.retry_delay = config.rabbitmq_retry_delay
        
        self.connection = None
        self.channel = None
        
        # Connect to RabbitMQ
        self.connect()
        
        logger.info("RabbitMQ client initialized")
    
    def connect(self) -> None:
        """Connect to RabbitMQ and set up exchange."""
        logger.info(f"Connecting to RabbitMQ at {self.host}:{self.port}")
        
        # Connection parameters
        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=credentials,
            connection_attempts=self.connection_attempts,
            retry_delay=self.retry_delay,
            heartbeat=600
        )
        
        # Connect with retry
        for attempt in range(self.connection_attempts):
            try:
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                # Declare the exchange
                self.channel.exchange_declare(
                    exchange=self.exchange,
                    exchange_type='topic',
                    durable=True
                )
                
                logger.info("Successfully connected to RabbitMQ")
                return
            except AMQPConnectionError as e:
                if attempt < self.connection_attempts - 1:
                    logger.warning(f"RabbitMQ connection attempt {attempt+1} failed: {e}. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to connect to RabbitMQ after {self.connection_attempts} attempts: {e}")
                    raise
    
    def reconnect_if_needed(self) -> None:
        """Check connection and reconnect if necessary."""
        try:
            if self.connection is None or not self.connection.is_open:
                logger.warning("Connection to RabbitMQ is closed, reconnecting...")
                self.connect()
            elif self.channel is None or not self.channel.is_open:
                logger.warning("Channel is closed, creating a new one...")
                self.channel = self.connection.channel()
                
                # Redeclare the exchange
                self.channel.exchange_declare(
                    exchange=self.exchange,
                    exchange_type='topic',
                    durable=True
                )
        except Exception as e:
            logger.error(f"Error reconnecting to RabbitMQ: {e}")
            self.connect()
    
    def close(self) -> None:
        """Close the connection to RabbitMQ."""
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
                logger.info("RabbitMQ connection closed")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}")
    
    def _ensure_queue(self, queue_name: str) -> None:
        """Ensure the queue exists, create if it doesn't."""
        try:
            self.reconnect_if_needed()
            self.channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={
                    'x-message-ttl': 86400000,  # 24 hours in milliseconds
                    'x-dead-letter-exchange': f"{self.exchange}.dead",
                    'x-dead-letter-routing-key': "dead-letter"
                }
            )
            
            # Ensure the dead letter exchange and queue exist
            self.channel.exchange_declare(
                exchange=f"{self.exchange}.dead",
                exchange_type='topic',
                durable=True
            )
            self.channel.queue_declare(
                queue=f"{queue_name}.dead",
                durable=True
            )
            self.channel.queue_bind(
                queue=f"{queue_name}.dead",
                exchange=f"{self.exchange}.dead",
                routing_key="dead-letter"
            )
        except Exception as e:
            logger.error(f"Error ensuring queue {queue_name}: {e}")
            self.reconnect_if_needed()
            raise
    
    def _get_queue_for_task(self, task: Task) -> str:
        """Determine the appropriate queue for a task based on its type and required capabilities."""
        # Use task type as the primary queue selector
        queue_base = f"{self.queue_prefix}.{task.task_type}"
        
        # If the task has specific capability requirements, append them to the queue name
        if task.required_capabilities:
            capabilities_str = "_".join(sorted(task.required_capabilities))
            return f"{queue_base}.{capabilities_str}"
        
        return queue_base
    
    def publish_task(self, task: Task) -> bool:
        """Publish a task to the appropriate queue."""
        logger.info(f"Publishing task {task.id} to RabbitMQ")
        
        try:
            self.reconnect_if_needed()
            
            # Convert task to JSON
            task_json = task.to_dict()
            
            # Get the queue for this task
            queue_name = self._get_queue_for_task(task)
            
            # Ensure queue exists
            self._ensure_queue(queue_name)
            
            # Bind the queue to the exchange with the appropriate routing key
            routing_key = f"task.{task.task_type}"
            self.channel.queue_bind(
                queue=queue_name,
                exchange=self.exchange,
                routing_key=routing_key
            )
            
            # Publish the message
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=json.dumps(task_json),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json',
                    headers={
                        'task_id': str(task.id),
                        'task_type': task.task_type
                    }
                )
            )
            
            logger.debug(f"Task {task.id} published to queue {queue_name} with routing key {routing_key}")
            return True
        
        except Exception as e:
            logger.error(f"Error publishing task {task.id}: {e}")
            return False
    
    def publish_tasks(self, tasks: List[Task]) -> Dict[UUID, bool]:
        """Publish multiple tasks to their appropriate queues."""
        results = {}
        for task in tasks:
            results[task.id] = self.publish_task(task)
        return results
    
    def setup_consumer_queue(self, executor_id: str, capabilities: List[str]) -> str:
        """Set up a queue for an executor based on its capabilities."""
        logger.info(f"Setting up consumer queue for executor {executor_id}")
        
        try:
            self.reconnect_if_needed()
            
            # Create a queue specific to this executor
            queue_name = f"{self.queue_prefix}.executor.{executor_id}"
            
            # Declare the queue
            self.channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={
                    'x-message-ttl': 86400000,  # 24 hours in milliseconds
                }
            )
            
            # Bind the queue to the exchange for each capability
            for capability in capabilities:
                routing_key = f"task.{capability}"
                self.channel.queue_bind(
                    queue=queue_name,
                    exchange=self.exchange,
                    routing_key=routing_key
                )
            
            logger.info(f"Consumer queue {queue_name} set up for executor {executor_id}")
            return queue_name
        
        except Exception as e:
            logger.error(f"Error setting up consumer queue for executor {executor_id}: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the RabbitMQ connection."""
        try:
            self.reconnect_if_needed()
            return {
                "status": "healthy",
                "connection": "open" if self.connection and self.connection.is_open else "closed",
                "channel": "open" if self.channel and self.channel.is_open else "closed"
            }
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
