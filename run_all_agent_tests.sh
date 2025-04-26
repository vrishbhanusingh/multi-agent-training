#!/bin/bash
set -e

echo "Running tests for agent_a..."
docker compose exec agent_a pytest

echo "Running tests for agent_b..."
docker compose exec agent_b pytest

echo "Running tests for agent_c..."
docker compose exec agent_c pytest

echo "All agent tests completed." 