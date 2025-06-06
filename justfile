# Neuron Project Commands
# Run `just` or `just --list` to see available commands

# Default command - shows help
default:
    @just --list

# ========== Frontend Commands ==========

# Install frontend dependencies
frontend-install:
    npm install

# Run frontend development server
frontend-dev:
    npm run dev

# Build frontend for production
frontend-build:
    npm run build

# Run frontend tests
frontend-test:
    npm test

# Run frontend tests with coverage
frontend-test-coverage:
    npm run test:coverage

# Run frontend tests in watch mode
frontend-test-watch:
    npm run test:watch

# Lint frontend code
frontend-lint:
    npm run lint

# Auto-fix frontend lint issues
frontend-lint-fix:
    npm run lint -- --fix

# ========== Backend Commands ==========

# Install backend dependencies
backend-install:
    poetry install

# Run backend server
backend-run:
    poetry run python -m neuron_server

# Run backend tests
backend-test:
    poetry run pytest src/neuron_server/

# Run backend tests with coverage
backend-test-coverage:
    poetry run pytest src/neuron_server/ --cov=src/neuron_server/ --cov-report=term

# Lint backend code
backend-lint:
    poetry run ruff check src/neuron_server/

# Auto-fix backend lint issues
backend-lint-fix:
    poetry run ruff check --fix src/neuron_server/

# ========== Docker Commands ==========

# Build all Docker images
docker-build:
    docker-compose build

# Start all services with Docker Compose
docker-up:
    docker-compose up -d

# Stop all services
docker-down:
    docker-compose down

# View Docker logs
docker-logs:
    docker-compose logs -f

# ========== Pre-commit Commands ==========

# Run pre-commit on all files
pre-commit-all:
    pre-commit run --all-files

# Run pre-commit on staged files
pre-commit:
    pre-commit run

# Install pre-commit hooks
pre-commit-install:
    pre-commit install

# ========== Workflow Commands ==========

# Lint Gitea workflow files
workflow-lint:
    actionlint .gitea/workflows/*.yml

# ========== Combined Commands ==========

# Install all dependencies
install: frontend-install backend-install pre-commit-install

# Run all linters
lint: frontend-lint backend-lint

# Auto-fix all lint issues
lint-fix: frontend-lint-fix backend-lint-fix

# Run all tests
test: frontend-test backend-test

# Run all tests with coverage
test-coverage: frontend-test-coverage backend-test-coverage

# Full CI check - runs all checks that would run in CI
ci-check: lint test frontend-build
    @echo "All CI checks passed!"

# Pre-PR check - ensures all requirements are met before creating a PR
pre-pr: lint-fix pre-commit-all ci-check
    @echo "✅ All pre-PR checks passed! Ready to create PR."

# ========== Development Commands ==========

# Start development environment (frontend and backend)
dev:
    #!/usr/bin/env bash
    echo "Starting backend server..."
    poetry run python -m neuron_server &
    BACKEND_PID=$!
    echo "Starting frontend dev server..."
    npm run dev &
    FRONTEND_PID=$!
    echo "Backend PID: $BACKEND_PID"
    echo "Frontend PID: $FRONTEND_PID"
    echo "Press Ctrl+C to stop both servers"
    wait

# Clean build artifacts
clean:
    rm -rf dist/
    rm -rf src/neuron_client/dist/
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name ".coverage" -delete
    find . -type d -name ".pytest_cache" -exec rm -rf {} +
    find . -type d -name ".ruff_cache" -exec rm -rf {} +

# Format code and run pre-commit hooks
format: lint-fix pre-commit