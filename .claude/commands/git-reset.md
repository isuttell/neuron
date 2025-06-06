# Git Reset Command

Reset the repository to a clean state before starting a new task:

```bash
# Save any uncommitted changes
git stash push -u -m "Auto-stash before reset"

# Switch to main and update
git checkout main
git fetch origin
git reset --hard origin/main

# Optional: Remove untracked files (use with caution)
# git clean -fd -n  # Dry run first to see what would be deleted
# git clean -fd     # Actually delete

# Show stash list in case you need to recover work
git stash list
```

This approach:

- Stashes any uncommitted work (including untracked files with -u)
- Safely resets to the latest main branch
- Preserves your work in the stash if needed
- Gives you control over cleaning untracked files
