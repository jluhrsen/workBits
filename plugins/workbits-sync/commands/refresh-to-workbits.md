---
description: Push local Claude/Codex/Cursor config to the workBits repo on GitHub, with secret scrubbing
---

# Refresh to workBits

Collect this machine's AI tooling configuration into `workBits/claude-sync/`
and push it to GitHub.

Run:

```bash
~/repos/workBits/claude-sync/sync.sh push
```

That script:

1. Runs `claude-sync/bin/collect.py`, which regenerates `claude-sync/manifest.json`
   (marketplaces, plugin inventory, file map) and refreshes `claude-sync/files/`
   with `~/.claude/CLAUDE.md`, `settings.personal.json`, `settings.work.json`,
   `settings.local.json`, local skills, the Vertex env snippet, the shell
   aliases, and the portable parts of the Codex and Cursor configs.
2. Replaces every credential-shaped env value with a placeholder. `JIRA_API_TOKEN`
   becomes `__FROM_FILE:$HOME/repos/workBits/jira_token__`.
3. Scans the payload for token, private key and `client_secret` patterns, plus a
   `gitleaks` pass if installed, and aborts the commit on any hit.
4. Commits and pushes only `claude-sync/`.

Report what changed in the commit, and note anything the scan flagged.

If the token file `~/repos/workBits/jira_token` is missing, say so: it is
gitignored and must exist for `pull` to restore a working Jira setup.
