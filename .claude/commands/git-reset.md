Reset the repository to a clean state. Since this is potientially destructive make sure to backup any uncommited changes before you do:

```bash
# Save any uncommitted changes, switch to master and update
git stash push -u -m "Auto-stash before reset" && git checkout master && git fetch origin && git reset --hard origin/master

# Optional: Remove untracked files (use with caution)
# git clean -fd -n  # Dry run first to see what would be deleted
# git clean -fd     # Actually delete

# Show stash list in case you need to recover work
git stash list
```
