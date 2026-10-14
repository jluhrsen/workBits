# New-laptop bootstrap prompt

Paste everything below the line into Claude Code (or any coding agent with
shell access) on the new machine. It is self-contained.

---

I just got this laptop and I want my Claude Code / Codex / Cursor setup to
match my other machine. The portable configuration lives in my GitHub repo
`https://github.com/jluhrsen/workBits` under `claude-sync/`, which has a
manifest, a config payload, and a bootstrap script. Please get me running.

Do this:

1. **Check prerequisites.** I need `git`, `python3`, and the Claude Code CLI
   (`claude`). If `claude` is missing, install it with
   `npm install -g @anthropic-ai/claude-code` and tell me if Node is missing too.
   `gh`, `jq` and `gcloud` are useful but not required by the script.

2. **Clone the config repo to the exact path the manifest expects:**
   `git clone https://github.com/jluhrsen/workBits.git ~/repos/workBits`
   The path matters - two of my plugin marketplaces are directory marketplaces
   that point at `$HOME/repos/workBits` and `$HOME/repos/RedHat/openshift/ai-helpers`.

3. **Read `~/repos/workBits/claude-sync/README.md` and `manifest.json`** so you
   know what is about to be installed, then show me a one-screen summary:
   how many plugins, which marketplaces, which files will be written, and
   anything marked optional.

4. **Preview, then run the bootstrap:**
   `~/repos/workBits/claude-sync/bootstrap.sh --dry-run`
   then, if it looks sane, `~/repos/workBits/claude-sync/bootstrap.sh`
   It is idempotent, so re-running after a fix is fine. It clones the repos
   behind the directory marketplaces, registers 6 marketplaces, installs ~44
   plugins, copies my settings/skills/shell glue into place (backing up
   anything it replaces), and appends one `source` line to `~/.zshrc`.
   The `local` marketplace and its `pr-ci-dashboard` plugin are optional - if
   they fail, note it and keep going.

5. **Install my secrets from the handoff file.** No credential is in git. I
   have a file called `claude-new-laptop-handoff/SECRETS.txt` that I moved over
   separately - ask me for its location, read it, and then:
   - write the Red Hat Atlassian API token to `~/repos/workBits/jira_token`
     (no trailing newline issues - the script strips whitespace), `chmod 600`
   - write the Google OAuth client secret JSON to
     `~/.claude/google_client_secret.json`, `chmod 600`
   - re-run `python3 -I ~/repos/workBits/claude-sync/bin/apply.py` so the
     `JIRA_API_TOKEN` placeholder in `~/.claude/settings.{personal,work}.json`
     gets filled from the token file
   Never commit any of these or echo them into a file inside a git repo.

6. **Restore my memory files** if the handoff bundle includes a `memory/`
   directory: each subdirectory maps to `~/.claude/projects/<same-name>/memory/`.
   Create the project directories as needed and copy the `.md` files in.

7. **Walk me through the logins you cannot do for me**, one command per line:
   - `claude` then `/login` (Claude Code auth)
   - `gcloud auth application-default login --project itpc-ca-3aa18a6935`
     for the Vertex path, if I say I want Vertex on this machine
   - `codex` sign-in, and `cursor-agent login` if I use the Cursor CLI

8. **Verify and report.** Confirm: `claude plugin list` count close to the
   manifest's enabled count; `~/.claude/CLAUDE.md`, `settings.personal.json`,
   `settings.work.json`, `settings.local.json`, `aliases.zsh` all present;
   `grep -c FROM_FILE ~/.claude/settings.*.json` returns 0 matches (token
   filled); a `GET https://redhat.atlassian.net/rest/api/3/myself` with basic
   auth `jluhrsen@redhat.com:<token>` returns HTTP 200. Then tell me to restart
   my shell and start Claude with `claude-work` (Vertex/work profile) or
   `claude-home` (personal profile).

Constraints: give me any command I have to run myself as a single line with no
newlines or indentation, under 120 characters. Do not put secrets in shell
history-visible arguments if you can write them with a file redirect instead.
Tell me plainly about anything that failed rather than working around it
silently.
