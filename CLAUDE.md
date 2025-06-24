# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Information

- **Repository Name**: isuttell/neuron
- **Repository URL**: https://gitea.zaks.io/isuttell/neuron
- **Git Remote Server**: Gitea (self-hosted at gitea.zaks.io)

Note: This local directory may be named differently (e.g., neuron-02), but the actual repository name is "isuttell/neuron".

## Project Overview

Neuron is a realtime chat application built with LangChain and LangGraph that provides an extensible platform for testing and experimenting with various LLM models and tool capabilities.

## Environment Information

### Production Environment
- Hosted on Lapetus homelab server (neuron.zaks.io)
- Contains the production database with all configured AI providers
- Accessible via `mcp__postgres-neuron__*` MCP tools

### Local Development Environment
- Docker-based setup on local machine using docker compose
- Has separate database instance for local development
- Accessible via `mcp__postgres-localhost__*` MCP tools (connects to localhost:5432)

### MCP Tool Usage
- `mcp__postgres-neuron__*` tools connect to the production database on Lapetus
- `mcp__postgres-localhost__*` tools connect to the local Docker database

## Architecture

Neuron consists of several key components:

- **Backend**: Python-based server using Quart for async HTTP and WebSocket support
- **Frontend**: React application with TypeScript, Redux, and Shadcn UI components
- **Database**: PostgreSQL with PGVector for vector storage
- **Knowledge Graph**: Neo4j for semantic data relationships
- **Cache**: Redis for pub/sub messaging and task scheduling
- **AI Integration**: LangChain and LangGraph for LLM workflows

The application uses a WebSocket-based event system for real-time communication between the client and server, with REST endpoints for resource management.

### Client Serving Options

The application supports two deployment modes:

1. **Separate Containers** (recommended for production): Client is served by nginx in a dedicated container
2. **Single Container** (for development/simple deployments): Python server can optionally serve client files

To enable client serving from the Python server, set the environment variable:
```bash
SERVE_CLIENT=true
```

When this is enabled, you can run just the server container without the separate client container.

## Important Notes

- The project uses Vite for frontend development and building
- The backend is built with Python 3.12 and uses Poetry for dependency management
- Neo4j is used for knowledge graph functionality
- Redis is used for caching and pub/sub messaging
- The system supports various LLM providers including OpenAI, Anthropic, Cohere, and Google

## Key Development Commands

### Frontend Development

```bash
# Install frontend dependencies
npm install

# Start frontend development server
npm run dev

# Run frontend tests
npm test

# Run frontend tests with coverage
npm run test:coverage

# Run continuous test watching
npm test:watch

# Lint frontend code
npm run lint

# Build frontend for production
npm run build
```

### Backend Development

```bash
# Install Python dependencies using Poetry
poetry install

# Start backend server
poetry run python -m neuron_server

# Run backend tests
poetry run pytest src/neuron_server/

# Run backend tests with coverage report
poetry run pytest src/neuron_server/ --cov=src/neuron_server/ --cov-report=term

# Lint and fix backend code
poetry run ruff check --fix src/neuron_server/
```

## Code Style Guidelines

### Frontend Code Style

- Use TypeScript for all frontend code
- Use functional and declarative programming patterns; avoid classes
- Use Tailwind CSS for styling; avoid inline styles
- Use Shadcn UI components for consistency; prefer reusable components
- Use Redux for state management; favor slice reducers and avoid storing derived state
- Use `camelCase` for variable names
- Do not modify shadcn/ui components in src/neuron_client/src/components/ui

### Backend Code Style

- Write concise, technical Python code
- Use Pydantic for data validation; ensure all models are strongly typed
- Use SQLAlchemy ORM for database interactions; avoid raw SQL unless necessary
- Use Quart for the web server and WebSocket handling; prioritize async operations
- Use `snake_case` for variable names
- Include type hints in all functions and class methods
- Use docstrings for all exported functions and classes
- Max line length is 88 characters and tabs count for 4 spaces

## Testing Requirements

### Frontend Testing

- Write unit tests for components using Jest and React Testing Library
- Mock network requests in tests

### Backend Testing

- Include tests for controllers, tools, and database models
- Use mocking for database and network operations to ensure isolation of tests

## Gitea Integration

This project uses a self-hosted Gitea instance at https://gitea.zaks.io for version control and CI/CD. When working with this repository:

- Always use the Gitea MCP tools installed for this project to interact with the repository
- Always specify the correct repository owner and name (isuttell/neuron) when using Gitea commands
- Use the `tea` CLI tool for Gitea operations instead of `gh` - most useful command is `tea pr --repo isuttell/neuron --comments <PR_NUMBER>` which gets comments from a PR
- CI/CD is handled by Gitea Actions, which run the lint and test commands automatically
- Always check the Gitea Actions status on pull requests before merging
- Always run lint and formatting commands to automatically fix issues before making manual code changes:
  - Frontend: `npm run lint -- --fix`
  - Backend: `poetry run ruff check --fix src/neuron_server/`
- Always use the pre-commit tool to verify commits will pass checks before actually committing:
  ```bash
  # Run pre-commit on all files
  pre-commit run --all-files

  # Run pre-commit on staged files
  pre-commit run
  ```

## Pull Request Requirements

**IMPORTANT**: Before creating any pull request, you MUST ensure all tests, lint checks, formatting, and type checks are passing. The CI/CD pipeline will run these checks automatically, and PRs with failing checks cannot be merged.

### Required Checks Before PR Submission

#### Frontend Checks
All of these commands must pass without errors:
```bash
# 1. Lint check (as run in CI)
npm run lint

# 2. Test suite (as run in CI)
npm test

# 3. Build verification (as run in CI)
npm run build
```

#### Backend Checks
All of these commands must pass without errors:
```bash
# 1. Lint check with Ruff (as run in CI)
poetry run ruff check src/neuron_server/

# 2. Test suite with coverage (as run in CI)
poetry run pytest src/neuron_server/ --cov
```

#### Workflow File Checks (if modifying .gitea/workflows)
```bash
# Lint workflow files
actionlint .gitea/workflows/*.yml
```

### Auto-fixing Issues
If any checks fail, try auto-fixing first:
- Frontend: `npm run lint -- --fix`
- Backend: `poetry run ruff check --fix src/neuron_server/`

### Verification Process
1. Run all applicable checks based on what you've modified
2. Fix any issues that arise
3. Re-run checks to ensure they pass
4. Only then create the pull request

For complete PR requirements and process, refer to @PR_REQUIREMENTS.md

## Monitoring and Logs

### Querying Preprod Logs with Loki

The preprod environment uses Loki for log aggregation. To query Neuron logs:

1. Use `mcp__loki__get_loki_label_values(label="container")` to find Neuron containers (they start with "neuron-")
2. Query logs with `mcp__loki__query_loki(query='{container="neuron-neuron_server-1"}', limit=50)`
