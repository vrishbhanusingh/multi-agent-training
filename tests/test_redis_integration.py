#!/usr/bin/env python3
"""
Integration tests for Redis state and memory functionality.
"""

import sys
import os
import unittest
import json
import time
import requests
import asyncio
from datetime import datetime
import uuid

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp.redis_client import RedisClient
from agents.agent_a.redis_state import StateClient as StateClientA
from agents.agent_a.redis_memory import MemoryClient as MemoryClientA

# Test configuration
MCP_HOST = os.getenv('MCP_HOST', 'http://localhost:8000')
TEST_AGENT_ID = f"test_agent_{uuid.uuid4().hex[:8]}"

class TestRedisIntegration(unittest.TestCase):
    """Integration tests for Redis state and memory functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before running tests."""
        # Direct Redis client for verification
        cls.redis_client = RedisClient()
        
        # Agent API clients
        cls.state_client = StateClientA(agent_id=TEST_AGENT_ID)
        cls.memory_client = MemoryClientA(agent_id=TEST_AGENT_ID)
        
        # Test timestamp
        cls.timestamp = datetime.now().isoformat()
        os.environ["TIMESTAMP"] = cls.timestamp
    
    async def delete_agent_state_async(self, agent_id):
        """Async wrapper for delete_agent_state"""
        return await self.redis_client.delete_agent_state(agent_id)
        
    async def clear_memory_async(self, agent_id):
        """Async wrapper for clear_memory"""
        return await self.redis_client.clear_memory(agent_id)
    
    def setUp(self):
        """Set up before each test."""
        # Clean up any existing test data
        # We need to run these async methods in a non-async context
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.delete_agent_state_async(TEST_AGENT_ID))
        loop.run_until_complete(self.clear_memory_async(TEST_AGENT_ID))
    
    def test_state_storage_and_retrieval(self):
        """Test that agent state can be stored and retrieved correctly."""
        # Test data
        test_state = {
            "status": "active",
            "last_activity": "sending_message",
            "last_update": self.timestamp,
            "configuration": {
                "model": "gemini-2.5-pro",
                "response_mode": "concise"
            }
        }
        
        # Store state via client
        self.state_client.update_or_create(test_state)
        
        # Retrieve state via client
        retrieved_state = self.state_client.get_state()
        
        # Verify state was stored correctly
        self.assertIsNotNone(retrieved_state)
        self.assertEqual(retrieved_state.get("status"), "active")
        self.assertEqual(retrieved_state.get("last_activity"), "sending_message")
        
        # Verify via direct Redis access
        loop = asyncio.get_event_loop()
        raw_state = loop.run_until_complete(self.redis_client.get_agent_state(TEST_AGENT_ID))
        self.assertIsNotNone(raw_state)
        self.assertEqual(raw_state.get("status"), "active")
    
    def test_state_ttl(self):
        """Test that state TTL is properly set."""
        # Store state with TTL
        test_state = {"status": "active", "timestamp": self.timestamp}
        self.state_client.update_or_create(test_state, ttl=2)
        
        # Verify state exists
        self.assertIsNotNone(self.state_client.get_state())
        
        # Wait for TTL to expire
        time.sleep(3)
        
        # State should be gone
        self.assertIsNone(self.state_client.get_state())
    
    def test_memory_message_storage_and_retrieval(self):
        """Test storing and retrieving message memories."""
        # Test message data
        test_message = {
            "sender": "agent_a",
            "recipient": "agent_b",
            "content": "Hello from integration test!",
            "sent_at": self.timestamp
        }
        
        # Store message via client
        self.memory_client.store_message(test_message)
        
        # Retrieve messages
        messages = self.memory_client.get_messages()
        
        # Verify message was stored correctly
        self.assertGreaterEqual(len(messages), 1)
        found = False
        for msg in messages:
            if msg.get("data", {}).get("content") == "Hello from integration test!":
                found = True
                break
        self.assertTrue(found, "Stored message was not found in retrieved messages")
    
    def test_memory_thinking_storage_and_retrieval(self):
        """Test storing and retrieving thinking memories."""
        # Test thinking data
        test_thinking = {
            "prompt": "Consider the implications of this message...",
            "timestamp": self.timestamp
        }
        
        # Store thinking via client
        self.memory_client.store_thinking(test_thinking)
        
        # Retrieve thinking entries
        thinking_entries = self.memory_client.get_thinking()
        
        # Verify thinking was stored correctly
        self.assertGreaterEqual(len(thinking_entries), 1)
        found = False
        for entry in thinking_entries:
            if "prompt" in entry.get("data", {}) and "Consider the implications" in entry.get("data", {}).get("prompt"):
                found = True
                break
        self.assertTrue(found, "Stored thinking was not found in retrieved entries")
    
    def test_conversation_context_retrieval(self):
        """Test conversation context retrieval functionality."""
        # Store a sequence of messages
        messages = [
            {
                "sender": "agent_a",
                "recipient": "agent_b",
                "content": "Hello agent B!",
                "sent_at": self.timestamp
            },
            {
                "sender": "agent_b", 
                "content": "Hi agent A, how are you?",
                "received_at": self.timestamp
            },
            {
                "sender": "agent_a",
                "recipient": "agent_b",
                "content": "I'm doing well, thank you!",
                "sent_at": self.timestamp
            }
        ]
        
        # Store messages
        for msg in messages:
            self.memory_client.store_message(msg)
        
        # Get conversation context
        context = self.memory_client.get_conversation_context(max_messages=5)
        
        # Verify context structure
        self.assertIsInstance(context, str)
        self.assertIn("Hello agent B!", context)
        self.assertIn("Hi agent A, how are you?", context)
        self.assertIn("I'm doing well, thank you!", context)
    
    def test_api_endpoints_directly(self):
        """Test the MCP server API endpoints directly."""
        # Test state endpoint
        state_url = f"{MCP_HOST}/agent/{TEST_AGENT_ID}/state"
        test_state = {"status": "testing_api", "timestamp": self.timestamp}
        
        # PUT state
        put_response = requests.put(state_url, json=test_state)
        self.assertEqual(put_response.status_code, 200)
        
        # GET state
        get_response = requests.get(state_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json().get("status"), "testing_api")
        
        # Test memory endpoint for adding an entry
        memory_url = f"{MCP_HOST}/agent/{TEST_AGENT_ID}/memory/entry"
        test_memory = {
            "type": "message",
            "data": {
                "sender": "api_test",
                "content": "Testing direct API access",
                "timestamp": self.timestamp
            }
        }
        
        # POST memory entry
        post_response = requests.post(memory_url, json=test_memory)
        self.assertEqual(post_response.status_code, 200)
        
        # GET memory entries
        get_memory_url = f"{MCP_HOST}/agent/{TEST_AGENT_ID}/memory/message"
        get_memory_response = requests.get(get_memory_url)
        self.assertEqual(get_memory_response.status_code, 200)
        
        # Verify the entry is in the response
        memory_entries = get_memory_response.json()
        found = False
        for entry in memory_entries:
            if entry.get("data", {}).get("content") == "Testing direct API access":
                found = True
                break
        self.assertTrue(found, "Memory entry was not found via API")
    
    def test_memory_pagination(self):
        """Test memory pagination functionality."""
        # Store multiple entries
        for i in range(10):
            self.memory_client.store_observation({
                "observation": f"Test observation {i}",
                "timestamp": self.timestamp
            })
        
        # Retrieve with limit
        entries_limit_5 = self.memory_client.get_observations(limit=5)
        self.assertEqual(len(entries_limit_5), 5)
        
        # Retrieve all
        all_entries = self.memory_client.get_observations(limit=20)
        self.assertGreaterEqual(len(all_entries), 10)

if __name__ == '__main__':
    unittest.main()
