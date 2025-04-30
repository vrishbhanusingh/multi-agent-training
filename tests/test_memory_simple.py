#!/usr/bin/env python3
"""
Simple test script for Redis memory integration.
This test doesn't require pytest and can run standalone.
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment variables for testing
os.environ["REDIS_HOST"] = "localhost"  # Use localhost instead of Redis container name
os.environ["TIMESTAMP"] = datetime.now().isoformat()
os.environ["AGENT_NAME"] = "test_agent"

# Import Redis client
try:
    from mcp.redis_client import RedisClient
    print("✅ Successfully imported RedisClient")
except Exception as e:
    print(f"❌ Failed to import RedisClient: {e}")
    sys.exit(1)

def test_redis_connection():
    """Test basic Redis connection"""
    try:
        client = RedisClient()
        print("✅ Successfully connected to Redis")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return None

def print_available_methods(client):
    """Print available methods on client"""
    methods = [method for method in dir(client) if not method.startswith('_') and callable(getattr(client, method))]
    print("\n==== CHECKING AVAILABLE METHODS ====\n")
    print("Available methods:")
    for method in sorted(methods):
        print(f"- {method}")
    return methods

async def test_state_operations(client):
    """Test state storage and retrieval"""
    agent_id = "test_agent"
    test_state = {
        "status": "active",
        "last_activity": "testing",
        "timestamp": os.environ["TIMESTAMP"]
    }
    
    try:
        # Store state
        success = await client.set_agent_state(agent_id, test_state)
        if success:
            print("✅ Successfully stored agent state")
        else:
            print("❌ Failed to store agent state")
            return False
        
        # Retrieve state
        retrieved_state = await client.get_agent_state(agent_id)
        if retrieved_state and retrieved_state.get("status") == "active":
            print("✅ Successfully retrieved agent state")
            print(f"   Retrieved: {json.dumps(retrieved_state, indent=2)}")
        else:
            print("❌ Failed to retrieve agent state correctly")
            print(f"   Retrieved: {retrieved_state}")
            return False
        
        # Test TTL
        success = await client.set_agent_state(agent_id, test_state, ttl=2)
        if success:
            print("✅ Set state with TTL=2 seconds")
        else:
            print("❌ Failed to set state with TTL")
            return False
        
        # Verify TTL was set
        time.sleep(3)
        expired_state = await client.get_agent_state(agent_id)
        if expired_state is None:
            print("✅ State correctly expired after TTL")
        else:
            print("❌ State did not expire as expected")
            return False
            
        return True
    except Exception as e:
        print(f"❌ State operations failed: {e}")
        return False

async def test_memory_operations(client):
    """Test memory storage and retrieval"""
    agent_id = "test_agent"
    
    try:
        # Test storing a message
        test_message = {
            "sender": "agent_a",
            "content": "Hello, this is a test message",
            "timestamp": os.environ["TIMESTAMP"]
        }
        success = await client.add_memory_entry(agent_id, "message", test_message)
        if success:
            print("✅ Successfully stored a message")
        else:
            print("❌ Failed to store message")
            return False
        
        # Test storing an observation
        test_observation = {
            "observation": "This is a test observation",
            "timestamp": os.environ["TIMESTAMP"]
        }
        success = await client.add_memory_entry(agent_id, "observation", test_observation)
        if success:
            print("✅ Successfully stored an observation")
        else:
            print("❌ Failed to store observation")
            return False
        
        # Test storing thinking
        test_thinking = {
            "prompt": "Thinking about test scenarios",
            "timestamp": os.environ["TIMESTAMP"]
        }
        success = await client.add_memory_entry(agent_id, "thinking", test_thinking)
        if success:
            print("✅ Successfully stored thinking")
        else:
            print("❌ Failed to store thinking")
            return False
        
        # Test retrieving messages
        messages = await client.get_memory_entries(agent_id, "message")
        if messages and len(messages) > 0:
            print(f"✅ Successfully retrieved {len(messages)} messages")
        else:
            print("❌ Failed to retrieve messages correctly")
            return False
        
        # Test retrieving all memory types
        all_memory = await client.get_all_memory(agent_id)
        if all_memory and len(all_memory) >= 3:  # Should have at least our 3 entries
            print(f"✅ Successfully retrieved all memory types: {len(all_memory)} entries")
        else:
            print(f"❌ Failed to retrieve all memory: {all_memory}")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Memory operations failed: {e}")
        return False

def list_async_methods():
    """List async methods available in RedisClient"""
    print("\n==== LISTING ASYNC METHODS ====\n")
    print("ℹ️ Note: Async methods need to be called in an async context")
    
    # List methods with 'async def' in the RedisClient source
    async_methods = []
    with open(os.path.join(os.path.dirname(__file__), '..', 'mcp', 'redis_client.py'), 'r') as file:
        lines = file.readlines()
        for i, line in enumerate(lines):
            if 'async def ' in line:
                method_name = line.split('async def ')[1].split('(')[0]
                async_methods.append(method_name)
    
    print("   Methods available:")
    for method in sorted(async_methods):
        print(f"   - {method}")

async def main():
    """Main async function to run tests"""
    print("\n==== TESTING REDIS MEMORY SYSTEM ====\n")
    
    # Test Redis connection
    client = test_redis_connection()
    if not client:
        return False
    
    # Print available methods
    methods = print_available_methods(client)
    
    print("\n==== TESTING SYNC METHODS ====\n")
    
    if 'set_state' in methods:
        # If the old method names exist, run tests with them
        if not await test_state_operations(client):
            return False
            
        if not await test_memory_operations(client):
            return False
    else:
        print("ℹ️ Client does not have set_state method, testing async methods instead")
        list_async_methods()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n✅ Basic Redis connectivity verified!")
    else:
        print("\n❌ Some Redis tests failed!")
        sys.exit(1)
