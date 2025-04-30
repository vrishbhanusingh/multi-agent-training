#!/usr/bin/env python3
"""
Redis Memory Client for Agent C

This module provides functions for managing agent memory via the MCP server's Redis integration.
"""

import os
import requests
import json
from typing import Dict, Any, Optional, List

# MCP Server connection settings
MCP_HOST = os.environ.get('MCP_HOST', 'mcp-server')
MCP_PORT = int(os.environ.get('MCP_PORT', 8000))
MCP_BASE_URL = f"http://{MCP_HOST}:{MCP_PORT}"
AGENT_NAME = 'agent_c'

class MemoryClient:
    """Client for managing agent memory through the MCP Redis integration"""
    
    def __init__(self, agent_id: str = AGENT_NAME, base_url: str = MCP_BASE_URL):
        """
        Initialize the memory client
        
        Args:
            agent_id: Agent identifier (default: agent_c)
            base_url: MCP server base URL
        """
        self.agent_id = agent_id
        self.base_url = base_url
        self.memory_base_url = f"{base_url}/agent/{agent_id}/memory"
        
    def store_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Store a message in memory
        
        Args:
            message_data: Message data containing content, sender, etc.
            
        Returns:
            bool: Success or failure
        """
        return self._add_memory_entry('message', message_data)
        
    def store_observation(self, observation_data: Dict[str, Any]) -> bool:
        """
        Store an observation in memory
        
        Args:
            observation_data: Observation data to store
            
        Returns:
            bool: Success or failure
        """
        return self._add_memory_entry('observation', observation_data)
        
    def store_thinking(self, thinking_data: Dict[str, Any]) -> bool:
        """
        Store thinking/reasoning data in memory
        
        Args:
            thinking_data: Thinking data containing topic, thoughts, etc.
            
        Returns:
            bool: Success or failure
        """
        return self._add_memory_entry('thinking', thinking_data)
    
    def _add_memory_entry(self, entry_type: str, data: Dict[str, Any]) -> bool:
        """
        Add a memory entry of the specified type
        
        Args:
            entry_type: Type of memory entry
            data: Memory entry data
            
        Returns:
            bool: Success or failure
        """
        try:
            url = f"{self.memory_base_url}/entry"
            response = requests.post(
                url,
                params={"entry_type": entry_type},
                json=data
            )
            if response.status_code == 200:
                return True
            else:
                print(f"[{self.agent_id}] Failed to add memory entry: {response.text}")
                return False
        except Exception as e:
            print(f"[{self.agent_id}] Error adding memory entry: {e}")
            return False
            
    def get_messages(self, limit: int = 10, oldest_first: bool = False) -> List[Dict[str, Any]]:
        """
        Get stored messages from memory
        
        Args:
            limit: Maximum number of messages to retrieve
            oldest_first: If True, return oldest messages first
            
        Returns:
            List[Dict[str, Any]]: List of message entries
        """
        return self._get_memory_entries('message', limit, oldest_first)
        
    def get_observations(self, limit: int = 10, oldest_first: bool = False) -> List[Dict[str, Any]]:
        """
        Get stored observations from memory
        
        Args:
            limit: Maximum number of observations to retrieve
            oldest_first: If True, return oldest observations first
            
        Returns:
            List[Dict[str, Any]]: List of observation entries
        """
        return self._get_memory_entries('observation', limit, oldest_first)
        
    def get_thinking(self, limit: int = 10, oldest_first: bool = False) -> List[Dict[str, Any]]:
        """
        Get stored thinking data from memory
        
        Args:
            limit: Maximum number of thinking entries to retrieve
            oldest_first: If True, return oldest thinking entries first
            
        Returns:
            List[Dict[str, Any]]: List of thinking entries
        """
        return self._get_memory_entries('thinking', limit, oldest_first)
    
    def _get_memory_entries(self, entry_type: str, limit: int = 10, oldest_first: bool = False) -> List[Dict[str, Any]]:
        """
        Get memory entries of the specified type
        
        Args:
            entry_type: Type of memory to retrieve
            limit: Maximum number of entries
            oldest_first: If True, return oldest entries first
            
        Returns:
            List[Dict[str, Any]]: List of memory entries
        """
        try:
            url = f"{self.memory_base_url}/{entry_type}"
            response = requests.get(
                url,
                params={"limit": limit, "oldest_first": oldest_first}
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[{self.agent_id}] Failed to get memory entries: {response.text}")
                return []
        except Exception as e:
            print(f"[{self.agent_id}] Error getting memory entries: {e}")
            return []
            
    def get_all_memory(self, limit: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all memory entries for the agent
        
        Args:
            limit: Maximum entries per type
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary of memory entries by type
        """
        try:
            response = requests.get(
                self.memory_base_url,
                params={"limit": limit}
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[{self.agent_id}] Failed to get memory: {response.text}")
                return {}
        except Exception as e:
            print(f"[{self.agent_id}] Error getting memory: {e}")
            return {}
            
    def clear_memory(self, entry_type: Optional[str] = None) -> bool:
        """
        Clear memory entries
        
        Args:
            entry_type: Optional specific type to clear (None for all)
            
        Returns:
            bool: Success or failure
        """
        try:
            params = {"entry_type": entry_type} if entry_type else {}
            response = requests.delete(
                self.memory_base_url,
                params=params
            )
            if response.status_code == 200:
                return True
            else:
                print(f"[{self.agent_id}] Failed to clear memory: {response.text}")
                return False
        except Exception as e:
            print(f"[{self.agent_id}] Error clearing memory: {e}")
            return False
            
    def get_conversation_context(self, max_messages: int = 5) -> str:
        """
        Get recent message history for context in a conversation
        
        Args:
            max_messages: Maximum number of messages to include
            
        Returns:
            str: Formatted conversation context
        """
        messages = self.get_messages(limit=max_messages)
        if not messages:
            return "No previous conversation."
            
        context = "Recent conversation history:\n"
        for i, msg in enumerate(reversed(messages)):
            data = msg.get("data", {})
            sender = data.get("sender", "unknown")
            content = data.get("content", "")
            context += f"{sender}: {content}\n"
            
        return context
