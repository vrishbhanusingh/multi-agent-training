# Multi-Agent Experiment 1 Log

## Experiment Goal
Test a multi-agent system with three agents (A, B, C), each running in its own Docker container, communicating directly via RabbitMQ using a message bus pattern.

---

## 1. Project Structure

```
multi-agent-training/
│
├── mcp/                      # MCP server and core logic
├── agents/
│   ├── agent_a/              # Agent A: code, Dockerfile, config
│   ├── agent_b/              # Agent B: code, Dockerfile, config
│   └── agent_c/              # Agent C: code, Dockerfile, config
├── docker/                   # (Optional) Shared Docker resources
├── project_logs/             # Documentation and logs
├── docker-compose.yml        # Orchestrates all services
├── requirements.txt          # (For MCP server)
└── README.md
```

---

## 2. Agent Container Design
- Each agent lives in its own subfolder under `agents/` (e.g., `agents/agent_a/`).
- Each agent folder contains:
  - A Python script for the agent logic (e.g., `main.py`)
  - A dedicated `Dockerfile` with its own build instructions
  - (Optional) Config files or requirements.txt if agents have different dependencies

---

## 3. Agent Python Script
- On startup, each agent:
  - Connects to RabbitMQ (host: `rabbitmq`)
  - Declares its own queue and binds to the topic exchange
  - Consumes messages from its queue
  - Publishes messages to other agents or broadcasts to all
  - Logs all received and sent messages

---

## 4. Docker Compose Topology
- **Services:**
  - `rabbitmq` (shared)
  - `redis` (shared, if needed)
  - `mcp-server` (shared, if needed)
  - `agent_a` (builds from `agents/agent_a/Dockerfile`)
  - `agent_b` (builds from `agents/agent_b/Dockerfile`)
  - `agent_c` (builds from `agents/agent_c/Dockerfile`)
- **Networking:**
  - All containers are on the same Docker Compose network.
  - Agents connect to RabbitMQ using the service name `rabbitmq`.

---

## 5. Testing Scenarios
- **Direct Messaging:**
  - Agent A → Agent B
  - Agent B → Agent C
  - Agent C → Agent A
- **Broadcast:**
  - Any agent sends a broadcast; all agents receive it.

---

## 6. Success Criteria
- Each agent container starts, connects to RabbitMQ, and declares its queue.
- Agents can send and receive direct and broadcast messages.
- Each agent logs its received and sent messages.

---

## 7. Implementation Steps
1. Create agent folders: `agents/agent_a/`, `agents/agent_b/`, `agents/agent_c/`
2. Write agent logic in each folder (`main.py`)
3. Write a Dockerfile in each agent folder (custom instructions as needed)
4. Update docker-compose.yml to add each agent as a service, building from its folder
5. Build and run the stack with `docker-compose up --build`
6. Observe logs for inter-agent communication

---

## 8. Helpful Execution Notes
- **RabbitMQ Host:** Use `rabbitmq` as the hostname in agent scripts (Docker Compose networking).
- **Exchange/Queue Naming:**
  - Use a topic exchange (e.g., `agent_communication`).
  - Each agent's queue: `agent_agent_a`, `agent_agent_b`, `agent_agent_c`.
  - Routing keys: `agent.agent_a.message`, `agent.agent_b.message`, etc. for direct; `agent.broadcast` for broadcast.
- **Agent Logging:**
  - Print/log all sent and received messages with timestamps, sender, receiver, and content.
- **Testing:**
  - Use `docker-compose logs agent_a` (or b/c) to view each agent's output.
- **Extensibility:**
  - Add more agents by copying a folder and updating the Dockerfile/service name.
  - Parameterize agent behavior/config via environment variables or config files.
- **Troubleshooting:**
  - Ensure all containers are healthy (`docker-compose ps`).
  - Check RabbitMQ management UI at `localhost:15672` for queue/exchange status.

---

## 9. Optional Enhancements
- Add health checks for each agent container
- Add persistent logging (mount a volume for logs)
- Add agent configuration via environment variables
- Implement agent response/acknowledgment logic

---

## 10. Summary
This plan sets up a robust experiment for multi-agent communication using Docker, RabbitMQ, and Python, with each agent isolated in its own container and folder for maximum flexibility and clarity.
