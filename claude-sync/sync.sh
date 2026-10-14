#!/usr/bin/env bash
# claude-sync: push local AI tooling config into this repo, or apply it locally.
#
#   ./claude-sync/sync.sh push    collect live config -> repo, scan, commit, push
#   ./claude-sync/sync.sh pull    git pull -> apply payload onto this machine
#
# Secrets are never collected: credential-shaped env keys are replaced with
# placeholders, and the Jira token is read at apply time from the gitignored
# file $HOME/repos/workBits/jira_token.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNC="$REPO/claude-sync"
MODE="${1:-}"

die() { echo "ERROR: $*" >&2; exit 1; }

# Refuse to commit anything credential-shaped, whatever the source.
scan_secrets() {
  local pattern='ATATT[0-9A-Za-z._-]{20,}|ghp_[0-9A-Za-z]{20,}|github_pat_[0-9A-Za-z_]{20,}|sk-[0-9A-Za-z]{20,}|AIza[0-9A-Za-z_-]{30,}|xox[abprs]-[0-9A-Za-z-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"client_secret"|"refresh_token"'
  if grep -rIEn --exclude-dir=.git --exclude=sync.sh "$pattern" "$SYNC" >/dev/null 2>&1; then
    echo "Secret-shaped content found in the payload:" >&2
    grep -rIEn --exclude-dir=.git --exclude=sync.sh -o "$pattern" "$SYNC" >&2
    die "refusing to commit - scrub it and retry"
  fi
  echo "  secret scan: clean"
  if command -v gitleaks >/dev/null 2>&1; then
    gitleaks detect --source "$SYNC" --no-git --redact --log-level error >/dev/null 2>&1 \
      && echo "  gitleaks: clean" || die "gitleaks flagged the payload - inspect before committing"
  fi
}

case "$MODE" in
push)
  command -v python3 >/dev/null || die "python3 required"
  echo "Collecting live config..."
  python3 -I "$SYNC/bin/collect.py"
  echo "Scanning..."
  scan_secrets
  cd "$REPO"
  git add claude-sync
  if git diff --cached --quiet -- claude-sync; then
    echo "No config changes to commit."
    exit 0
  fi
  git diff --cached --stat -- claude-sync
  git commit -q -m "claude-sync: refresh config payload from $(hostname) - $(date +%F)"
  git push origin HEAD
  echo "Pushed."
  ;;
pull)
  cd "$REPO"
  git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"
  python3 -I "$SYNC/bin/apply.py" "${2:-}"
  echo "Restart Claude Code to pick up settings changes."
  ;;
*)
  sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 1
  ;;
esac
