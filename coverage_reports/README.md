# Test Coverage Report

This directory contains the test coverage reports generated during test runs.
Reports are in HTML format and can be viewed in a browser.

## How to Generate Reports

To generate a coverage report, run tests with the coverage option:

```bash
# Run tests with coverage
docker-compose -f docker-compose.test.yml run --rm unit-tests python -m pytest agents/executor_agent/tests/unit --cov=agents.executor_agent --cov-report=html:./coverage_reports/unit/

# For integration tests
docker-compose -f docker-compose.test.yml run --rm integration-tests python -m pytest agents/executor_agent/tests/integration --cov=agents.executor_agent --cov-report=html:./coverage_reports/integration/
```

## Viewing Reports

After generating reports, open the index.html file in your browser from the appropriate coverage directory.
