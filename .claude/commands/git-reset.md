Reset the repository to a clean state ready for another task. Since this is potientially destructive make sure to backup any uncommited changes before you do:

```bash
# Save any uncommitted changes, switch to master and reset
git stash push -u -m "Auto-stash before reset" && git checkout master && git fetch origin && git reset --hard origin/master
```
