# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

[Neuron](https://gitea.zaks.io/isuttell/neuron) is a realtime chat application built with LangChain and LangGraph that provides an extensible platform for testing and experimenting with various LLM models and tool capabilities. 

## Architecture

Neuron consists of several key components:

- **Backend**: Python-based server using Quart for async HTTP and WebSocket support
- **Frontend**: React application with TypeScript, Redux, and Shadcn UI components
- **Database**: PostgreSQL with PGVector for vector storage
- **Knowledge Graph**: Neo4j for semantic data relationships
- **Cache**: Redis for pub/sub messaging and task scheduling
- **AI Integration**: LangChain and LangGraph for LLM workflows

The application uses a WebSocket-based event system for real-time communication between the client and server, with REST endpoints for resource management.

## Important Notes

- The project uses Vite for frontend development and building
- The backend is built with Python 3.11 and uses Poetry for dependency management
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
- CI/CD is handled by Gitea Actions, which run the lint and test commands automatically
- Always check the Gitea Actions status on pull requests before merging

For complete PR requirements and process, refer to @./PR_REQUIREMENTS.md
