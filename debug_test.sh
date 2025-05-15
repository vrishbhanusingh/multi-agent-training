#!/bin/bash
# Run specific tests in debug mode

set -e

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Run specific tests with debug options"
    echo ""
    echo "Options:"
    echo "  -f, --file PATH      Test file to run"
    echo "  -t, --test NAME      Specific test function to run"
    echo "  -m, --module MODULE  Test module to run (unit, integration, e2e)"
    echo "  -s, --show-output    Show print statements (adds -s flag to pytest)"
    echo "  -p, --pdb            Enable Python debugger on failures"
    echo "  -v, --verbose        Enable verbose output"
    echo "  -h, --help           Display this help message"
}

# Default values
TEST_FILE=""
TEST_NAME=""
MODULE="unit"
SHOW_OUTPUT=""
PDB=""
VERBOSE="-v"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            TEST_FILE="$2"
            shift
            shift
            ;;
        -t|--test)
            TEST_NAME="$2"
            shift
            shift
            ;;
        -m|--module)
            MODULE="$2"
            shift
            shift
            ;;
        -s|--show-output)
            SHOW_OUTPUT="-s"
            shift
            ;;
        -p|--pdb)
            PDB="--pdb"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-vvv"
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

# Validate module
if [[ "$MODULE" != "unit" && "$MODULE" != "integration" && "$MODULE" != "e2e" ]]; then
    echo "Error: Module must be one of: unit, integration, e2e"
    exit 1
fi

# Construct the test command
case "$MODULE" in
    "unit")
        SERVICE="unit-tests"
        TEST_PATH="agents/executor_agent/tests/unit"
        ;;
    "integration")
        SERVICE="integration-tests"
        TEST_PATH="agents/executor_agent/tests/integration"
        ;;
    "e2e")
        SERVICE="e2e-tests"
        # For e2e, we use the specific e2e test file directly
        TEST_PATH="agents/executor_agent/tests/e2e_test.py"
        ;;
esac

# Add test file if specified
if [[ -n "$TEST_FILE" ]]; then
    TEST_PATH="${TEST_PATH}/${TEST_FILE}"
    
    # If test name is also specified, add it
    if [[ -n "$TEST_NAME" ]]; then
        TEST_PATH="${TEST_PATH}::${TEST_NAME}"
    fi
fi

echo "==================================================================="
echo "🐞 Running tests in debug mode"
echo "==================================================================="
echo "Module:   ${MODULE}"
echo "Path:     ${TEST_PATH}"
echo "Options:  ${SHOW_OUTPUT} ${PDB} ${VERBOSE}"
echo "==================================================================="

# If e2e test, run directly with relevant args
if [[ "$MODULE" == "e2e" ]]; then
    docker-compose -f docker-compose.test.yml run --rm e2e-tests python "${TEST_PATH}" --orchestrator-url http://orchestrator:8000 --username executor --password executor_password
else
    # Run the test with the specified options
    docker-compose -f docker-compose.test.yml run --rm "${SERVICE}" python -m pytest "${TEST_PATH}" ${SHOW_OUTPUT} ${PDB} ${VERBOSE}
fi
