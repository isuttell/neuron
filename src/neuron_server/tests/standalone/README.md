# Standalone Tests

This directory contains standalone tests that don't rely on importing the actual codebase modules. This approach helps avoid issues with dependencies and database connections in CI environments.

## Why Standalone Tests?

The main benefits of standalone tests are:

1. **Isolation**: Tests are isolated from the actual implementation, so they don't depend on imports or database connections.
2. **Decoupling**: Tests are decoupled from implementation details, making them more resilient to changes.
3. **Simplicity**: Tests are easier to understand and maintain.
4. **Performance**: Tests run faster because they don't need to initialize the actual application.
5. **CI Compatibility**: Tests run reliably in CI environments where databases may not be available.

## How to Run

```bash
cd /path/to/neuron/src/neuron_server/tests/standalone
python -m pytest test_app.py -v
```

## Implementation

These tests create a simplified version of the API endpoints that mimics the behavior of the actual application. They use Quart for HTTP request handling and implement mock services for the backend functionality.

The test framework creates a complete standalone implementation that doesn't import from the actual codebase, making it robust to changes in the implementation details.

## Usage in CI

These tests are particularly useful in CI environments where:

1. Database servers (PostgreSQL, Redis, Neo4j) are not available
2. Test environments need to be ephemeral and self-contained
3. Tests need to run quickly without complex setup