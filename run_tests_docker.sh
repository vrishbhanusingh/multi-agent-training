#!/bin/bash
# This script runs specific test types for the orchestrator-executor system
# using Docker Compose to ensure proper integration.

set -e

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Run specific tests for the orchestrator-executor system"
    echo ""
    echo "Options:"
    echo "  -u, --unit       Run unit tests only"
    echo "  -i, --integration Run integration tests only"
    echo "  -e, --e2e        Run end-to-end tests only"
    echo "  -a, --all        Run all tests (default)"
    echo "  -k, --keep       Keep containers running after tests"
    echo "  -h, --help       Display this help message"
}

# Default values
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_E2E=false
KEEP_RUNNING=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--unit)
            RUN_UNIT=true
            shift
            ;;
        -i|--integration)
            RUN_INTEGRATION=true
            shift
            ;;
        -e|--e2e)
            RUN_E2E=true
            shift
            ;;
        -a|--all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_E2E=true
            shift
            ;;
        -k|--keep)
            KEEP_RUNNING=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# If no test type is specified, run all tests
if [ "$RUN_UNIT" = false ] && [ "$RUN_INTEGRATION" = false ] && [ "$RUN_E2E" = false ]; then
    RUN_UNIT=true
    RUN_INTEGRATION=true
    RUN_E2E=true
fi

echo "==================================================================="
echo "🚀 Starting test environment using Docker Compose..."
echo "==================================================================="

# Stop any existing containers and remove them
docker-compose -f docker-compose.test.yml down -v

# Start all the services in detached mode
docker-compose -f docker-compose.test.yml up -d postgres rabbitmq orchestrator executor

echo "Waiting 30 seconds for services to fully start up..."
sleep 30

# Run unit tests if requested
if [ "$RUN_UNIT" = true ]; then
    echo "==================================================================="
    echo "▶️ Running Unit Tests"
    echo "==================================================================="
    docker-compose -f docker-compose.test.yml run --rm unit-tests
fi

# Run integration tests if requested
if [ "$RUN_INTEGRATION" = true ]; then
    echo "==================================================================="
    echo "▶️ Running Integration Tests"
    echo "==================================================================="
    docker-compose -f docker-compose.test.yml run --rm integration-tests
fi

# Run end-to-end tests if requested
if [ "$RUN_E2E" = true ]; then
    echo "==================================================================="
    echo "▶️ Running End-to-End Tests"
    echo "==================================================================="
    docker-compose -f docker-compose.test.yml run --rm e2e-tests
fi

echo "==================================================================="
echo "✅ All requested tests completed!"
echo "==================================================================="

# Shut down the environment if not keeping it running
if [ "$KEEP_RUNNING" = false ]; then
    echo "Stopping and removing all containers..."
    docker-compose -f docker-compose.test.yml down -v
else
    echo "Test environment is still running."
    echo "You can access the services at:"
    echo "  - Orchestrator API: http://localhost:8000"
    echo "  - RabbitMQ Management: http://localhost:15672"
    echo "  - PostgreSQL: localhost:5432"
    echo ""
    echo "To stop the environment later, run:"
    echo "  docker-compose -f docker-compose.test.yml down -v"
fi
