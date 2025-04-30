#!/usr/bin/env python3
"""
Redis State Client for Agent A

This module provides functions for managing agent state via the MCP server's Redis integration.
"""

import os
import requests
import json
from typing import Dict, Any, Optional

# MCP Server connection settings
MCP_HOST = os.environ.get('MCP_HOST', 'mcp-server')
MCP_PORT = int(os.environ.get('MCP_PORT', 8000))
MCP_BASE_URL = f"http://{MCP_HOST}:{MCP_PORT}"
AGENT_NAME = 'agent_a'

class StateClient:
    """Client for managing agent state through the MCP Redis integration"""
    
    def __init__(self, agent_id: str = AGENT_NAME, base_url: str = MCP_BASE_URL):
        """
        Initialize the state client
        
        Args:
            agent_id: Agent identifier (default: agent_a)
            base_url: MCP server base URL
        """
        self.agent_id = agent_id
        self.base_url = base_url
        self.state_url = f"{base_url}/agent/{agent_id}/state"
        
    def get_state(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the agent's current state
        
        Returns:
            Optional[Dict[str, Any]]: The agent state or None if not found or error
        """
        try:
            response = requests.get(self.state_url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"[{self.agent_id}] No state found")
                return None
            else:
                print(f"[{self.agent_id}] Failed to get state: {response.text}")
                return None
        except Exception as e:
            print(f"[{self.agent_id}] Error getting state: {e}")
            return None
            
    def update_state(self, state: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Update the agent's state
        
        Args:
            state: The new state data
            ttl: Time-to-live in seconds (default: 1 hour)
            
        Returns:
            bool: Success or failure
        """
        try:
            response = requests.post(
                self.state_url, 
                json=state,
                params={"ttl": ttl}
            )
            if response.status_code == 200:
                return True
            else:
                print(f"[{self.agent_id}] Failed to update state: {response.text}")
                return False
        except Exception as e:
            print(f"[{self.agent_id}] Error updating state: {e}")
            return False
            
    def delete_state(self) -> bool:
        """
        Delete the agent's state
        
        Returns:
            bool: Success or failure
        """
        try:
            response = requests.delete(self.state_url)
            if response.status_code in (200, 204):
                return True
            else:
                print(f"[{self.agent_id}] Failed to delete state: {response.text}")
                return False
        except Exception as e:
            print(f"[{self.agent_id}] Error deleting state: {e}")
            return False
            
    def update_or_create(self, state_update: Dict[str, Any]) -> bool:
        """
        Update existing state or create new if none exists
        
        Args:
            state_update: The state data to update or create
            
        Returns:
            bool: Success or failure
        """
        try:
            current_state = self.get_state()
            if current_state:
                # Update existing state
                current_state.update(state_update)
                return self.update_state(current_state)
            else:
                # Create new state
                return self.update_state(state_update)
        except Exception as e:
            print(f"[{self.agent_id}] Error updating/creating state: {e}")
            return False
