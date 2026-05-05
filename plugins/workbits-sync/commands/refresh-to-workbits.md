---
description: Push local Claude config (skills, settings) to GitHub workBits repo with secret detection
---

# Refresh to workBits

Push your local Claude Code configuration (skills and portable settings) to the workBits GitHub repository.

**What gets pushed:**
- `~/.claude/skills/` → `workBits/.claude/skills/`
- Portable settings keys (enabledPlugins, extraKnownMarketplaces, permissions) extracted from `~/.claude/settings.json` into `workBits/.claude/settings.json`

**What stays local:** Machine-specific keys like model, effortLevel, alwaysThinkingEnabled are NOT pushed.

**Security:** Scans for secrets with Gitleaks before pushing (optional but recommended)

## Usage

Just run this skill. It will:
1. Check prerequisites
2. Copy skills to workBits
3. Extract portable settings keys into workBits (with $HOME path normalization)
4. Scan for secrets (if gitleaks installed)
5. Commit and push to GitHub

## Implementation

```bash
#!/bin/bash
set -euo pipefail

WORKBITS_DIR="$HOME/repos/workBits"
CLAUDE_DIR="$HOME/.claude"

echo "Syncing Claude config to workBits..."
echo ""

# Check for jq (required for settings extraction)
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is required for settings extraction but not installed."
    echo "Install it: sudo dnf install jq  (or)  brew install jq"
    exit 1
fi

# Step 1: Check if workBits repo exists
if [[ ! -d "$WORKBITS_DIR" ]]; then
    echo "ERROR: workBits repo not found at $WORKBITS_DIR"
    echo ""
    echo "Clone it first:"
    echo "  git clone https://github.com/jluhrsen/workBits.git $WORKBITS_DIR"
    exit 1
fi

# Step 2: Check for uncommitted changes
cd "$WORKBITS_DIR"
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "WARNING: workBits has uncommitted changes."
    echo ""
    read -p "What to do? [C]ommit them / [S]tash them / [A]bort: " choice
    case "$choice" in
        [Cc]*)
            git add -A
            git commit -m "Manual changes before Claude config sync"
            ;;
        [Ss]*)
            git stash
            echo "Changes stashed"
            ;;
        *)
            echo "Aborted"
            exit 1
            ;;
    esac
fi

# Step 3: Ensure .claude/skills directory exists
mkdir -p "$WORKBITS_DIR/.claude/skills"

# Step 4: Copy skills using rsync (mirrors source, removes deleted)
echo "Copying skills..."
if command -v rsync &> /dev/null; then
    rsync -a --delete "$CLAUDE_DIR/skills/" "$WORKBITS_DIR/.claude/skills/"
else
    rm -rf "$WORKBITS_DIR/.claude/skills"
    mkdir -p "$WORKBITS_DIR/.claude/skills"
    cp -r "$CLAUDE_DIR/skills/." "$WORKBITS_DIR/.claude/skills/"
fi

# Step 5: Extract portable settings keys and write to repo
echo "Extracting portable settings..."

local_settings="$CLAUDE_DIR/settings.json"
repo_settings="$WORKBITS_DIR/.claude/settings.json"

if [[ -f "$local_settings" ]]; then
    # Extract only portable keys from global settings
    portable=$(jq --arg home "$HOME" '{
        enabledPlugins: .enabledPlugins,
        extraKnownMarketplaces: .extraKnownMarketplaces,
        permissions: .permissions
    } | with_entries(select(.value != null))
    | if .extraKnownMarketplaces then
        .extraKnownMarketplaces |= with_entries(
            .value.source.path |= gsub($home; "$HOME")
        )
      else . end
    ' "$local_settings")

    if [[ -f "$repo_settings" ]]; then
        # Merge portable keys into existing repo settings (preserves repo-only keys like skipDangerousModePermissionPrompt)
        merged=$(jq -s '.[0] * .[1]' "$repo_settings" <(echo "$portable"))
        echo "$merged" | jq '.' > "$repo_settings.tmp" && mv "$repo_settings.tmp" "$repo_settings"
    else
        echo "$portable" | jq '.' > "$repo_settings"
    fi
    echo "  Extracted: enabledPlugins, extraKnownMarketplaces, permissions"
    echo "  Paths normalized: $HOME -> \$HOME"
else
    echo "  settings.json not found locally, skipping"
fi

# Step 6: Secret detection with Gitleaks (optional)
cd "$WORKBITS_DIR"
if command -v gitleaks &> /dev/null; then
    echo ""
    echo "Scanning for secrets with Gitleaks..."
    if gitleaks detect --source .claude/ --verbose --no-git 2>/dev/null; then
        echo "No secrets detected"
    else
        GITLEAKS_EXIT=$?
        if [[ $GITLEAKS_EXIT -eq 1 ]]; then
            echo ""
            echo "WARNING: Secrets detected! See output above."
            echo ""
            read -p "Continue pushing anyway? [y/N]: " continue
            if [[ ! "$continue" =~ ^[Yy]$ ]]; then
                echo "Aborted. Fix secrets and try again."
                exit 1
            fi
            echo "WARNING: Proceeding with secrets (you were warned!)"
        fi
    fi
else
    echo ""
    echo "Gitleaks not installed (secret detection skipped)"
    echo "  Install: go install github.com/gitleaks/gitleaks/v8@latest"
    echo ""
    read -p "Continue without secret detection? [Y/n]: " continue
    if [[ "$continue" =~ ^[Nn]$ ]]; then
        echo "Aborted"
        exit 1
    fi
fi

# Step 7: Git commit and push
echo ""
echo "Committing and pushing..."

git add .claude/skills/ .claude/settings.json .claude/README.md 2>/dev/null || true

if git diff --staged --quiet; then
    echo "No changes to commit (already up to date)"
else
    COMMIT_MSG="Sync Claude config from $(hostname) - $(date +%Y-%m-%d)"
    git commit -m "$COMMIT_MSG"

    if git push origin main; then
        echo ""
        echo "Successfully pushed to GitHub!"
    else
        echo ""
        echo "ERROR: Push failed. Check network and GitHub access."
        exit 1
    fi
fi

SKILL_COUNT=$(find "$WORKBITS_DIR/.claude/skills" -type f -name "*.md" | wc -l)
echo ""
echo "Summary:"
echo "  - Skills synced: $SKILL_COUNT"
echo "  - Portable settings: extracted and normalized"
echo "  - Destination: workBits/.claude/"
echo ""
echo "Sync complete!"
```
