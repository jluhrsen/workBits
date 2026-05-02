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
