---
name: refresh-from-workbits
description: Pull Claude config (skills, settings) from GitHub workBits repo
---

# Refresh from workBits

Pull your Claude Code configuration from the GitHub workBits repository.

## What this does

Syncs from GitHub to local:
- `workBits/.claude/skills/` → `~/.claude/skills/`
- `workBits/.claude/settings.json` → `~/.claude/settings.json`

## Steps

1. **Verify workBits repo exists**
   ```bash
   ls ~/repos/workBits
   ```
   If not found, tell user to clone it first.

2. **Pull latest from GitHub**
   ```bash
   cd ~/repos/workBits
   git pull origin main
   ```

3. **Check for local uncommitted changes in ~/.claude**
   ```bash
   cd ~/.claude
   git status --short 2>/dev/null || echo "(~/.claude is not a git repo - OK)"
   ```
   If there are uncommitted changes to skills, warn user they'll be overwritten.

4. **Copy skills directory**
   ```bash
   mkdir -p ~/.claude/skills
   rsync -av --delete ~/repos/workBits/.claude/skills/ ~/.claude/skills/
   ```

5. **Copy settings.json if it exists**
   ```bash
   if [[ -f ~/repos/workBits/.claude/settings.json ]]; then
       cp ~/repos/workBits/.claude/settings.json ~/.claude/settings.json
       echo "✅ Copied settings.json"
   else
       echo "⚠️  No settings.json in workBits"
   fi
   ```

6. **Show summary**
   Count synced files:
   ```bash
   find ~/.claude/skills -type f -name "*.md" | wc -l
   ```
   
   Report what was synced and remind user they need to restart Claude Code or start a new session to load the updated skills.
