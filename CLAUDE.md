# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Multi-Agent Training System - a distributed system for training and testing multiple AI agents that communicate with each other. The system consists of:

- Three independent agents (agent_a, agent_b, agent_c) with Google Gemini AI integration
- MCP (Master Control Program) server for centralized control and monitoring
- RabbitMQ for inter-agent messaging
- Redis for state/memory storage

## Commands

### Environment Setup

```bash
# Set necessary environment variables
export GEMINI_API_KEY=your_gemini_api_key
export GEMINI_MODEL=gemini-2.5-pro-exp-03-25  # Optional, this is the default

# For Vertex AI (alternative to API key)
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=your_google_cloud_project
export GOOGLE_CLOUD_LOCATION=us-central1  # Optional, this is the default

# Redis config (defaults shown)
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=your_redis_password  # Optional
```

### Running the System

```bash
# Start all services with Docker Compose
docker compose up

# Start in detached mode
docker compose up -d

# Start specific services
docker compose up rabbitmq redis mcp-server agent_a

# Stop services
docker compose down
```

### Running Tests

```bash
# Run all agent tests
./run_all_agent_tests.sh

# Run tests for a specific agent
docker compose exec agent_a pytest
docker compose exec agent_b pytest
docker compose exec agent_c pytest

# Run a specific test
docker compose exec agent_a pytest tests/test_gemini_integration.py
```

### Agent Communication Testing

```bash
# Run the testing agent to send test messages to all agents
docker compose run testing_agent python test_send.py
```

## Architecture

### Core Components

1. **Agents (agent_a, agent_b, agent_c)**
   - Run in isolated Docker containers
   - Use RabbitMQ for inter-agent communication
   - Use Redis for state and memory storage
   - Integrate with Google Gemini LLM for "thinking"

2. **MCP Server**
   - FastAPI server exposing HTTP endpoints
   - Manages agent registration, state/memory, and message routing
   - Provides centralized control and monitoring

3. **RabbitMQ**
   - Message broker for agent-to-agent communication
   - Uses topic exchange pattern ("agent_communication")
   - Each agent has its own dedicated queue

4. **Redis**
   - Stores agent state and memory
   - Manages different memory types (messages, observations, thinking)
   - Maintains conversation history and context

### Agent Memory System

The memory system allows agents to:
- Store and retrieve state information
- Maintain persistent memory across sessions
- Enhance LLM prompts with contextual awareness
- Track conversation history between agents

Memory is implemented using two Redis clients:
- `StateClient`: Manages agent state (status, activity, configuration)
- `MemoryClient`: Handles different memory types (messages, observations, thinking)

### Message Protocol

Agents communicate using Protocol Buffers (protobuf):
- Defined in `common/a2a_protocol/proto/a2a_message.proto`
- Messages include sender, recipient, content, and timestamp
- Serialization/deserialization handled by the protocol module

### Workflow

1. Agents register with the MCP server and create message queues
2. Agents send messages to specific agents or broadcast to all
3. Recipient agents process messages using Gemini LLM
4. Responses are generated and sent back through RabbitMQ
5. All message history and agent states are stored in Redis

## Common Patterns

### Agent Implementation

Each agent follows a similar pattern:
- Background thread for sending messages periodically
- Main loop for receiving and responding to messages
- Memory-enhanced LLM processing
- Rate limiting for responses to avoid circular conversations

### Message Processing Flow

1. Receive message (protobuf) from RabbitMQ
2. Store in agent memory via Redis
3. Process with Gemini LLM, using memory context
4. Generate and send response
5. Update agent state and memory

### Error Handling

The codebase emphasizes:
- Graceful handling of connection failures
- Automatic reconnection to services
- Thread safety for concurrent operations
- Rate limiting to prevent message storms