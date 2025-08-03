Create a task list and verify each item passes before creating a PR using the Gitea MCP. All tests, linters and formatters must succeed for the PR to be approved. Do not bypass any checks.

## Branch Preparation

- [ ] Fetch and rebase the latest changes from the master branch to avoid merge conflicts
- [ ] Ensure we're on a appropriately named branch off of master

## Quality Checks

### For Any Frontend Changes

- [ ] `npm run lint --fix` - Frontend linting errors
- [ ] `npm run build` - Frontend type errors
- [ ] `npm test` - Frontend tests

### For Any Backend Changes

- [ ] `poetry run ruff check src/neuron_server/ --fix` - Backend linting errors
- [ ] `poetry run ruff format src/neuron_server/` - Backend code formatting
- [ ] `poetry run pytest` - Backend tests

## Final Steps

- [ ] `pre-commit run --all-files` - pre-hooks
- [ ] Commit
- [ ] Push branch to remote repository
- [ ] Create PR using Gitea MCP
