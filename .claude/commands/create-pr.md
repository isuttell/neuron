Create a task list and verify each item passes before creating a PR using the Gitea MCP:

## Branch Preparation

- [ ] Pull latest changes from main branch to avoid merge conflicts
- [ ] Ensure we're on a appropriately named branch off ofmain
- [ ] Resolve any merge conflicts if they exist

## Quality Checks

- [ ] `npm run lint --fix` - Frontend linting errors
- [ ] `npx tsc --noEmit .` - Frontend type errors
- [ ] `npm test` - Frontend tests
- [ ] `poetry run ruff check .  --fix` - Backend linting errors
- [ ] `poetry run ruff format . --fix` - Backend code formatting
- [ ] `poetry run pytest` - Backend tests
- [ ] `pre-commit run --all-files` - pre-hooks

## Final Steps

- [ ] Push branch to remote repository
- [ ] Create PR using Gitea MCP

ALL checks must pass or the PR will be REJECTED.
