# claude-sync

Portable Claude Code / Codex / Cursor configuration, shared between machines
through this repo. One machine pushes its live config here; another applies it.

## Layout

| Path | What it is |
|---|---|
| `manifest.json` | generated inventory: marketplaces, plugins, file map, what is deliberately excluded |
| `files/` | the config payload itself (settings, `CLAUDE.md`, local skills, shell glue, Codex/Cursor config) |
| `bin/collect.py` | reads this machine's live config and regenerates `manifest.json` + `files/` |
| `bin/apply.py` | copies `files/` into place, backing up whatever it replaces |
| `sync.sh` | `push` (collect, scan for secrets, commit, push) and `pull` (git pull, apply) |
| `bootstrap.sh` | new machine: clone repos, add marketplaces, install plugins, apply files |

## Usage

```bash
./claude-sync/sync.sh push     # this machine -> repo -> GitHub
./claude-sync/sync.sh pull     # GitHub -> this machine
./claude-sync/bootstrap.sh     # new machine, first time (--dry-run to preview)
```

In Claude Code the same two operations are `/refresh-to-workbits` and
`/refresh-from-workbits` from the `workbits-sync` plugin.

## Secrets

Nothing credential-shaped is committed. `collect.py` replaces any env key
matching `*TOKEN|*SECRET|*PASSWORD|*API_KEY|*_KEY` with a placeholder, and
`sync.sh push` refuses to commit if a token, private key or `client_secret`
pattern shows up in the payload (plus a `gitleaks` pass when installed).

`JIRA_API_TOKEN` is the one credential the config needs at runtime. The
committed settings carry the placeholder
`__FROM_FILE:$HOME/repos/workBits/jira_token__`; `apply.py` fills it from
`$HOME/repos/workBits/jira_token`, which is gitignored. Put the token there by
hand on each machine.

Per-machine logins that are never synced: `~/.claude/.credentials.json`,
`~/.codex/auth.json`, Cursor auth, and gcloud ADC for the Vertex path.

## Merge-only files

Codex and Cursor rewrite their own config files (plugin caches, MCP wiring,
auth, UI counters), so `apply.py` never overwrites an existing
`~/.codex/config.toml` or `~/.cursor/cli-config.json`. If one is already there
it writes `<file>.from-sync` beside it for a hand merge; on a fresh machine it
writes the file directly.

## Deliberately not synced

Session transcripts, `history.jsonl`, `file-history/`, shell snapshots,
telemetry, plugin and marketplace caches (re-fetched from source), claude.ai
synced skills, caveman runtime state, and `~/.claude/projects/*/memory/`.
Memory files are work notes about internal systems, so they stay out of a
public repo and move between machines out of band.

## Profiles

`settings.personal.json` and `settings.work.json` differ only in the Vertex
keys (`CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_VERTEX_PROJECT_ID`,
`CLOUD_ML_REGION`). Claude Code is started against one of them explicitly, via
the `claude-work` / `claude-home` aliases in `files/zsh/aliases.zsh`.
