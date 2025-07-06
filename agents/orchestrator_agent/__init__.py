"""
Main module for the orchestrator agent.
This module provides access to the FastAPI app for uvicorn deployment.
"""

from agents.orchestrator_agent.controllers.api import app

# Export the FastAPI app for uvicorn
# When running with uvicorn, we use: uvicorn agents.orchestrator_agent:app
