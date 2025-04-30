#!/usr/bin/env python3
"""
Script to log a conversation in agent memory.
"""
import os
import sys
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Set environment variables for testing
os.environ["REDIS_HOST"] = "localhost"  # Use localhost instead of Redis container name
os.environ["TIMESTAMP"] = datetime.now().isoformat()

# Import the MemoryClient
from agents.agent_a.redis_memory import MemoryClient

def log_conversation(agent_id, conversation_text):
    """Log a conversation in the agent's memory"""
    client = MemoryClient(agent_id=agent_id)
    
    # Store conversation as thinking
    result = client.store_thinking({
        "conversation": conversation_text,
        "timestamp": datetime.now().isoformat(),
        "source": "manual_logging",
        "topic": "Task 5 Implementation Review"
    })
    
    if result:
        print(f"✅ Conversation successfully logged in {agent_id}'s memory")
    else:
        print(f"❌ Failed to log conversation in {agent_id}'s memory")
        print("   This might be because Redis is not running. Make sure docker-compose is up.")
    
    return result

def main():
    """Main function"""
    # Default agent ID
    agent_id = "conversation_logger"
    
    # Summary of our conversation
    conversation = """
Task 5 Implementation Review:

1. Redis Client Implementation:
   - Enhanced Redis client with state and memory storage functions
   - Implemented Redis schemas for agent state and memory with TTL handling
   - Added memory categorization (messages, observations, thinking)

2. MCP Server Integration:
   - Added FastAPI endpoints for state/memory management
   - Implemented proper error handling and status codes
   - Created backward-compatible methods for legacy code

3. Agent Integration:
   - Updated all three agent implementations with memory-aware functions
   - Added message processing with memory context
   - Implemented automatic memory storage of interactions
   - Added state tracking for agent activities

4. Testing & Documentation:
   - Created test_redis_integration.py for comprehensive testing
   - Created test_memory_simple.py for basic functionality testing
   - Updated the task status in tasks.json and task_005.txt

All subtasks for Task 5 have been marked as complete, and the memory system provides:
1. State management for tracking agent status
2. Memory storage for conversations and observations
3. Context enrichment for Gemini prompts
"""
    
    # Log the conversation
    log_conversation(agent_id, conversation)

if __name__ == "__main__":
    main()
