# Testing the Orchestrator-Executor System

This document provides instructions for testing the orchestrator-executor system with various levels of tests.

## Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose
- Poetry or pip for dependency management

## Quick Start with Docker (Recommended)

The easiest way to run all tests is using the provided Docker scripts that handle all the environment setup:

```bash
# Run all tests (unit, integration, and end-to-end)
./run_tests_docker.sh --all

# Run only specific tests
./run_tests_docker.sh --unit          # Run only unit tests
./run_tests_docker.sh --integration   # Run only integration tests
./run_tests_docker.sh --e2e           # Run only end-to-end tests

# Keep the test environment running after tests complete
./run_tests_docker.sh --all --keep
```

## 1. Unit Testing

Unit tests verify the individual components of the system in isolation using mocks and stubs.

### Running Unit Tests Directly

```bash
# Navigate to the executor agent directory
cd agents/executor_agent

# Run unit tests only
python -m pytest tests/unit -v
```

### Running Unit Tests with Docker

```bash
# Run only unit tests in Docker
docker-compose -f docker-compose.test.yml run --rm unit-tests
```

These tests verify:
- Task handler protocol implementation
- Task poller interface implementation
- Executor agent functionality

## 2. Integration Testing

Integration tests verify the interaction between multiple components within the executor agent.

### Running Integration Tests Directly

```bash
# Navigate to the executor agent directory
cd agents/executor_agent

# Run integration tests
python -m pytest tests/integration -v
```

### Running Integration Tests with Docker

```bash
# Run only integration tests in Docker
docker-compose -f docker-compose.test.yml run --rm integration-tests
```

These tests verify:
- Complete task execution flow
- Handling of multiple task types
- Error handling during task execution

## 3. End-to-End Testing

End-to-end tests verify the complete system with orchestrator and executor agents running together.

### Running End-to-End Tests with Docker

```bash
# Method 1: Using the specific E2E test service
docker-compose -f docker-compose.test.yml run --rm e2e-tests

# Method 2: Manual approach
# Start the test environment
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be ready (approximately 30 seconds)
sleep 30

# Run the end-to-end test
python agents/executor_agent/tests/e2e_test.py --orchestrator-url http://localhost:8000 --username executor --password executor_password

# Shutdown the test environment
docker-compose -f docker-compose.test.yml down
```

### What the E2E Test Verifies

The end-to-end test:
1. Creates a test DAG with 3 tasks (echo → transform → echo)
2. Submits the DAG to the orchestrator
3. Monitors the execution until completion
4. Verifies each task's results

## 4. Running All Tests

For convenience, you can run all tests using the provided scripts:

### Using Docker (Recommended)

```bash
# Run all tests with a single command
./run_all_tests_docker.sh

# Or use the more flexible script with options
./run_tests_docker.sh --all
```

### Using Direct Python Execution

```bash
# Make the script executable
chmod +x run_executor_tests.sh

# Run all tests
./run_executor_tests.sh
```

## 5. Manual Testing

You can also manually test the system by:

1. Starting the services:
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

2. Submit a test query via the API:
   ```bash
   curl -X POST http://localhost:8000/api/queries \
     -H "Content-Type: application/json" \
     -d '{"query": "Process and transform this text to uppercase: hello world", "parameters": {}}'
   ```

3. Monitor the execution in the logs:
   ```bash
   docker-compose -f docker-compose.test.yml logs -f orchestrator executor
   ```

4. Check the results via the API:
   ```bash
   # Replace with your actual query ID from step 2
   curl http://localhost:8000/api/queries/YOUR_QUERY_ID
   ```

## Troubleshooting

### Common Issues and Solutions

#### Test Container Fails to Start

If the test containers fail to start, check:

```bash
# Check the container logs
docker-compose -f docker-compose.test.yml logs unit-tests
docker-compose -f docker-compose.test.yml logs integration-tests
docker-compose -f docker-compose.test.yml logs e2e-tests
```

#### Services Not Running Properly

If services aren't working correctly:

1. Check the logs for both services:
   ```bash
   docker-compose -f docker-compose.test.yml logs orchestrator
   docker-compose -f docker-compose.test.yml logs executor
   ```

2. Verify connectivity between services:
   ```bash
   docker exec -it multi-agent-training-executor-1 curl -v orchestrator:8000/health
   ```

3. Inspect the database state:
   ```bash
   docker exec -it multi-agent-training-postgres-1 psql -U testuser -d orchestrator_test -c "SELECT * FROM tasks;"
   ```

4. Verify RabbitMQ connections:
   ```bash
   docker exec -it multi-agent-training-rabbitmq-1 rabbitmqctl list_connections
   ```

### Debugging Tests

#### Using Interactive Mode

You can run tests in interactive mode to debug failures:

```bash
# Run unit tests with -s flag to see print statements
docker-compose -f docker-compose.test.yml run --rm unit-tests python -m pytest agents/executor_agent/tests/unit -v -s

# Run a specific test file
docker-compose -f docker-compose.test.yml run --rm unit-tests python -m pytest agents/executor_agent/tests/unit/test_executor_agent.py -v

# Run a specific test function
docker-compose -f docker-compose.test.yml run --rm unit-tests python -m pytest agents/executor_agent/tests/unit/test_executor_agent.py::TestExecutorAgent::test_register_handler -v
```

#### Entering the Container Shell

For more complex debugging, you can enter the test container shell:

```bash
# Start a shell in the test container
docker-compose -f docker-compose.test.yml run --rm unit-tests /bin/bash

# From inside the container, you can run tests manually
python -m pytest agents/executor_agent/tests/unit -v
```

### Environment Inspection

To inspect the running environment:

```bash
# List all running services
docker-compose -f docker-compose.test.yml ps

# Check RabbitMQ management interface
echo "RabbitMQ Management UI available at: http://localhost:15672 (guest/guest)"

# View real-time logs
docker-compose -f docker-compose.test.yml logs -f
```

## Code Coverage Analysis

You can generate code coverage reports to see how well your tests cover the code:

```bash
# Generate coverage reports for unit and integration tests
./generate_coverage_reports.sh

# If services are not running yet, use --start-services
./generate_coverage_reports.sh --start-services

# Keep services running after generating reports
./generate_coverage_reports.sh --start-services --keep-running
```

Coverage reports will be generated in HTML format in the `coverage_reports` directory:
- Unit test coverage: `./coverage_reports/unit/index.html`
- Integration test coverage: `./coverage_reports/integration/index.html`

## Advanced Debugging

For more complex debugging scenarios, use the debug test script:

```bash
# Debug a specific test file
./debug_test.sh --file test_executor_agent.py --module unit

# Debug a specific test function
./debug_test.sh --file test_executor_agent.py --test TestExecutorAgent::test_register_handler --module unit

# Show print statements
./debug_test.sh --file test_task_handler.py --module unit --show-output

# Use Python debugger for interactive debugging
./debug_test.sh --file test_executor_integration.py --module integration --pdb

# Run E2E tests in debug mode
./debug_test.sh --module e2e
```
