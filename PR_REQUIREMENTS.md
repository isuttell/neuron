# Pull Request Requirements

This document outlines the requirements for creating pull requests for the Neuron project.

## Branch Naming

Use concise, descriptive branch names that indicate the type of change (e.g., `fix-transcript-api`, `feature-webhooks`).

## Pull Request Description

PR descriptions must include:

1. **Summary**: Concise high-level description (2-3 sentences)
2. **Impact Areas**: List of components/systems affected
3. **Test Plan**: How the changes were tested

## Pre-submission Checklist

Before submitting a PR, verify:

### For Backend Changes (Python)
- [ ] Runs without errors: `poetry run python -m neuron_server`
- [ ] Tests pass: `poetry run pytest src/neuron_server/`
- [ ] Linting passes: `poetry run ruff check --fix src/neuron_server/`
- [ ] Test coverage: `poetry run pytest src/neuron_server/ --cov=src/neuron_server/ --cov-report=term`

### For Frontend Changes (TypeScript/React)
- [ ] Builds successfully: `npm run build`
- [ ] Tests pass: `npm test`
- [ ] Linting passes: `npm run lint`
- [ ] Test coverage: `npm run test:coverage`

## Pull Request Process

1. Create a branch from `master` using a concise, descriptive name
2. Make changes adhering to code quality guidelines
3. Run pre-submission checks locally
4. Create PR using Gitea MCP tools
