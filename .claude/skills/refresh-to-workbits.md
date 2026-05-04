---
name: refresh-to-workbits
description: Push local Claude config (skills, settings) to GitHub workBits repo
---

# Refresh to workBits

Push your local Claude Code configuration to the GitHub workBits repository.

## What this does

Syncs from local to GitHub:
- `~/.claude/skills/` → `workBits/.claude/skills/`
- `~/.claude/settings.json` → `workBits/.claude/settings.json`

## Steps

1. **Verify workBits repo exists**
   ```bash
   ls ~/repos/workBits
   ```
   If not found, tell user to clone it first.

2. **Check for uncommitted changes in workBits**
   ```bash
   cd ~/repos/workBits && git status --short
   ```
   If there are changes, ask user what to do (commit, stash, or abort).

3. **Copy skills directory**
   ```bash
   rsync -av --delete ~/.claude/skills/ ~/repos/workBits/.claude/skills/
   ```

4. **Copy settings.json if it exists**
   ```bash
   if [[ -f ~/.claude/settings.json ]]; then
       cp ~/.claude/settings.json ~/repos/workBits/.claude/settings.json
       echo "✅ Copied settings.json"
   else
       echo "⚠️  No settings.json found"
   fi
   ```

5. **Commit and push**
   ```bash
   cd ~/repos/workBits
   git add .claude/
   git status --short
   ```
   
   If there are staged changes:
   ```bash
   git commit -m "Sync Claude config from $(hostname) - $(date +%Y-%m-%d)"
   git push origin main
   ```
   
   If no changes, report "Already up to date".

6. **Show summary**
   Count synced files:
   ```bash
   find ~/repos/workBits/.claude/skills -type f -name "*.md" | wc -l
   ```
   
   Report what was synced.
