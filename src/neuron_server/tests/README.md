# Neuron Server Tests

This directory contains tests for the Neuron server components.

## Testing Approach

There are two main approaches to testing in this project:

1. **Standard Tests**: These tests directly import and test the actual codebase components. They use mocks to avoid database connections and external dependencies. Examples include:
   - `test_scheduler_controller.py`

2. **Standalone Tests**: These tests create a standalone version of the component being tested without importing the actual implementation. This approach is useful when dealing with complex dependencies or import cycles. Examples include:
   - `standalone/test_app.py` (standalone implementation of scheduler API endpoints)

## Database Mocking

Tests in this project need to avoid making real database connections, especially in CI environments where databases are not available. We use several approaches to mock database access:

1. **SQLAlchemy Session Mocking**: We mock the SQLAlchemy session to avoid actual database connections.
2. **API Module Mocking**: We mock the API module to avoid dependencies that might require database access.
3. **Model Mocking**: We mock the model classes to avoid database access in model methods.

## Running Tests

To run all tests:

```bash
poetry run pytest src/neuron_server/tests/
```

To run a specific test file:

```bash
poetry run pytest src/neuron_server/tests/test_scheduler_controller.py
```

To run with verbose output:

```bash
poetry run pytest src/neuron_server/tests/test_scheduler_controller.py -v
```

## Standalone Tests

For tests that are difficult to run due to complex dependencies, we've created standalone versions that don't import the actual implementation. These tests are in the `standalone` directory.

To run standalone tests:

```bash
poetry run pytest src/neuron_server/tests/standalone/
```

## Testing in CI Environment

In CI environments, there are no database servers available. All database connections must be properly mocked. The conftest.py file includes fixtures to mock database connections for all tests.

## Adding New Tests

When adding new tests:

1. Use dependency injection and mocking to avoid actual database connections
2. Add necessary fixtures to mock dependencies
3. If you encounter circular imports or complex dependencies, consider creating a standalone test
4. Ensure tests run in CI environments without database access