---
description: Save current session to continuum vault
---

# Save Session to Continuum Vault

Create a snapshot of the current session and save it to the continuum vault.

## What to do

1. **Import the continuum module**
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path.home()))
   from continuum import ContinuumRepo
   ```

2. **Ask user for optional description**
   - Prompt: "Session description (optional, press enter to skip):"
   - Use input() to get the description

3. **Create the snapshot**
   ```python
   continuum_path = Path.home() / '.continuum'
   workspace_path = Path.cwd()

   repo = ContinuumRepo(str(continuum_path))

   print("📸 Creating snapshot...")
   metadata = repo.create_snapshot(workspace_path, description)

   print(f"  ✓ Saved conversation")
   print(f"  ✓ Captured git state: {metadata['git']['branch'] or 'N/A'}")
   if metadata['git']['has_uncommitted']:
       print(f"  ✓ Stashed uncommitted files")
   if metadata['git']['has_unpushed']:
       print(f"  ✓ Pushed wip branch")
   print(f"  ✓ Host: {metadata['hostname']} ({metadata['kernel_version']})")
   ```

4. **Commit and push to continuum repo**
   ```python
   print("  ✓ Committing to continuum repo...")
   success = repo.commit_and_push_snapshot(
       metadata['session_id'],
       metadata['description']
   )

   if success:
       print("  ✓ Pushed to private repo")
       print()
       print("Sweet dreams! Resume with: ccc")
   else:
       print()
       print("⚠️  Warning: Failed to push to continuum repo")
       print("Session saved locally but not synced to remote")
   ```

5. **Exit Claude Code**
   - Use `sys.exit(0)` to cleanly exit after saving

## Important notes

- Run all code in a single Python execution using the Bash tool
- The continuum module is located at ~/continuum.py in the container
- Handle errors gracefully and inform the user
- Always show the session ID in the output so user can reference it later
