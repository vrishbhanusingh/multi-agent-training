# Product Requirem## Key User Flows**:
  - Start all services with a single Docker Compose command
  - Submit workflow requests to the orchestrator via its REST API
  - Monitor task execution and DAG progress through status endpoints
  - Retrieve results when workflow execution completes
  - Run automated tests to verify end-to-end workflow processingocument (PRD)

## Overview
This project is a scalable, distributed multi-agent system designed to enable robust workflow orchestration and task execution. It uses a centralized orchestrator agent that plans workflows as Directed Acyclic Graphs (DAGs) and specialized executor agents that perform specific tasks. The system leverages Docker Compose for infrastructure orchestration, Postgres for persistent storage, RabbitMQ for messaging, and FastAPI for API endpoints. It is intended for developers and researchers building complex, multi-step workflows that require coordination between specialized agents, with a focus on modularity, extensibility, and automated testing.

## Core Features
- **Orchestrator-Executor Architecture**: A single orchestrator agent decomposes workflows into discrete tasks with dependencies (DAG), while specialized executor agents perform specific tasks.
- **DAG-Based Workflow Management**: Workflows are represented as Directed Acyclic Graphs with tasks as nodes and dependencies as edges, enabling complex multi-step processing.
- **Self-Improving Workflow Engine via Reinforcement Learning**: The system is designed for resilience and self-improvement. It treats errors not as failures, but as training data. An `EvaluatorAgent` assesses task outcomes, assigning rewards and structured feedback. When a task fails, the `OrchestratorAgent` enters a "Correction Mode" to perform "DAG Surgery," dynamically inserting new corrective tasks into the workflow. The outcomes of these events are used to train the orchestrator's policy via a PPO-based Reinforcement Learning loop, making the system progressively better at planning and problem-solving.
- **Task Distribution via RabbitMQ**: The orchestrator publishes tasks to RabbitMQ queues, and executor agents consume these tasks based on their capabilities.
- **Persistent Storage with Postgres**: DAGs, task statuses, and results are stored in Postgres for durability and queryability.
- **REST API Interface**: The orchestrator exposes HTTP endpoints for workflow submission, DAG visualization, task status monitoring, and result retrieval.
- **Automated Testing**: Comprehensive test suite covering DAG generation, task execution, and end-to-end workflow processing.
- **Docker Compose Orchestration**: All services (orchestrator, executors, Postgres, RabbitMQ) are orchestrated via Docker Compose, ensuring reproducibility and easy scaling.

## User Experience
- **User Personas**: 
  - Developers building distributed agent systems
  - Researchers experimenting with agent communication patterns
- **Key User Flows**:
  - Start all services with a single Docker Compose command
  - Submit workflow requests to the orchestrator via the MCP API
  - Monitor task execution and DAG progress
  - Retrieve results when workflow execution completes
  - Run automated tests to verify end-to-end workflow processing
- **UI/UX Considerations**: 
  - No frontend UI; interaction is via API, logs, and test scripts
  - Clear logging for all agent actions and message flows

## Technical Architecture
- **System Components**:
  - `agents/orchestrator_agent/`: The central orchestrator that plans workflows as DAGs and learns from outcomes.
  - `agents/executor_agents/`: Specialized agents that execute specific task types and report detailed results.
  - `agents/evaluator_agent/`: A new agent that assesses task outcomes, calculates rewards, and generates structured feedback.
  - `docker-compose.yml`: Orchestrates all containers
  - `project_logs/`: Documentation and experiment logs
- **Data Models**:
  - DAGs stored in Postgres with nodes (tasks) and edges (dependencies). A parent `workflows` table tracks the overall state and total reward for an entire user request.
  - Task status and results stored in Postgres for persistence. The `tasks` table is enriched with columns for `reward`, structured `feedback_notes` (JSONB), and `retries` to support the learning loop.
  - Tasks distributed via RabbitMQ queues based on task type and executor capabilities.
- **APIs and Integrations**:
  - Orchestrator REST API for workflow submission, DAG status, and results
  - Task polling interface for executors to retrieve available tasks
  - Result reporting interface for executors to update task status and store results
- **Infrastructure Requirements**:
  - Docker and Docker Compose
  - Python 3.10+ for orchestrator and executor agents
  - RabbitMQ for task distribution
  - Postgres for persistent storage of DAGs, tasks, and results

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
  - **Implement `EvaluatorAgent`**: Build the agent for automated task validation and reward assignment.
  - **Develop Orchestrator "Correction Mode"**: Enhance the `OrchestratorAgent` with the logic to analyze failures and perform "DAG Surgery" to insert corrective tasks.
  - **Integrate Reinforcement Learning Loop**: Implement a PPO-based training process to update the orchestrator's policy based on workflow outcomes.
  - **Build Observability Dashboard**: Create a monitoring interface to track workflow health, error rates, and learning performance metrics.
  - Integrate with CI/CD for automated testing

## Logical Dependency Chain
- Foundation: Set up Docker Compose, Postgres, RabbitMQ, and MCP server
- Next: Implement orchestrator agent with DAG planning capabilities
- Then: Develop executor agents and task execution framework
- After: Add comprehensive testing, monitoring, and workflow visualization
- Always: Ensure each feature is atomic and can be built upon in future iterations

## Risks and Mitigations
- **Technical Challenges**: Ensuring reliable message delivery and agent state consistency. Mitigation: Use robust libraries (pika, redis-py), automated tests, and Docker health checks.
- **MVP Scope**: Risk of over-engineering. Mitigation: Focus on core agent communication and state management first.
- **RL Training Complexity**: Training the PPO model can be complex, with risks of unstable learning or poor convergence. Mitigation: Start with a simple reward function, log all state-action-reward tuples for offline analysis, establish a baseline performance metric, and version control the trained models.
- **Resource Constraints**: Docker resource usage and service startup order. Mitigation: Use health checks and clear documentation.

## Appendix
- See `project_logs/` for detailed experiment and architecture logs
- Example test scripts and usage instructions in `agents/testing_agent/`
- All endpoints and integration details documented in `mcp/` and logs