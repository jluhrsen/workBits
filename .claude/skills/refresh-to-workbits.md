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
