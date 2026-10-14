---
description: Pull the latest Claude/Codex/Cursor config from the workBits repo and apply it locally
---

# Refresh from workBits

Apply the configuration payload in `workBits/claude-sync/` to this machine.

Run:

```bash
~/repos/workBits/claude-sync/sync.sh pull
```

That script fast-forwards the repo, then runs `claude-sync/bin/apply.py`, which:

1. Backs up every file it is about to replace into
   `~/.claude/backups/claude-sync-<timestamp>/`.
2. Copies the payload into place: `~/.claude/CLAUDE.md`, the three settings
   files, local skills (machine-managed `skills/synced/` is left alone),
   `~/.config/claude-code-vertex/env.sh`, `~/.claude/aliases.zsh`,
   `~/.codex/config.toml`, `~/.cursor/cli-config.json`.
3. Fills the `JIRA_API_TOKEN` placeholder from `~/repos/workBits/jira_token`
   and chmods the settings file to 600. If that token file is missing, the
   placeholder stays and the script says so.

Pass `--dry-run` through to preview: `~/repos/workBits/claude-sync/sync.sh pull --dry-run`.

Settings changes need a Claude Code restart. For a brand new machine, use
`~/repos/workBits/claude-sync/bootstrap.sh` instead - it also clones the repos
behind the directory marketplaces and installs the plugins.
