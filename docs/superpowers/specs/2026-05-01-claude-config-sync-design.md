# Claude Code Configuration Sync Design

**Date:** 2026-05-01  
**Purpose:** Sync Claude Code configuration (skills, settings) between two laptops using workBits GitHub repo as central storage

## Overview

Create a system to keep Claude Code configuration synchronized across multiple machines using the existing `jluhrsen/workBits` GitHub repository as the source of truth. Two bash-based skills will handle bidirectional sync with secret detection and intelligent first-sync merging.

## Goals

- Keep `~/.claude/skills/` and `~/.claude/settings.json` in sync across laptops
- Use GitHub (workBits repo) as central storage
- Detect and prevent secrets from being committed
- Handle first-time sync intelligently (merge, don't overwrite)
- Simple, transparent bash implementation

## Non-Goals

- Syncing project-specific state (`~/.claude/projects/`)
- Syncing cache, history, or session data
- Automatic background syncing (manual invocation only)
- Resolving complex merge conflicts automatically

## Architecture

### Repository Structure

```
~/repos/workBits/
├── .claude/
│   ├── skills/
│   │   ├── check-branch-sync.md
│   │   ├── refresh-to-workbits.md      (new, syncs itself!)
│   │   ├── refresh-from-workbits.md    (new, syncs itself!)
│   │   ├── ci-prow-navigation/
│   │   └── jira/
│   ├── settings.json                    (synced)
│   ├── settings.local.json              (existing, NOT synced, gitignored)
│   └── README.md                         (new, explains the sync system)
├── .gitignore                            (add .claude/settings.local.json)
└── (other workBits content...)
```

### What Gets Synced

**Included:**
- `~/.claude/skills/` ↔ `workBits/.claude/skills/` (all skills, including subdirectories)
- `~/.claude/settings.json` ↔ `workBits/.claude/settings.json`

**Excluded:**
- Project-specific state (`~/.claude/projects/`)
- History, sessions, cache files
- `settings.local.json` (machine-specific overrides)
- Backups, debug files

### Data Flow

```
Laptop A                    GitHub                     Laptop B
~/.claude/     ←--pull--→  workBits/.claude/  ←--pull--→  ~/.claude/
    ↓                          ↑                             ↓
    |                          |                             |
 [push] → scan secrets → [commit & push]              [first sync merge]
```

## Components

### 1. Skill: `refresh-to-workbits`

**Purpose:** Push local Claude config to GitHub

**Location:** `~/.claude/skills/refresh-to-workbits.md`

**Process:**
1. Verify prerequisites:
   - Check workBits repo exists at `~/repos/workBits/`
   - If missing: offer to clone from GitHub
2. Check for uncommitted changes in workBits:
   - Run `git status` in workBits
   - If dirty: ask user to commit/stash/cancel
3. Copy local files to workBits staging:
   - `rsync -a --delete ~/.claude/skills/ ~/repos/workBits/.claude/skills/`
   - `cp ~/.claude/settings.json ~/repos/workBits/.claude/settings.json`
   - Note: rsync --delete ensures workBits matches local (removes deleted skills)
4. Secret detection with Gitleaks:
   - Check if gitleaks installed: `command -v gitleaks`
   - If not installed: offer to install, fallback to proceeding with warning
   - Run: `gitleaks detect --source .claude/ --verbose --no-git`
   - If secrets detected: show findings, ask "Review and fix before pushing. Continue anyway? Y/n"
5. Git commit and push:
   - `cd ~/repos/workBits`
   - `git add .claude/skills/ .claude/settings.json .claude/README.md`
   - Commit: `git commit -m "Sync Claude config from $(hostname) - $(date +%Y-%m-%d)"`
   - `git push origin main`
6. Report status: "✅ Pushed X skills and settings.json to workBits"

**Error Handling:**
- Repo doesn't exist → offer to clone
- Uncommitted changes → ask user to handle
- Network/push fails → show error, exit gracefully
- Gitleaks not installed → warn and proceed (user's choice)
- Permission errors → show error with needed permissions

### 2. Skill: `refresh-from-workbits`

**Purpose:** Pull latest Claude config from GitHub

**Location:** `~/.claude/skills/refresh-from-workbits.md`

**Process:**
1. Verify workBits repo exists
2. Pull latest from GitHub:
   - `cd ~/repos/workBits && git pull`
3. Ask: "First sync on this machine? (will merge, not overwrite) Y/n"
4. **If first sync (merge mode):**
   - For each file in `workBits/.claude/skills/` and `settings.json`:
     - If doesn't exist locally: copy to `~/.claude/`
     - If exists locally: compare modification timestamps
       - `stat -c %Y file` (Linux) or `stat -f %m file` (macOS)
       - Keep whichever version is newer
   - For local-only files in `~/.claude/skills/`: keep them (don't delete)
   - Show summary: "Merged: copied X files, kept Y local files (newer), skipped Z files (local newer)"
   - Suggest: "Run /refresh-to-workbits to push merged result to GitHub"
5. **If regular sync (timestamp mode):**
   - For each file in `workBits/.claude/`:
     - Compare timestamp with local version
     - If GitHub version newer: copy to `~/.claude/`
     - If local version newer: skip and report
   - Show: "Updated X files, skipped Y files (local newer)"
6. Report final status

**Safety Features:**
- Before overwriting local file: show "Overwriting: skills/foo.md (GitHub newer by 2 days)"
- Optional backup to `~/.claude/backups/` before first sync (ask user)

**Error Handling:**
- Repo doesn't exist → error and exit
- Git pull fails → show error, suggest manual resolution
- Network down → exit gracefully
- Permission errors → show error

### 3. Secret Detection (Gitleaks)

**Tool:** [Gitleaks](https://github.com/gitleaks/gitleaks) v8+

**Why Gitleaks:**
- Industry standard for secret detection
- Detects 100+ secret patterns (GitHub tokens, AWS keys, API tokens, JWT, etc.)
- Fast enough for interactive use (~1 second for small repos)
- Single binary, easy to install
- Actively maintained

**Detection Flow:**
1. Check installation: `command -v gitleaks &> /dev/null`
2. If not installed:
   ```
   Gitleaks not found. Install? (recommended for security)
   [Y]es - install via go install
   [N]o - proceed without secret detection (WARNING)
   ```
3. Scan staged files: `gitleaks detect --source .claude/ --verbose --no-git`
4. If secrets found:
   - Show gitleaks output (file, line number, secret type)
   - Ask: "⚠️  Secrets detected. What to do?"
     - [R]eview and fix manually (abort push)
     - [C]ontinue anyway (you take responsibility)
5. If user continues: warn in commit message

**Fallback:** If gitleaks unavailable and user declines install, proceed with prominent warning message.

### 4. Documentation

**workBits/.claude/README.md:**

```markdown
# Claude Code Configuration Sync

This folder contains synced Claude Code configuration for keeping
multiple machines in sync via GitHub.

## What's Synced

- `skills/` - Custom Claude skills
- `settings.json` - Global Claude settings

## What's NOT Synced

- `settings.local.json` - Machine-specific overrides (gitignored)
- Project-specific state, history, cache

## Usage

### Push changes to GitHub:
Run: `/refresh-to-workbits` in Claude Code

### Pull latest from GitHub:
Run: `/refresh-from-workbits` in Claude Code

## First-Time Setup (new laptop)

1. Clone: `git clone https://github.com/jluhrsen/workBits.git ~/repos/workBits`
2. In Claude Code: `/refresh-from-workbits`
3. Answer "Y" to "First sync?" to merge with existing local config
4. Run `/refresh-to-workbits` to push merged result back to GitHub

## Security

Gitleaks scans for secrets before pushing. Review any warnings carefully.
Never commit API tokens, passwords, or other sensitive data.
```

**workBits/.gitignore additions:**
```
.claude/settings.local.json
.claude/backups/
```

## First-Sync Bootstrap Strategy

**The Problem:**
- Laptop A: has skills {check-branch-sync, ci-prow-navigation, jira}
- Laptop B: has different skills {unknown-but-valuable}
- Need to merge both sets into GitHub without losing anything

**The Solution:**

**Phase 1 - Laptop A (initial push):**
1. Run `/refresh-to-workbits` from Laptop A
2. If workBits `.claude/` is empty or minimal: just push
3. If has content: pull first, merge timestamps, then push

**Phase 2 - Laptop B (first sync):**
1. Run `/refresh-from-workbits` on Laptop B
2. Answer "Y" to "First sync on this machine?"
3. Skill merges:
   - Downloads Laptop A's skills from GitHub
   - Keeps Laptop B's local-only skills
   - For files in both: newer timestamp wins
4. Run `/refresh-to-workbits` to push merged result back
5. Now GitHub has union of both laptops

**Phase 3 - Laptop A (pull merged result):**
1. Run `/refresh-from-workbits` on Laptop A
2. Answer "N" to first sync (regular mode now)
3. Gets Laptop B's unique skills

**After bootstrap:**
- Both laptops have all skills
- GitHub is source of truth
- Regular syncs use simple timestamp comparison

## Implementation Details

**Skill File Format:**
Standard Claude skill markdown with frontmatter:
```markdown
---
name: refresh-to-workbits
description: Push local Claude config (skills, settings) to GitHub workBits repo
---

# Refresh to workBits

[Instructions for users]

## Implementation

[Bash code blocks]
```

**Timestamp Comparison (cross-platform):**
```bash
# Linux
get_timestamp() { stat -c %Y "$1"; }

# macOS  
get_timestamp() { stat -f %m "$1"; }

# Detect platform
if stat -c %Y . &>/dev/null; then
    GET_TS="stat -c %Y"
else
    GET_TS="stat -f %m"
fi
```

**Directory Sync:**
```bash
# Use rsync to sync skills (mirrors source, removing deleted files)
rsync -a --delete ~/.claude/skills/ ~/repos/workBits/.claude/skills/

# -a = archive mode (recursive, preserve permissions, timestamps)
# --delete = remove files in dest that don't exist in source
# Trailing slashes are important: source/ means "contents of source"
```

## Testing Strategy

**Phase 1 - Current Laptop:**
1. Create backup: `cp -r ~/.claude ~/.claude.backup`
2. Run `/refresh-to-workbits` - verify push to GitHub
3. Check GitHub: skills and settings.json present
4. Modify a skill locally
5. Run `/refresh-to-workbits` again - verify incremental push

**Phase 2 - Second Laptop (when available):**
1. Run `/refresh-from-workbits` with first-sync=Y
2. Verify local skills merged with GitHub skills
3. Run `/refresh-to-workbits` - verify merged result pushed
4. On first laptop: run `/refresh-from-workbits` - verify gets second laptop's skills

**Phase 3 - Regular Use:**
1. Make changes on either laptop
2. Push from that laptop
3. Pull on other laptop
4. Verify changes propagated correctly

## Edge Cases & Error Handling

| Scenario | Handling |
|----------|----------|
| workBits repo doesn't exist | Offer to clone from GitHub |
| Git conflicts during pull | Show error, user resolves manually |
| Network/GitHub down | Show error, exit gracefully, no retry |
| Uncommitted changes in workBits | Ask: commit them / stash them / cancel |
| File permission errors | Show error with permissions needed |
| Gitleaks not installed | Offer install, fallback to warning |
| Skills sync themselves | Meta! The sync skills will sync themselves |
| Empty settings.json | Valid, sync empty file |
| Very large skill files | No special handling, git handles it |

## Security Considerations

1. **Secret Detection:** Gitleaks scans before every push
2. **GitHub Privacy:** workBits is a private repo (assumed)
3. **Local Permissions:** `~/.claude/` should be user-readable only
4. **No Auto-Commit:** User explicitly invokes sync (no hooks)
5. **Review Before Push:** Gitleaks shows what will be committed

## Success Criteria

- ✅ Can push local config to GitHub from Laptop A
- ✅ Can pull config from GitHub to Laptop B
- ✅ First-sync merge preserves unique content from both laptops
- ✅ Subsequent syncs use timestamp comparison correctly
- ✅ Secrets are detected and prevented from being committed
- ✅ Both laptops stay in sync with minimal manual effort
- ✅ Skills sync themselves (meta-sync works)

## Future Enhancements (Out of Scope)

- Automatic sync on skill changes (via git hooks or watchers)
- Conflict resolution UI (for now: manual)
- Sync additional Claude config (keybindings, prompts)
- Multi-machine tracking (which machines are in sync)
- Diff preview before sync
- Selective skill sync (choose which skills to sync)
