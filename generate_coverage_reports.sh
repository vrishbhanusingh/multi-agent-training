#!/bin/bash
# This script generates test coverage reports for the orchestrator-executor system

set -e

# Create directories for coverage reports
mkdir -p coverage_reports/unit coverage_reports/integration

echo "==================================================================="
echo "🚀 Starting services for coverage testing..."
echo "==================================================================="

# Start all the services in detached mode if needed
if [ "$1" = "--start-services" ]; then
    docker-compose -f docker-compose.test.yml up -d postgres rabbitmq orchestrator executor
    echo "Waiting 15 seconds for services to fully start up..."
    sleep 15
fi

echo "==================================================================="
echo "📊 Generating Unit Test Coverage"
echo "==================================================================="
docker-compose -f docker-compose.test.yml run --rm unit-tests python -m pytest agents/executor_agent/tests/unit \
    --cov=agents.executor_agent --cov-report=html:./coverage_reports/unit/ --cov-report=term

echo "==================================================================="
echo "📊 Generating Integration Test Coverage"
echo "==================================================================="
docker-compose -f docker-compose.test.yml run --rm integration-tests python -m pytest agents/executor_agent/tests/integration \
    --cov=agents.executor_agent --cov-report=html:./coverage_reports/integration/ --cov-report=term

echo "==================================================================="
echo "✅ Coverage reports generated!"
echo "==================================================================="
echo "Unit test coverage: ./coverage_reports/unit/index.html"
echo "Integration test coverage: ./coverage_reports/integration/index.html"

# Clean up if we started the services
if [ "$1" = "--start-services" ]; then
    if [ "$2" != "--keep-running" ]; then
        echo "Stopping and removing services..."
        docker-compose -f docker-compose.test.yml down
    else
        echo "Services are still running. Use 'docker-compose -f docker-compose.test.yml down' to stop them."
    fi
fi
