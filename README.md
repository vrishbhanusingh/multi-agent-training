# Multi-Agent Training System

A distributed system for training and testing multiple AI agents that communicate with each other via RabbitMQ messaging. This system includes:

- Three independent agents (agent_a, agent_b, agent_c) with Google Gemini AI integration
- MCP server for centralized control and monitoring
- RabbitMQ for inter-agent messaging
- Redis for state/memory storage

## Features

- **Agent Communication**: Agents can send direct messages to specific agents or broadcast to all
- **Gemini Integration**: Each agent uses Google's Gemini model for "thinking" about messages and generating responses
- **Intelligent Conversations**: Agents can have meaningful exchanges by analyzing received messages and crafting appropriate responses
- **Distributed Architecture**: Each agent runs in its own container with independent processing
- **Memory System**: Agents maintain context and history using Redis-based memory storage
- **State Management**: Track agent states and configurations persistently 

## Environment Setup

To run this system, you need to set the following environment variables:

- `GEMINI_API_KEY`: Your Google AI Studio API key for Gemini
- `GEMINI_MODEL`: (Optional) The Gemini model to use (default: gemini-2.5-pro-exp-03-25)

Alternatively, for Vertex AI:
- `GOOGLE_GENAI_USE_VERTEXAI`: Set to "true" to use Vertex AI instead of API key
- `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID
- `GOOGLE_CLOUD_LOCATION`: (Optional) Region for Vertex AI (default: us-central1)

Redis configuration:
- `REDIS_HOST`: Redis server host (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)
- `REDIS_PASSWORD`: Redis password (optional)

## Agent Memory System

The system includes a comprehensive memory and state management system that allows agents to:

1. **Store and retrieve state information**
2. **Maintain persistent memory across sessions**
3. **Enhance LLM prompts with contextual awareness**
4. **Track conversation history between agents**

### Memory Architecture

The memory system is built on Redis and provides the following capabilities:

#### Agent State

- Each agent maintains a state object in Redis
- State includes current activity, last interactions, and configuration
- State has configurable TTL (Time-To-Live) for automatic cleanup
- Accessed via `/agent/{agent_id}/state` endpoints

#### Agent Memory Types

The memory system supports different types of memory entries:

1. **Messages**: Conversation history between agents
   - Includes sender, recipient, content, and timestamps
   - Tracks both sent and received messages

2. **Observations**: Agent's observations about the environment
   - Records responses from LLM calls
   - Stores any environmental perception data

3. **Thinking**: Internal thought processes of the agent
   - Records prompts sent to the LLM
   - Documents reasoning and decision-making

### Using the Memory System

Each agent includes two client libraries for interacting with memory:

#### State Client (`redis_state.py`)

```python
from redis_state import StateClient

# Initialize the client
state_client = StateClient(agent_id="agent_a")

# Store or update state
state_client.update_or_create({
    "status": "active",
    "last_activity": "processing_message",
    "configuration": {"response_mode": "detailed"}
})

# Get current state
current_state = state_client.get_state()
```

#### Memory Client (`redis_memory.py`)

```python
from redis_memory import MemoryClient

# Initialize the client
memory_client = MemoryClient(agent_id="agent_a")

# Store a message
memory_client.store_message({
    "sender": "agent_a",
    "recipient": "agent_b",
    "content": "Hello agent B!",
    "sent_at": "2023-06-15T14:35:12.345Z"
})

# Store an observation
memory_client.store_observation({
    "observation": "Agent B responded quickly to my greeting",
    "timestamp": "2023-06-15T14:35:15.678Z"
})

# Get conversation context for LLM prompts
context = memory_client.get_conversation_context(max_messages=5)
```

### Memory-Enhanced LLM Integration

The Gemini LLM integration is enhanced with memory context:

```python
def ask_gemini(query: str, use_memory: bool = True):
    if use_memory:
        # Enhance the prompt with memory context
        query = enrich_query_with_memory(query)
    
    # Process with Gemini
    response = client.models.generate_content(model=MODEL, contents=query)
    return response.text

def enrich_query_with_memory(query: str):
    # Get conversation history
    conversation_context = memory_client.get_conversation_context()
    
    # Combine with query
    enhanced_query = f"""
    Memory Context:
    {conversation_context}
    
    Current Query:
    {query}
    """
    return enhanced_query
```

### MCP Server Endpoints

The MCP server provides the following endpoints for memory management:

- `GET /agent/{agent_id}/state` - Retrieve agent state
- `PUT /agent/{agent_id}/state` - Update agent state
- `DELETE /agent/{agent_id}/state` - Clear agent state

- `GET /agent/{agent_id}/memory/{entry_type}` - Get memory entries by type
- `POST /agent/{agent_id}/memory/entry` - Add a new memory entry
- `DELETE /agent/{agent_id}/memory` - Clear all memory for an agent
- `DELETE /agent/{agent_id}/memory/{entry_type}` - Clear memory of specific type