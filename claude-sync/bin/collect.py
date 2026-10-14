#!/usr/bin/env python3
"""Generate the claude-sync payload in workBits from this machine's live config."""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

HOME = Path.home()
REPO = HOME / "repos/workBits"
SYNC = REPO / "claude-sync"
FILES = SYNC / "files"
CLAUDE = HOME / ".claude"

TOKEN_PLACEHOLDER = "__FROM_FILE:$HOME/repos/workBits/jira_token__"
SECRET_ENV_KEYS = re.compile(r"(TOKEN|SECRET|PASSWORD|API_KEY|_KEY)$", re.I)

def scrub_settings(src: Path) -> dict:
    d = json.loads(src.read_text())
    env = d.get("env", {})
    for k in list(env):
        if SECRET_ENV_KEYS.search(k):
            env[k] = TOKEN_PLACEHOLDER if k == "JIRA_API_TOKEN" else "__SET_LOCALLY__"
    return d

def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")

# --- settings ---
for name in ("settings.personal.json", "settings.work.json"):
    write_json(FILES / "claude" / name, scrub_settings(CLAUDE / name))
shutil.copy2(CLAUDE / "settings.local.json", FILES / "claude/settings.local.json")
shutil.copy2(CLAUDE / "CLAUDE.md", FILES / "claude/CLAUDE.md")

# --- local (non-plugin) skills ---
skills_dst = FILES / "claude/skills"
if skills_dst.exists():
    shutil.rmtree(skills_dst)
skills_dst.mkdir(parents=True)
for d in sorted((CLAUDE / "skills").iterdir()):
    if d.is_dir() and d.name != "synced" and (d / "SKILL.md").exists():
        shutil.copytree(d, skills_dst / d.name)

# --- vertex env.sh ---
vsrc = HOME / ".config/claude-code-vertex/env.sh"
if vsrc.exists():
    (FILES / "config/claude-code-vertex").mkdir(parents=True, exist_ok=True)
    shutil.copy2(vsrc, FILES / "config/claude-code-vertex/env.sh")

# --- codex: keep portable keys only ---
codex_src = HOME / ".codex/config.toml"
if codex_src.exists():
    keep, drop_section = [], False
    for line in codex_src.read_text().splitlines():
        if line.startswith("["):
            sec = line.strip("[]")
            drop_section = (
                sec.startswith("tui") or sec.startswith("hooks") or
                sec.startswith("mcp_servers") or sec.startswith("marketplaces") or
                sec.startswith("desktop")
            )
        if not drop_section:
            keep.append(line)
    out = FILES / "codex/config.toml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(keep).rstrip() + "\n")

# --- cursor: drop auth + caches ---
cur_src = HOME / ".cursor/cli-config.json"
if cur_src.exists():
    c = json.loads(cur_src.read_text())
    for k in ("authInfo", "privacyCache", "autoReviewAvailabilityCache",
              "serverConfigCache", "modelSelectionHistory"):
        c.pop(k, None)
    write_json(FILES / "cursor/cli-config.json", c)

# --- manifest: marketplaces + plugins ---
known = json.loads((CLAUDE / "plugins/known_marketplaces.json").read_text())
installed = json.loads((CLAUDE / "plugins/installed_plugins.json").read_text())["plugins"]
active = json.loads((CLAUDE / "settings.personal.json").read_text()).get("enabledPlugins", {})

CLONES = {
    "workbits": "https://github.com/jluhrsen/workBits.git",
    "ai-helpers": "https://github.com/jluhrsen/ai-helpers.git",
    "local": "https://github.com/jluhrsen/pr-ci-dashboard.git",
}
github, directory = {}, {}
for name, info in known.items():
    src = info.get("source", {})
    if src.get("source") == "github":
        github[name] = src["repo"]
    elif src.get("source") == "directory":
        directory[name] = {
            "path": src["path"].replace(str(HOME), "$HOME"),
            "clone": CLONES.get(name, ""),
        }
# 'local' marketplace is referenced by an enabled plugin but no longer registered
if any(p.endswith("@local") for p in active) and "local" not in directory:
    directory["local"] = {
        "path": "$HOME/repos/RedHat/openshift/pr-ci-dashboard",
        "clone": CLONES["local"],
        "optional": True,
        "note": "not registered in known_marketplaces.json on the source machine and the "
                "repo ships only .claude-plugin/plugin.json, so 'marketplace add' may "
                "refuse it; the dashboard helpers are nice-to-have",
    }

plugins = []
for pid in sorted(installed):
    mkt = pid.split("@")[-1]
    optional = bool(directory.get(mkt, {}).get("optional"))
    plugins.append({
        "id": pid,
        "marketplace": mkt,
        "enabled": bool(active.get(pid, False)),
        "resolvable": mkt in github or mkt in directory,
        "optional": optional,
    })

manifest = {
    "version": 1,
    "generatedOn": subprocess.run(["date", "-I"], capture_output=True, text=True).stdout.strip(),
    "sourceHost": subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip(),
    "marketplaces": {"github": github, "directory": directory},
    "plugins": plugins,
    "files": {
        "files/claude/CLAUDE.md": "$HOME/.claude/CLAUDE.md",
        "files/claude/settings.personal.json": "$HOME/.claude/settings.personal.json",
        "files/claude/settings.work.json": "$HOME/.claude/settings.work.json",
        "files/claude/settings.local.json": "$HOME/.claude/settings.local.json",
        "files/claude/skills": "$HOME/.claude/skills",
        "files/config/claude-code-vertex/env.sh": "$HOME/.config/claude-code-vertex/env.sh",
        "files/zsh/aliases.zsh": "$HOME/.claude/aliases.zsh",
        "files/codex/config.toml": "$HOME/.codex/config.toml",
        "files/cursor/cli-config.json": "$HOME/.cursor/cli-config.json",
    },
    "mergeOnly": [
        "files/codex/config.toml",
        "files/cursor/cli-config.json",
    ],
    "secretsHandledOutOfBand": [
        "$HOME/.claude/settings.{personal,work}.json env.JIRA_API_TOKEN (placeholder, filled from $HOME/repos/workBits/jira_token)",
        "$HOME/repos/workBits/jira_token (gitignored)",
        "$HOME/.claude/google_client_secret.json",
        "$HOME/.claude/.credentials.json (re-login instead)",
        "$HOME/.codex/auth.json (re-login instead)",
        "$HOME/.config/gcloud/application_default_credentials.json (re-auth instead)",
    ],
    "notSynced": [
        "sessions/", "history.jsonl", "projects/*.jsonl", "file-history/",
        "shell-snapshots/", "telemetry/", "cache/", "plugins/cache/",
        "plugins/marketplaces/", "skills/synced/", ".caveman-* state",
        "projects/*/memory/ (internal notes; handed over out of band)",
    ],
}
write_json(SYNC / "manifest.json", manifest)

print("payload written:", SYNC)
print("skills:", sorted(p.name for p in skills_dst.iterdir()))
print("plugins:", len(plugins), "enabled:", sum(1 for p in plugins if p["enabled"]))
print("unresolvable:", [p["id"] for p in plugins if not p["resolvable"]])
