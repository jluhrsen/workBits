# Claude Code / AI tooling shell glue. Source this from ~/.zshrc:
#   [ -f "$HOME/.claude/aliases.zsh" ] && . "$HOME/.claude/aliases.zsh"

# Vertex AI env (personal GCP project). Credentials come from gcloud ADC,
# not from this file: gcloud auth application-default login
[ -f "$HOME/.config/claude-code-vertex/env.sh" ] && . "$HOME/.config/claude-code-vertex/env.sh"

# Work profile: Vertex-backed, telemetry + Jira env from settings.work.json
alias claude-work='claude --dangerously-skip-permissions --settings "$HOME/.claude/settings.work.json"'

# Personal profile: same config dir, Vertex vars blanked in settings.personal.json
alias claude-home='claude --dangerously-skip-permissions --settings "$HOME/.claude/settings.personal.json"'

# Fully separate config dir + claude.ai login (subscription account)
alias claude-personal='env -u CLAUDE_CODE_USE_VERTEX -u ANTHROPIC_VERTEX_PROJECT_ID -u CLOUD_ML_REGION CLAUDE_CONFIG_DIR="$HOME/.claude-personal" claude'
