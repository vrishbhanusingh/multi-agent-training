#!/bin/bash
# This script runs all tests (unit, integration, and end-to-end) for the orchestrator-executor system
# using Docker Compose to ensure proper integration.

set -e

echo "==================================================================="
echo "🚀 Starting test environment using Docker Compose..."
echo "==================================================================="

# Stop any existing containers and remove them
docker-compose -f docker-compose.test.yml down -v

# Start all the services in detached mode
docker-compose -f docker-compose.test.yml up -d postgres rabbitmq orchestrator executor

echo "Waiting 30 seconds for services to fully start up..."
sleep 30

echo "==================================================================="
echo "▶️ Running Unit Tests"
echo "==================================================================="
docker-compose -f docker-compose.test.yml run --rm unit-tests

echo "==================================================================="
echo "▶️ Running Integration Tests"
echo "==================================================================="
docker-compose -f docker-compose.test.yml run --rm integration-tests

echo "==================================================================="
echo "▶️ Running End-to-End Tests"
echo "==================================================================="
docker-compose -f docker-compose.test.yml run --rm e2e-tests

echo "==================================================================="
echo "✅ All tests completed!"
echo "==================================================================="

# Ask if the user wants to keep the environment running
read -p "Do you want to keep the test environment running? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping and removing all containers..."
    docker-compose -f docker-compose.test.yml down -v
fi
