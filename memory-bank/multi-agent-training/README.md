# Multi-Agent Training Project (Memory Bank Entry)

## Project Overview
This project implements a scalable, distributed multi-agent system for agent communication, state management, and automated testing. The system is built using FastAPI (for the MCP server), Redis (for agent state and memory), RabbitMQ (for agent-to-agent messaging), and Docker Compose (for orchestration).

## Key Features
- **Multiple Agents**: Each agent runs in its own container and communicates via RabbitMQ.
- **MCP Server**: FastAPI-based server for agent registration, state, memory, and message routing.
- **Redis Integration**: Agents and the MCP use Redis for fast, persistent state and memory storage.
- **Automated Testing**: Pytest-based tests for all agents, with a shell script to run all tests in Docker Compose.
- **Extensible Architecture**: Easy to add new agents, tests, and features.

## Architecture Summary
- **Agents**: agent_a, agent_b, agent_c, and a testing agent, each with their own Dockerfile and test suite.
- **MCP**: Exposes HTTP endpoints for agent management and messaging.
- **RabbitMQ**: Topic exchange for agent communication, with agent-specific queues.
- **Redis**: Stores agent state and memory as JSON/hashes.
- **Docker Compose**: Orchestrates all services and provides a unified development and test environment.

## Usage
- Bring up the system: `docker compose up -d --build`
- Run all agent tests: `./run_all_agent_tests.sh`

## Next Steps
- Expand agent logic and inter-agent communication
- Add more advanced tests and CI integration
- Implement monitoring, authentication, and lifecycle management

---
This entry was auto-generated from project logs for the memory bank.
