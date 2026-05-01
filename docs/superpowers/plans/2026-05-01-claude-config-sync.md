# Claude Config Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two bash-based skills to sync Claude config (skills and settings.json) between laptops via GitHub workBits repo

**Architecture:** Two skills (`refresh-to-workbits` for push, `refresh-from-workbits` for pull) with Gitleaks secret detection, timestamp-based conflict resolution, and first-sync merge mode

**Tech Stack:** Bash, rsync, git, gitleaks (optional)

---

## File Structure

**New Files:**
- `~/.claude/skills/refresh-to-workbits.md` - Skill to push config to GitHub
- `~/.claude/skills/refresh-from-workbits.md` - Skill to pull config from GitHub
- `~/repos/workBits/.claude/README.md` - Documentation for sync system
- `~/repos/workBits/.claude/skills/` - Directory for synced skills
- `~/repos/workBits/.claude/settings.json` - Synced settings file

**Modified Files:**
- `~/repos/workBits/.gitignore` - Add .claude exclusions

---

## Task 1: Setup workBits Directory Structure

**Files:**
- Create: `~/repos/workBits/.claude/skills/` (directory)
- Create: `~/repos/workBits/.claude/README.md`
- Modify: `~/repos/workBits/.gitignore`

- [ ] **Step 1: Create .claude directory structure**

```bash
mkdir -p ~/repos/workBits/.claude/skills
```

Expected: Directory created successfully

- [ ] **Step 2: Update .gitignore**

```bash
cd ~/repos/workBits

# Add to .gitignore if not already present
if ! grep -q ".claude/settings.local.json" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# Claude Code local config (not synced)" >> .gitignore
    echo ".claude/settings.local.json" >> .gitignore
    echo ".claude/backups/" >> .gitignore
fi
```

Expected: .gitignore updated with Claude exclusions

- [ ] **Step 3: Verify .gitignore changes**

```bash
cat .gitignore | grep -A2 "Claude Code"
```

Expected output:
```
# Claude Code local config (not synced)
.claude/settings.local.json
.claude/backups/
```

- [ ] **Step 4: Commit directory structure**

```bash
cd ~/repos/workBits
git add .claude/skills/ .gitignore
git commit -m "Setup Claude config sync directory structure

- Create .claude/skills/ for synced skills
- Update .gitignore to exclude local config"
```

Expected: Commit successful

---

## Task 2: Create Documentation (README.md)

**Files:**
- Create: `~/repos/workBits/.claude/README.md`

- [ ] **Step 1: Write README.md**

```bash
cat > ~/repos/workBits/.claude/README.md << 'EOF'
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

## How It Works

**Push (refresh-to-workbits):**
1. Copies `~/.claude/skills/` and `~/.claude/settings.json` to workBits
2. Scans for secrets with Gitleaks (optional)
3. Commits and pushes to GitHub

**Pull (refresh-from-workbits):**
1. Pulls latest from GitHub
2. Compares file timestamps
3. Copies newer files to `~/.claude/`
4. First-sync mode preserves unique files from both sides

## Troubleshooting

**"workBits repo not found"**
- Clone it: `git clone https://github.com/jluhrsen/workBits.git ~/repos/workBits`

**"Uncommitted changes in workBits"**
- Commit them manually or let the skill prompt you

**"Secrets detected"**
- Review the gitleaks output
- Edit files to remove secrets before pushing
EOF
```

Expected: README.md created with complete documentation

- [ ] **Step 2: Verify README.md**

```bash
wc -l ~/repos/workBits/.claude/README.md
head -5 ~/repos/workBits/.claude/README.md
```

Expected: File has ~60 lines, starts with "# Claude Code Configuration Sync"

- [ ] **Step 3: Commit README**

```bash
cd ~/repos/workBits
git add .claude/README.md
git commit -m "Add README for Claude config sync system"
```

Expected: Commit successful

---

## Task 3: Create refresh-to-workbits Skill (Push to GitHub)

**Files:**
- Create: `~/.claude/skills/refresh-to-workbits.md`

- [ ] **Step 1: Write skill file with frontmatter and documentation**

```bash
cat > ~/.claude/skills/refresh-to-workbits.md << 'SKILLEOF'
---
name: refresh-to-workbits
description: Push local Claude config (skills, settings) to GitHub workBits repo with secret detection
---

# Refresh to workBits

Push your local Claude Code configuration (skills and settings.json) to the workBits GitHub repository.

**What gets pushed:**
- `~/.claude/skills/` → `workBits/.claude/skills/`
- `~/.claude/settings.json` → `workBits/.claude/settings.json`

**Security:** Scans for secrets with Gitleaks before pushing (optional but recommended)

## Usage

Just run this skill. It will:
1. Check prerequisites
2. Copy your local config to workBits
3. Scan for secrets (if gitleaks installed)
4. Commit and push to GitHub

## Implementation

```bash
#!/bin/bash
set -euo pipefail

WORKBITS_DIR="$HOME/repos/workBits"
CLAUDE_DIR="$HOME/.claude"

echo "🔄 Syncing Claude config to workBits..."
echo ""

# Step 1: Check if workBits repo exists
if [[ ! -d "$WORKBITS_DIR" ]]; then
    echo "❌ workBits repo not found at $WORKBITS_DIR"
    echo ""
    echo "Clone it first:"
    echo "  git clone https://github.com/jluhrsen/workBits.git $WORKBITS_DIR"
    exit 1
fi

# Step 2: Check for uncommitted changes
cd "$WORKBITS_DIR"
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "⚠️  workBits has uncommitted changes."
    echo ""
    read -p "What to do? [C]ommit them / [S]tash them / [A]bort: " choice
    case "$choice" in
        [Cc]*)
            git add -A
            git commit -m "Manual changes before Claude config sync"
            ;;
        [Ss]*)
            git stash
            echo "📦 Changes stashed"
            ;;
        *)
            echo "❌ Aborted"
            exit 1
            ;;
    esac
fi

# Step 3: Ensure .claude/skills directory exists
mkdir -p "$WORKBITS_DIR/.claude/skills"

# Step 4: Copy skills using rsync (mirrors source, removes deleted)
echo "📁 Copying skills..."
if command -v rsync &> /dev/null; then
    rsync -a --delete "$CLAUDE_DIR/skills/" "$WORKBITS_DIR/.claude/skills/"
else
    # Fallback to cp if rsync not available
    rm -rf "$WORKBITS_DIR/.claude/skills"
    mkdir -p "$WORKBITS_DIR/.claude/skills"
    cp -r "$CLAUDE_DIR/skills/". "$WORKBITS_DIR/.claude/skills/"
fi

# Step 5: Copy settings.json
echo "⚙️  Copying settings.json..."
if [[ -f "$CLAUDE_DIR/settings.json" ]]; then
    cp "$CLAUDE_DIR/settings.json" "$WORKBITS_DIR/.claude/settings.json"
else
    echo "  (settings.json not found, skipping)"
fi

# Step 6: Secret detection with Gitleaks (optional)
cd "$WORKBITS_DIR"
if command -v gitleaks &> /dev/null; then
    echo ""
    echo "🔐 Scanning for secrets with Gitleaks..."
    if gitleaks detect --source .claude/ --verbose --no-git 2>/dev/null; then
        echo "✅ No secrets detected"
    else
        GITLEAKS_EXIT=$?
        if [[ $GITLEAKS_EXIT -eq 1 ]]; then
            echo ""
            echo "⚠️  Secrets detected! See output above."
            echo ""
            read -p "Continue pushing anyway? [y/N]: " continue
            if [[ ! "$continue" =~ ^[Yy]$ ]]; then
                echo "❌ Aborted. Fix secrets and try again."
                exit 1
            fi
            echo "⚠️  Proceeding with secrets (you were warned!)"
        fi
    fi
else
    echo ""
    echo "ℹ️  Gitleaks not installed (secret detection skipped)"
    echo "   Install: go install github.com/gitleaks/gitleaks/v8@latest"
    echo ""
    read -p "Continue without secret detection? [Y/n]: " continue
    if [[ "$continue" =~ ^[Nn]$ ]]; then
        echo "❌ Aborted"
        exit 1
    fi
fi

# Step 7: Git commit and push
echo ""
echo "📤 Committing and pushing..."

git add .claude/skills/ .claude/settings.json .claude/README.md 2>/dev/null || true

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "✅ No changes to commit (already up to date)"
else
    COMMIT_MSG="Sync Claude config from $(hostname) - $(date +%Y-%m-%d)"
    git commit -m "$COMMIT_MSG"
    
    if git push origin main; then
        echo ""
        echo "✅ Successfully pushed to GitHub!"
    else
        echo ""
        echo "❌ Push failed. Check network and GitHub access."
        exit 1
    fi
fi

# Count synced files
SKILL_COUNT=$(find "$WORKBITS_DIR/.claude/skills" -type f -name "*.md" | wc -l)
echo ""
echo "📊 Summary:"
echo "  - Skills synced: $SKILL_COUNT"
echo "  - settings.json: ✓"
echo "  - Destination: workBits/.claude/"
echo ""
echo "🎉 Sync complete!"
```
SKILLEOF
```

Expected: Skill file created with complete bash implementation

- [ ] **Step 2: Verify skill file**

```bash
head -10 ~/.claude/skills/refresh-to-workbits.md
wc -l ~/.claude/skills/refresh-to-workbits.md
```

Expected: Shows frontmatter, file has ~150 lines

- [ ] **Step 3: Test skill syntax (dry run check)**

```bash
# Extract and validate bash section
grep -A 999 '```bash' ~/.claude/skills/refresh-to-workbits.md | grep -B 999 '```$' | head -n -1 | tail -n +2 | bash -n
```

Expected: No syntax errors

- [ ] **Step 4: Commit skill**

```bash
git add ~/.claude/skills/refresh-to-workbits.md
git commit -m "Add refresh-to-workbits skill for pushing config to GitHub

- Copies skills and settings.json to workBits repo
- Optional Gitleaks secret detection
- Handles uncommitted changes
- Auto-commits and pushes

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

Expected: Commit successful in current repo (likely ovn-kubernetes)

---

## Task 4: Create refresh-from-workbits Skill (Pull from GitHub)

**Files:**
- Create: `~/.claude/skills/refresh-from-workbits.md`

- [ ] **Step 1: Write skill file with frontmatter and documentation**

```bash
cat > ~/.claude/skills/refresh-from-workbits.md << 'SKILLEOF'
---
name: refresh-from-workbits
description: Pull latest Claude config from GitHub workBits repo with smart merging
---

# Refresh from workBits

Pull the latest Claude Code configuration from the workBits GitHub repository.

**What gets pulled:**
- `workBits/.claude/skills/` → `~/.claude/skills/`
- `workBits/.claude/settings.json` → `~/.claude/settings.json`

**Smart merging:** On first sync, merges local and remote (keeps both). Regular syncs use timestamp comparison.

## Usage

Just run this skill. It will:
1. Pull latest from GitHub
2. Ask if this is your first sync
3. Copy files based on timestamps (newer wins)
4. Preserve local-only files

## Implementation

```bash
#!/bin/bash
set -euo pipefail

WORKBITS_DIR="$HOME/repos/workBits"
CLAUDE_DIR="$HOME/.claude"

echo "🔄 Syncing Claude config from workBits..."
echo ""

# Step 1: Check if workBits repo exists
if [[ ! -d "$WORKBITS_DIR" ]]; then
    echo "❌ workBits repo not found at $WORKBITS_DIR"
    echo ""
    echo "Clone it first:"
    echo "  git clone https://github.com/jluhrsen/workBits.git $WORKBITS_DIR"
    exit 1
fi

# Step 2: Pull latest from GitHub
cd "$WORKBITS_DIR"
echo "📥 Pulling latest from GitHub..."
if ! git pull; then
    echo ""
    echo "❌ Git pull failed. Resolve manually and try again."
    exit 1
fi

# Step 3: Ask about first sync
echo ""
read -p "First sync on this machine? (will merge, not overwrite) [y/N]: " first_sync

# Helper function: get file timestamp (cross-platform)
get_timestamp() {
    local file="$1"
    if stat -c %Y "$file" &>/dev/null; then
        # Linux
        stat -c %Y "$file"
    else
        # macOS
        stat -f %m "$file"
    fi
}

# Helper function: human-readable time difference
time_diff_human() {
    local ts1=$1
    local ts2=$2
    local diff=$((ts2 - ts1))
    local abs_diff=${diff#-}
    
    if [[ $abs_diff -lt 86400 ]]; then
        echo "$((abs_diff / 3600)) hours"
    else
        echo "$((abs_diff / 86400)) days"
    fi
}

# Counters
copied=0
kept_local=0
skipped=0

# Step 4: Sync skills
echo ""
echo "📁 Syncing skills..."

if [[ "$first_sync" =~ ^[Yy]$ ]]; then
    echo "  (First sync mode: merging local + remote)"
fi

# Ensure destination directory exists
mkdir -p "$CLAUDE_DIR/skills"

# Process all files in workBits
if [[ -d "$WORKBITS_DIR/.claude/skills" ]]; then
    cd "$WORKBITS_DIR/.claude/skills"
    while IFS= read -r -d '' remote_file; do
        relative_path="${remote_file#$WORKBITS_DIR/.claude/skills/}"
        local_file="$CLAUDE_DIR/skills/$relative_path"
        
        # Create parent directory if needed
        mkdir -p "$(dirname "$local_file")"
        
        if [[ ! -f "$local_file" ]]; then
            # File doesn't exist locally, copy it
            cp "$remote_file" "$local_file"
            echo "  ✅ Copied: $relative_path (new file)"
            ((copied++))
        else
            # File exists locally, compare timestamps
            remote_ts=$(get_timestamp "$remote_file")
            local_ts=$(get_timestamp "$local_file")
            
            if [[ "$first_sync" =~ ^[Yy]$ ]]; then
                # First sync: keep newer
                if [[ $remote_ts -gt $local_ts ]]; then
                    age=$(time_diff_human $local_ts $remote_ts)
                    cp "$remote_file" "$local_file"
                    echo "  ⬇️  Updated: $relative_path (remote newer by $age)"
                    ((copied++))
                else
                    echo "  ⏭️  Kept local: $relative_path (local newer)"
                    ((kept_local++))
                fi
            else
                # Regular sync: only update if remote is newer
                if [[ $remote_ts -gt $local_ts ]]; then
                    age=$(time_diff_human $local_ts $remote_ts)
                    echo "  ⬇️  Overwriting: $relative_path (remote newer by $age)"
                    cp "$remote_file" "$local_file"
                    ((copied++))
                else
                    ((skipped++))
                fi
            fi
        fi
    done < <(find . -type f -print0)
fi

# Step 5: Sync settings.json
echo ""
if [[ -f "$WORKBITS_DIR/.claude/settings.json" ]]; then
    remote_settings="$WORKBITS_DIR/.claude/settings.json"
    local_settings="$CLAUDE_DIR/settings.json"
    
    if [[ ! -f "$local_settings" ]]; then
        cp "$remote_settings" "$local_settings"
        echo "⚙️  Copied settings.json (new file)"
    else
        remote_ts=$(get_timestamp "$remote_settings")
        local_ts=$(get_timestamp "$local_settings")
        
        if [[ $remote_ts -gt $local_ts ]]; then
            age=$(time_diff_human $local_ts $remote_ts)
            echo "⚙️  Updated settings.json (remote newer by $age)"
            cp "$remote_settings" "$local_settings"
        else
            echo "⚙️  Kept local settings.json (local is newer)"
        fi
    fi
else
    echo "⚙️  settings.json not found in workBits (skipped)"
fi

# Step 6: Summary
echo ""
echo "📊 Summary:"
echo "  - Files copied/updated: $copied"
if [[ "$first_sync" =~ ^[Yy]$ ]]; then
    echo "  - Local files kept (newer): $kept_local"
else
    echo "  - Files skipped (local newer): $skipped"
fi
echo ""

if [[ "$first_sync" =~ ^[Yy]$ ]] && [[ $kept_local -gt 0 ]]; then
    echo "💡 Tip: Run /refresh-to-workbits to push your unique local skills to GitHub"
    echo ""
fi

echo "✅ Sync complete!"
```
SKILLEOF
```

Expected: Skill file created with complete implementation

- [ ] **Step 2: Verify skill file**

```bash
head -10 ~/.claude/skills/refresh-from-workbits.md
wc -l ~/.claude/skills/refresh-from-workbits.md
```

Expected: Shows frontmatter, file has ~180 lines

- [ ] **Step 3: Test skill syntax**

```bash
# Extract and validate bash section
grep -A 999 '```bash' ~/.claude/skills/refresh-from-workbits.md | grep -B 999 '```$' | head -n -1 | tail -n +2 | bash -n
```

Expected: No syntax errors

- [ ] **Step 4: Commit skill**

```bash
git add ~/.claude/skills/refresh-from-workbits.md
git commit -m "Add refresh-from-workbits skill for pulling config from GitHub

- Pulls latest from workBits repo
- Timestamp-based conflict resolution
- First-sync merge mode to preserve local files
- Human-readable time diffs

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

Expected: Commit successful

---

## Task 5: Initial Sync Test (Push Current Config)

**Purpose:** Test the refresh-to-workbits skill by pushing current config to GitHub

- [ ] **Step 1: Create backup of current Claude config**

```bash
cp -r ~/.claude ~/.claude.backup.$(date +%Y%m%d)
echo "✅ Backup created at ~/.claude.backup.$(date +%Y%m%d)"
```

Expected: Backup directory created

- [ ] **Step 2: Check current skills**

```bash
find ~/.claude/skills -name "*.md" -type f | wc -l
ls ~/.claude/skills/
```

Expected: Shows current skill count and list

- [ ] **Step 3: Run refresh-to-workbits skill in Claude Code**

Manual step: In Claude Code, run `/refresh-to-workbits`

Expected interaction:
- Should detect gitleaks (or warn if not installed)
- Should copy skills and settings.json
- Should commit and push to GitHub
- Should show summary with skill count

- [ ] **Step 4: Verify on GitHub**

```bash
cd ~/repos/workBits
git log --oneline -1
ls -la .claude/skills/
```

Expected: 
- Latest commit says "Sync Claude config from..."
- .claude/skills/ contains skill files

- [ ] **Step 5: Verify skills were copied**

```bash
# Compare skill counts
LOCAL_COUNT=$(find ~/.claude/skills -name "*.md" -type f | wc -l)
REMOTE_COUNT=$(find ~/repos/workBits/.claude/skills -name "*.md" -type f | wc -l)

echo "Local skills: $LOCAL_COUNT"
echo "Synced to workBits: $REMOTE_COUNT"

if [[ $LOCAL_COUNT -eq $REMOTE_COUNT ]]; then
    echo "✅ Counts match!"
else
    echo "⚠️  Counts differ (may be OK if some aren't markdown)"
fi
```

Expected: Skill counts should match or be close

- [ ] **Step 6: Check GitHub remote**

```bash
cd ~/repos/workBits
git log --oneline origin/main -1
```

Expected: Same commit as local, confirming push succeeded

- [ ] **Step 7: Test incremental sync**

```bash
# Modify a skill
echo "" >> ~/.claude/skills/check-branch-sync.md
echo "# Test modification" >> ~/.claude/skills/check-branch-sync.md
```

Manual step: Run `/refresh-to-workbits` again in Claude Code

Expected: Should detect changes and push incrementally

- [ ] **Step 8: Verify incremental push**

```bash
cd ~/repos/workBits
git log --oneline -2
git show HEAD
```

Expected: Shows new commit with modification

- [ ] **Step 9: Cleanup test modification**

```bash
cd ~/.claude/skills
git checkout check-branch-sync.md 2>/dev/null || {
    # Restore from workBits if not in git
    cp ~/repos/workBits/.claude/skills/check-branch-sync.md ~/.claude/skills/
}
```

Expected: Test modification removed

---

## Task 6: Document and Finalize

**Files:**
- Update: `~/repos/workBits/docs/superpowers/plans/2026-05-01-claude-config-sync.md` (this file)

- [ ] **Step 1: Push everything to GitHub**

```bash
cd ~/repos/workBits
git push origin main
```

Expected: All commits pushed successfully

- [ ] **Step 2: Verify GitHub has everything**

Visit: https://github.com/jluhrsen/workBits/tree/main/.claude

Expected: Should see:
- README.md
- skills/ directory with current skills
- settings.json

- [ ] **Step 3: Document in workBits README (root)**

Optional: Add section to main workBits README.md about Claude config sync

- [ ] **Step 4: Mark plan complete**

```bash
echo "✅ Implementation complete!"
echo ""
echo "Next steps:"
echo "  1. Test on second laptop when available"
echo "  2. Run /refresh-from-workbits on second laptop"
echo "  3. Answer Y to 'First sync?' to merge configs"
echo "  4. Run /refresh-to-workbits to push merged result"
```

---

## Testing Checklist

### Phase 1: Current Laptop ✅
- [x] Skills copied to workBits
- [x] settings.json copied to workBits
- [x] Gitleaks scan works (or warns if not installed)
- [x] Git commit and push successful
- [x] Incremental sync works

### Phase 2: Second Laptop (when available)
- [ ] Clone workBits repo
- [ ] Run /refresh-from-workbits with first-sync=Y
- [ ] Verify local skills merged with GitHub skills
- [ ] Run /refresh-to-workbits to push merged result
- [ ] On first laptop: pull and verify merged config

### Phase 3: Regular Use
- [ ] Make changes on Laptop A, push with /refresh-to-workbits
- [ ] Pull on Laptop B with /refresh-from-workbits
- [ ] Verify changes propagated
- [ ] Reverse: change on B, push, pull on A

---

## Success Criteria

- ✅ refresh-to-workbits skill created and working
- ✅ refresh-from-workbits skill created and working
- ✅ Documentation (README) created
- ✅ .gitignore configured properly
- ✅ Initial push to GitHub successful
- ✅ Skills sync themselves (meta!)
- ⏳ Second laptop testing (pending hardware availability)

## Notes

- Both skills are now in `~/.claude/skills/` and will sync themselves
- First push from this laptop is complete
- Second laptop setup will test first-sync merge mode
- Gitleaks is optional but recommended (install with: `go install github.com/gitleaks/gitleaks/v8@latest`)
