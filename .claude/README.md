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
