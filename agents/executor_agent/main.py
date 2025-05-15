#!/usr/bin/env python
"""
Executor Agent main application entry point.

This module serves as the application entry point for the executor agent subsystem.
It handles:
1. Application initialization and configuration loading
2. Setting up logging and monitoring
3. Component instantiation and wiring
4. Task handler registration
5. Main execution loop management
6. Graceful shutdown and cleanup

The executor agent is designed to be run as a standalone service, either
directly or in a containerized environment. It communicates with the
orchestrator system through its configured task poller implementation.

This module demonstrates the full initialization flow for the executor agent,
showing how all components connect together into a complete system.
"""
import logging
import sys
import time
import asyncio
import os
import signal

from agents.executor_agent.executor_agent import ExecutorAgent
from agents.executor_agent.services.api_task_poller import ApiTaskPoller
from agents.executor_agent.services.generic_task_handler import GenericTaskHandler
from agents.executor_agent.config import config

# Set up logging
logging.basicConfig(
    level=config.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"executor_agent_{time.strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """
    Initialize and run the executor agent.
    
    This asynchronous function serves as the main entry point for the executor agent.
    It performs the complete initialization sequence:
    
    1. Sets up the task poller for communication with the orchestrator
    2. Creates the executor agent instance with the configured identity
    3. Registers all required task handlers
    4. Starts the agent's main execution loop
    5. Handles cleanup on shutdown
    
    The function uses proper exception handling to ensure errors are logged
    and the process exits with appropriate status codes.
    
    Returns:
        None
        
    Raises:
        SystemExit: With appropriate exit codes if initialization or execution fails
    """
    logger.info(f"Starting Executor Agent: {config.agent_name}")
    logger.info(f"Configuration: {config.to_dict()}")
    
    try:
        # Initialize task poller
        task_poller = ApiTaskPoller(
            executor_id=config.agent_id or f"executor-{os.getpid()}",
            capabilities=config.capabilities
        )
        await task_poller.initialize()
        
        # Initialize executor agent
        executor = ExecutorAgent(
            executor_id=config.agent_id,
            name=config.agent_name,
            task_poller=task_poller
        )
        
        # Register task handlers
        # The generic handler provides basic task types like echo, delay, and data transformation
        # Additional specialized handlers can be registered here as needed
        generic_handler = GenericTaskHandler()
        executor.register_handler(generic_handler)
        
        # Log the capabilities and task types available
        logger.info(f"Executor capabilities: {executor.capabilities}")
        logger.info(f"Supported task types: {executor.supported_task_types}")
        
        # Start the executor's main processing loop
        # This call is blocking and will only return on shutdown
        await executor.start()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down")
    
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1)
    
    finally:
        # Cleanup phase - ensure we properly clean up resources
        # This runs whether the agent exited normally or due to an exception
        # Close the task poller if it was successfully initialized
        # This ensures proper cleanup of HTTP sessions and other resources
        if 'task_poller' in locals() and task_poller:
            logger.info("Closing task poller connection...")
            await task_poller.close()
            
        logger.info("Executor agent shutdown complete")


if __name__ == "__main__":
    """
    Script entry point - runs the main async function when executed directly.
    
    This conditional block ensures the script can be both run directly as
    an application and imported as a module for testing or integration.
    When run directly, it sets up the asyncio event loop and runs the main
    function that initializes and starts the executor agent.
    """
    # Use asyncio.run() to properly set up and tear down the event loop
    # This handles event loop lifecycle, ensuring proper cleanup on exit
    asyncio.run(main())
