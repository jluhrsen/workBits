#!/usr/bin/env bash
# One-shot setup of the Claude Code / Codex / Cursor environment on a new machine.
# Idempotent: safe to re-run. Reads claude-sync/manifest.json for the repo and
# plugin inventory. Secrets are never fetched from git - see SECRETS section at
# the end of the run for what still needs a human.
set -uo pipefail

SYNC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$SYNC/manifest.json"
DRY_RUN=0
SKIP_PLUGINS=0
FAILED=()

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --skip-plugins) SKIP_PLUGINS=1 ;;
    -h|--help) sed -n '2,6p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 1 ;;
  esac
done

say()  { printf '\n==> %s\n' "$*"; }
run()  { if [[ $DRY_RUN -eq 1 ]]; then echo "  [dry-run] $*"; else "$@"; fi; }
jqm()  { python3 -c "import json,sys;print(json.load(open('$MANIFEST'))$1)"; }

say "Preflight"
for tool in git python3 claude; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "  ok: $tool"
  else
    echo "  MISSING: $tool"
    [[ "$tool" == claude ]] && echo "    install: npm install -g @anthropic-ai/claude-code"
    exit 1
  fi
done
[[ -f "$MANIFEST" ]] || { echo "manifest not found: $MANIFEST" >&2; exit 1; }
echo "  manifest generated $(jqm "['generatedOn']") on $(jqm "['sourceHost']")"

say "Cloning repos that back directory marketplaces"
while IFS='|' read -r name path clone optional; do
  [[ -z "$name" ]] && continue
  dest="${path/\$HOME/$HOME}"
  if [[ -d "$dest/.git" ]]; then
    echo "  present: $name -> $dest"
  elif [[ -z "$clone" ]]; then
    echo "  SKIP: $name has no clone URL; create $dest by hand"
    FAILED+=("clone:$name")
  else
    echo "  cloning $name -> $dest"
    run mkdir -p "$(dirname "$dest")"
    if ! run git clone "$clone" "$dest"; then
      [[ -n "$optional" ]] && echo "    optional - continuing" || FAILED+=("clone:$name")
    fi
  fi
done < <(python3 -c "
import json
m=json.load(open('$MANIFEST'))['marketplaces']['directory']
for n,i in m.items():
    print('%s|%s|%s|%s' % (n, i['path'], i.get('clone',''), '1' if i.get('optional') else ''))
")

say "Registering marketplaces"
existing="$(claude plugin marketplace list 2>/dev/null || true)"
while IFS='|' read -r name source optional; do
  [[ -z "$name" ]] && continue
  src="${source/\$HOME/$HOME}"
  if grep -q "^\s*$name\b" <<<"$existing" || grep -q "\b$name\b" <<<"$existing"; then
    echo "  already added: $name"
    continue
  fi
  echo "  adding $name ($src)"
  if ! run claude plugin marketplace add "$src" --scope user; then
    [[ -n "$optional" ]] && echo "    optional - continuing" || FAILED+=("marketplace:$name")
  fi
done < <(python3 -c "
import json
m=json.load(open('$MANIFEST'))['marketplaces']
for n,r in m['github'].items(): print('%s|%s|' % (n, r))
for n,i in m['directory'].items():
    print('%s|%s|%s' % (n, i['path'], '1' if i.get('optional') else ''))
")

if [[ $SKIP_PLUGINS -eq 0 ]]; then
  say "Installing plugins (enabled on the source machine)"
  installed="$(claude plugin list 2>/dev/null || true)"
  while IFS='|' read -r pid optional; do
    [[ -z "$pid" ]] && continue
    if grep -q "$pid" <<<"$installed"; then
      echo "  already installed: $pid"
      continue
    fi
    echo "  installing $pid"
    if ! run claude plugin install "$pid" --scope user -y; then
      [[ -n "$optional" ]] && echo "    optional - continuing" || FAILED+=("plugin:$pid")
    fi
  done < <(python3 -c "
import json
for p in json.load(open('$MANIFEST'))['plugins']:
    if p['enabled'] and p['resolvable']:
        print('%s|%s' % (p['id'], '1' if p.get('optional') else ''))
")
else
  say "Skipping plugin install (--skip-plugins)"
fi

say "Applying config files"
if [[ $DRY_RUN -eq 1 ]]; then
  python3 -I "$SYNC/bin/apply.py" --dry-run
else
  python3 -I "$SYNC/bin/apply.py" || FAILED+=("apply")
fi

say "Shell glue"
zshrc="$HOME/.zshrc"
line='[ -f "$HOME/.claude/aliases.zsh" ] && . "$HOME/.claude/aliases.zsh"'
if [[ -f "$zshrc" ]] && grep -qF 'aliases.zsh' "$zshrc"; then
  echo "  already sourced from ~/.zshrc"
elif [[ $DRY_RUN -eq 1 ]]; then
  echo "  [dry-run] append to ~/.zshrc: $line"
else
  printf '\n# Claude Code aliases + Vertex env\n%s\n' "$line" >> "$zshrc"
  echo "  appended source line to ~/.zshrc"
fi

say "Secrets still needed (none of these live in git)"
token="$HOME/repos/workBits/jira_token"
if [[ -s "$token" ]]; then
  echo "  ok: $token present"
else
  echo "  MISSING: $token"
  echo "    paste the Red Hat Atlassian API token from your handoff file, then re-run:"
  echo "    python3 -I $SYNC/bin/apply.py"
fi
[[ -f "$HOME/.claude/google_client_secret.json" ]] \
  && echo "  ok: ~/.claude/google_client_secret.json present" \
  || echo "  MISSING: ~/.claude/google_client_secret.json (copy from handoff file)"

say "Manual steps left"
cat <<'MANUAL'
  1. claude  ->  /login            (Claude Code auth; ~/.claude/.credentials.json is per-machine)
  2. gcloud auth application-default login --project itpc-ca-3aa18a6935   (Vertex path)
  3. codex   ->  sign in           (~/.codex/auth.json is per-machine)
  4. cursor-agent login            (if you use the Cursor CLI)
  5. Verify Jira auth: start Claude Code and run /jira, or check for HTTP 200 from
     GET https://redhat.atlassian.net/rest/api/3/myself with basic auth
     (JIRA_USERNAME:JIRA_API_TOKEN)
MANUAL

if ((${#FAILED[@]})); then
  say "Finished with problems"
  printf '  failed: %s\n' "${FAILED[@]}"
  exit 1
fi
say "Bootstrap complete - restart your shell, then start Claude with: claude-work"
