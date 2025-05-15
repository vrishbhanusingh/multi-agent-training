#!/bin/bash
# Script to run all executor agent tests

set -e

echo "Running executor agent unit tests..."
cd agents/executor_agent
python -m pytest tests/unit -v

echo "Running executor agent integration tests..."
python -m pytest tests/integration -v

echo "All tests completed successfully!"
