---
description: Pull latest Claude config from GitHub workBits repo with smart merging
---

# Refresh from workBits

Pull the latest Claude Code configuration from the workBits GitHub repository and sync ai-helpers plugins.

**What gets synced:**
- `workBits/.claude/skills/` → `~/.claude/skills/`
- Portable settings (enabledPlugins, extraKnownMarketplaces, permissions) merged into `~/.claude/settings.json`
- ai-helpers repository updated to latest main branch
- New ai-helpers plugins automatically detected and enabled

**Smart merging:** Skills use timestamp comparison. Settings are key-merged so machine-specific preferences (model, effortLevel, etc.) are preserved.

## Usage

Just run this skill. It will:
1. Update ai-helpers to latest main (if repo is clean)
2. Pull latest from workBits GitHub
3. Ask if this is your first sync
4. Copy skill files based on timestamps (newer wins)
5. Merge portable settings keys into global settings
6. Auto-detect and enable new ai-helpers plugins
7. Preserve local-only files and machine-specific preferences

## Implementation

```bash
#!/bin/bash
set -euo pipefail

WORKBITS_DIR="$HOME/repos/workBits"
AI_HELPERS_DIR="$HOME/repos/RedHat/openshift/ai-helpers"
CLAUDE_DIR="$HOME/.claude"

echo "Syncing Claude config from workBits and ai-helpers..."
echo ""

# Check for jq (required for settings merge)
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is required for settings merge but not installed."
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

# Step 2: Update ai-helpers if it exists
if [[ -d "$AI_HELPERS_DIR" ]]; then
    echo "Updating ai-helpers..."
    cd "$AI_HELPERS_DIR"
    
    # Check if we can switch to main (clean working tree)
    if git diff-index --quiet HEAD -- 2>/dev/null; then
        current_branch=$(git rev-parse --abbrev-ref HEAD)
        if [[ "$current_branch" != "main" ]]; then
            echo "  Switching to main branch..."
            git checkout main 2>/dev/null || echo "  Warning: Could not switch to main, staying on $current_branch"
        fi
        echo "  Pulling latest from GitHub..."
        if ! git pull; then
            echo "  Warning: Git pull failed for ai-helpers, continuing anyway..."
        fi
    else
        echo "  Warning: ai-helpers has uncommitted changes, skipping git pull"
    fi
    echo ""
else
    echo "Warning: ai-helpers not found at $AI_HELPERS_DIR, skipping..."
    echo ""
fi

# Step 3: Pull latest from workBits
cd "$WORKBITS_DIR"
echo "Pulling latest from workBits..."
if ! git pull; then
    echo ""
    echo "ERROR: Git pull failed. Resolve manually and try again."
    exit 1
fi

# Step 4: Ask about first sync
echo ""
read -p "First sync on this machine? (will merge, not overwrite) [y/N]: " first_sync

# Helper function: get file timestamp (cross-platform)
get_timestamp() {
    local file="$1"
    if stat -c %Y "$file" &>/dev/null; then
        stat -c %Y "$file"
    else
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
        local hours=$((abs_diff / 3600))
        echo "$hours hour$([[ $hours -ne 1 ]] && echo s || true)"
    else
        local days=$((abs_diff / 86400))
        echo "$days day$([[ $days -ne 1 ]] && echo s || true)"
    fi
}

# Counters
copied=0
kept_local=0
skipped=0

# Step 5: Sync skills
echo ""
echo "Syncing skills..."

if [[ "$first_sync" =~ ^[Yy]$ ]]; then
    echo "  (First sync mode: merging local + remote)"
fi

mkdir -p "$CLAUDE_DIR/skills"

if [[ -d "$WORKBITS_DIR/.claude/skills" ]]; then
    cd "$WORKBITS_DIR/.claude/skills"
    while IFS= read -r -d '' remote_file; do
        relative_path="${remote_file#./}"
        local_file="$CLAUDE_DIR/skills/$relative_path"
        mkdir -p "$(dirname "$local_file")"
        if [[ ! -f "$local_file" ]]; then
            cp "$remote_file" "$local_file"
            echo "  Copied: $relative_path (new file)"
            ((copied++))
        else
            remote_ts=$(get_timestamp "$remote_file")
            local_ts=$(get_timestamp "$local_file")
            if [[ "$first_sync" =~ ^[Yy]$ ]]; then
                if [[ $remote_ts -gt $local_ts ]]; then
                    age=$(time_diff_human $local_ts $remote_ts)
                    cp "$remote_file" "$local_file"
                    echo "  Updated: $relative_path (remote newer by $age)"
                    ((copied++))
                else
                    echo "  Kept local: $relative_path (local newer)"
                    ((kept_local++))
                fi
            else
                if [[ $remote_ts -gt $local_ts ]]; then
                    age=$(time_diff_human $local_ts $remote_ts)
                    echo "  Overwriting: $relative_path (remote newer by $age)"
                    cp "$remote_file" "$local_file"
                    ((copied++))
                else
                    ((skipped++))
                fi
            fi
        fi
    done < <(find . -type f -print0)
fi

# Step 6: Merge portable settings into global settings
echo ""
echo "Merging settings..."

remote_settings="$WORKBITS_DIR/.claude/settings.json"
local_settings="$CLAUDE_DIR/settings.json"

if [[ -f "$remote_settings" ]]; then
    # Expand $HOME placeholder in extraKnownMarketplaces paths
    remote_expanded=$(jq --arg home "$HOME" '
        if .extraKnownMarketplaces then
            .extraKnownMarketplaces |= with_entries(
                .value.source.path |= gsub("\\$HOME"; $home)
            )
        else . end
    ' "$remote_settings")

    # Extract portable keys from repo settings
    portable_keys=$(echo "$remote_expanded" | jq '{
        enabledPlugins: .enabledPlugins,
        extraKnownMarketplaces: .extraKnownMarketplaces,
        permissions: .permissions
    } | with_entries(select(.value != null))')

    if [[ -f "$local_settings" ]]; then
        # Merge: portable keys from repo override, local machine keys preserved
        merged=$(jq -s '.[0] * .[1]' "$local_settings" <(echo "$portable_keys"))
        echo "$merged" | jq '.' > "$local_settings.tmp" && mv "$local_settings.tmp" "$local_settings"
        echo "  Merged portable keys into global settings"
        echo "  (enabledPlugins, extraKnownMarketplaces, permissions)"
        echo "  Machine-specific keys preserved (model, effortLevel, etc.)"
    else
        # No local settings yet, use portable keys as starting point
        echo "$portable_keys" | jq '.' > "$local_settings"
        echo "  Created global settings from portable keys"
    fi
else
    echo "  settings.json not found in workBits (skipped)"
fi

# Step 7: Check for new ai-helpers plugins
echo ""
echo "Checking for new ai-helpers plugins..."

if [[ -f "$AI_HELPERS_DIR/.claude-plugin/marketplace.json" ]] && [[ -f "$local_settings" ]]; then
    # Get all plugin names from ai-helpers marketplace
    available_plugins=$(jq -r '.plugins[].name' "$AI_HELPERS_DIR/.claude-plugin/marketplace.json" | sort)
    
    # Get currently enabled ai-helpers plugins
    enabled_plugins=$(jq -r '.enabledPlugins | keys[] | select(endswith("@ai-helpers")) | sub("@ai-helpers$";"")' "$local_settings" | sort)
    
    # Find new plugins that aren't enabled yet
    new_plugins=$(comm -23 <(echo "$available_plugins") <(echo "$enabled_plugins"))
    
    if [[ -n "$new_plugins" ]]; then
        new_count=$(echo "$new_plugins" | wc -l)
        echo "  Found $new_count new plugin(s):"
        echo "$new_plugins" | sed 's/^/    - /'
        echo ""
        echo "  Enabling new plugins..."
        
        # Build jq expression to add new plugins
        for plugin in $new_plugins; do
            # Add to local settings
            temp=$(jq --arg plugin "${plugin}@ai-helpers" '.enabledPlugins[$plugin] = true' "$local_settings")
            echo "$temp" > "$local_settings"
            
            # Add to workBits settings
            if [[ -f "$remote_settings" ]]; then
                temp=$(jq --arg plugin "${plugin}@ai-helpers" '.enabledPlugins[$plugin] = true' "$remote_settings")
                echo "$temp" > "$remote_settings"
            fi
        done
        
        echo "  ✓ Enabled $new_count new plugin(s)"
    else
        echo "  All ai-helpers plugins already enabled"
    fi
else
    echo "  Skipping plugin check (ai-helpers marketplace or settings not found)"
fi

# Step 8: Summary
echo ""
echo "Summary:"
echo "  - Files copied/updated: $copied"
if [[ "$first_sync" =~ ^[Yy]$ ]]; then
    echo "  - Local files kept (newer): $kept_local"
else
    echo "  - Files skipped (local newer): $skipped"
fi
echo ""

if [[ "$first_sync" =~ ^[Yy]$ ]] && [[ $kept_local -gt 0 ]]; then
    echo "Tip: Run /refresh-to-workbits to push your unique local skills to GitHub"
    echo ""
fi

echo "Sync complete!"
```
