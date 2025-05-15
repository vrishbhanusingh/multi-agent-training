#!/bin/bash
# Simple test runner script

# Print current working directory
echo "Current directory: $(pwd)"

# Try to determine python command
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found"
    exit 1
fi

echo "Using Python: $($PYTHON_CMD --version)"

# Install pytest if needed
echo "Installing pytest and pytest-asyncio..."
$PYTHON_CMD -m pip install pytest pytest-asyncio || {
    echo "Failed to install pytest. Continuing anyway in case it's already installed."
}

# Set PYTHONPATH to include the project root
export PYTHONPATH=$(pwd)
echo "PYTHONPATH set to: $PYTHONPATH"

# Run tests
echo "Running unit tests..."
$PYTHON_CMD -c "import sys; print(sys.path)" # Debug
$PYTHON_CMD -m pytest agents/executor_agent/tests/unit -v

echo "Tests completed"
