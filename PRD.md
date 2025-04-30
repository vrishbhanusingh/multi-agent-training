# Product Requirements Document (PRD)

## Overview
This project is a scalable, distributed multi-agent system designed to enable robust agent-to-agent communication and state management. It leverages Docker Compose for orchestration, RabbitMQ for messaging, Redis for agent state/memory, and FastAPI for the MCP (Master Control Program) server. The system is intended for developers and researchers building, testing, and evolving distributed agent workflows, with a focus on modularity, extensibility, and automated testing.

## Core Features
- **Multi-Agent Architecture**: Each agent (agent_a, agent_b, agent_c) runs in its own Docker container, with isolated codebases and dependencies.
- **Agent Messaging via RabbitMQ**: Agents communicate using a topic exchange, supporting both direct and broadcast messages. Each agent has its own queue.
- **Stateful Agents with Redis**: Agents can store and retrieve state and memory using Redis, managed via the MCP server.
- **MCP Server (FastAPI)**: Exposes HTTP endpoints for agent registration, state/memory management, and message routing.
- **Automated Testing**: Each agent includes pytest-based tests for RabbitMQ integration, with a root script to run all tests in sequence. A dedicated testing agent enables scripted communication tests.
- **Docker Compose Orchestration**: All services (agents, RabbitMQ, Redis, MCP server) are orchestrated via Docker Compose, ensuring reproducibility and easy scaling.

## User Experience
- **User Personas**: 
  - Developers building distributed agent systems
  - Researchers experimenting with agent communication patterns
- **Key User Flows**:
  - Start all services with a single Docker Compose command
  - Register agents and manage their state via the MCP API
  - Send and receive messages between agents, or broadcast to all
  - Run automated tests to verify integration and communication
- **UI/UX Considerations**: 
  - No frontend UI; interaction is via API, logs, and test scripts
  - Clear logging for all agent actions and message flows

## Technical Architecture
- **System Components**:
  - `mcp/`: FastAPI server for agent management and messaging
  - `agents/`: Individual agent folders (agent_a, agent_b, agent_c, testing_agent)
  - `docker-compose.yml`: Orchestrates all containers
  - `project_logs/`: Documentation and experiment logs
- **Data Models**:
  - Agent state and memory stored as JSON/hashes in Redis
  - Messages routed via RabbitMQ topic exchange (`agent_communication`)
- **APIs and Integrations**:
  - MCP server exposes endpoints for health, agent state/memory, registration, message sending, and broadcast
  - Agents connect to RabbitMQ and Redis using Docker Compose service names
- **Infrastructure Requirements**:
  - Docker and Docker Compose
  - Python 3.10+ for agents and MCP
  - RabbitMQ and Redis services

## Development Roadmap
- **MVP Requirements**:
  - Stand up all core services (RabbitMQ, Redis, MCP, agents)
  - Implement agent registration, state/memory management, and messaging
  - Provide automated tests for agent communication
  - Document architecture and usage
- **Future Enhancements**:
  - Add authentication/authorization to MCP endpoints
  - Expand agent logic and inter-agent workflows
  - Add persistent logging and monitoring
  - Implement advanced message routing and error handling
  - Integrate with CI/CD for automated testing

## Logical Dependency Chain
- Foundation: Set up Docker Compose, RabbitMQ, Redis, and MCP server
- Next: Implement agent containers and basic messaging
- Then: Add automated testing and the testing agent
- After: Expand agent logic, add advanced features, and improve test coverage
- Always: Ensure each feature is atomic and can be built upon in future iterations

## Risks and Mitigations
- **Technical Challenges**: Ensuring reliable message delivery and agent state consistency. Mitigation: Use robust libraries (pika, redis-py), automated tests, and Docker health checks.
- **MVP Scope**: Risk of over-engineering. Mitigation: Focus on core agent communication and state management first.
- **Resource Constraints**: Docker resource usage and service startup order. Mitigation: Use health checks and clear documentation.

## Appendix
- See `project_logs/` for detailed experiment and architecture logs
- Example test scripts and usage instructions in `agents/testing_agent/`
- All endpoints and integration details documented in `mcp/` and logs 