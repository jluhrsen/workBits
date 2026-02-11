# Claude Code Continuum (CCC) - Design Document

**Date:** 2026-02-10
**Status:** Approved
**Project Tagline:** Your sandboxed Claude Code environment—pause anywhere, resume everywhere from your private git repo.

## Overview

Claude Code Continuum (CCC) is a containerized Claude Code environment that enables seamless session continuity across any machine. The core innovation is **pause anywhere, resume everywhere** - you can stop work mid-debugging session on one laptop and pick up exactly where you left off on another, with full workspace state including uncommitted code changes, conversation history, and accumulated knowledge.

### Key Differentiators

Unlike existing solutions (ClaudeBox, claude-container, Docker Sandboxes, super-claude-kit, Claude-Mem), CCC uniquely solves the **cross-machine portability problem**. No other solution handles the "coffee shop laptop → desktop → work laptop" workflow with full workspace state (uncommitted code + conversation + learned knowledge).

## Architecture

### Core Components

1. **Container Layer:** UBI9-based Docker image (`quay.io/jluhrsen/claude-code-continuum`)
2. **Wrapper Script:** `ccc` command that handles Docker complexity
3. **Continuum Repository:** Private git repo for sessions, knowledge, and configuration
4. **Security Model:** Sandboxed filesystem access with scoped credentials

### Key Design Principle

Git provides the backbone for everything - session versioning, time-travel debugging, cross-machine sync, and conflict resolution. We leverage existing git infrastructure (GitHub/GitLab) rather than building custom sync mechanisms.

## Component Details

### 1. Docker Image

**Base:** Red Hat UBI9 (`registry.access.redhat.com/ubi9/ubi`)

**Pre-installed Tools:**
- Claude Code CLI with superpowers plugin
- Development: golang (latest), make, golangci-lint
- OpenShift/K8s: oc, kubectl, gh CLI
- Shell: zsh with oh-my-zsh, Powerlevel10k theme
- Editor: vim with sensible defaults
- Git for workspace and continuum operations

**Configuration:**
- Sanitized .zshrc baked in (based on user's current one, host-specific bits removed)
- Entrypoint: Session manager that shows banner → syncs continuum → presents session picker

### 2. Wrapper Script (`ccc`)

**Responsibilities:**
- Auto-detects and mounts Claude authentication (`~/.claude/`, `~/.config/gcloud/`)
- Mounts current working directory as `/workspace` (read-write)
- Whitelists `/tmp` for additional clones
- Mounts continuum deploy key (`~/.ssh/continuum_deploy_key`)
- Passes through Claude-related env vars (CLAUDE_CODE_USE_VERTEX, etc.)
- Validates setup before starting container
- Forwards all arguments to containerized Claude

**Validation Logic:**
- If `CONTINUUM_REPO_URL` is set, verify deploy key exists
- Fail fast with helpful setup instructions if incomplete

### 3. Continuum Repository Structure

```
claude-continuum-private/
├── sessions/
│   └── session-abc123/
│       ├── metadata.json          # timestamp, repo, branch, working dir
│       ├── conversation.json      # full chat history
│       ├── snapshot.patch         # git diff of uncommitted changes
│       └── wip-branch             # temp branch name with unpushed commits
├── knowledge/
│   ├── openshift-ci.md           # Prow, CI/CD workflows
│   ├── kubernetes.md             # OVN/networking patterns
│   ├── jira.md                   # Bug tracking workflows
│   ├── golang-patterns.md        # Go-specific learnings
│   └── git-workflows.md          # Universal git patterns
└── config/
    ├── blocklist.txt             # Commands requiring approval
    └── auto-load-rules.yaml      # Which knowledge loads for which repos
```

## Core Workflows

### First-Time Setup

1. User creates private git repo (e.g., `github.com/jluhrsen/claude-continuum-private`)
2. User creates GitHub deploy key with read-write access to that repo
3. User saves deploy key to `~/.ssh/continuum_deploy_key`
4. User sets env vars (add to ~/.zshrc):
   ```bash
   export CONTINUUM_REPO_URL=git@github.com:jluhrsen/claude-continuum-private.git
   ```
5. User runs `ccc` → container initializes continuum repo with default structure

### Starting a Session

```bash
$ cd ~/repos/ovn-kubernetes
$ ccc

🌌 Claude Code Continuum
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  READ/WRITE ACCESS: /home/you/repos/ovn-kubernetes (and below)
⚠️  Whitelisted: /tmp
⚠️  Continuum repo: git@github.com:jluhrsen/claude-continuum-private.git
ℹ️  Claude account: Vertex AI (itpc-gcp-hybrid-pe-eng-claude)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 Syncing from private repo...

Available sessions:
  1. [2h ago] Debugging OVN CI failure (ovn-kubernetes/)
  2. [1d ago] CNO investigation (cluster-network-operator/)
  3. [3d ago] Prow job analysis (ovn-kubernetes/)
  n. Start new session

Select [1-3/n]: 1

🔄 Restoring session state...
  ✓ Branch: feature/ovn-debug
  ✓ Applied 3 uncommitted files
  ✓ Restored 2 unpushed commits

📚 Auto-loading knowledge:
  ✓ openshift-ci.md (Prow workflows, artifact hunting)
  ✓ kubernetes.md (OVN/networking patterns)
  ✓ jira.md (Bug tracking workflows)
  ✓ golang-patterns.md (Go best practices)

Morning! We were debugging that OVN CI failure. Last we checked,
the pod logs showed a timeout in the webhook service...
```

### The "nightnight" Command

```
you> /nightnight

📸 Creating snapshot...
  ✓ Saved conversation (247 messages)
  ✓ Captured git state: feature/ovn-debug
  ✓ Stashed 3 uncommitted files
  ✓ Pushed wip branch: claude-wip/session-abc123
  ✓ Committed to continuum repo
  ✓ Pushed to private repo

Sweet dreams! Resume with: ccc
```

## Advanced Features

### Auto-Learning with `/remember`

When Claude detects a useful pattern or user explicitly captures:

```
you> To check prow jobs, use: gh api repos/openshift/ovn-kubernetes/pulls/1234/checks

claude> 🧠 That looks like a useful pattern. Remember this?

you> yes

claude> Which category should I add this to?
  1. openshift-ci.md (Prow, CI/CD workflows)
  2. kubernetes.md (K8s/OVN patterns)
  3. jira.md (Bug tracking)
  4. Create new category...

you> 1

claude> Which repos should auto-load openshift-ci.md?
  Currently: ovn-kubernetes, cluster-network-operator
  [enter repo names, "all", or "keep current"]

you> keep current

claude> ✓ Added to openshift-ci.md
        ✓ Committed to continuum repo
        ✓ Will auto-load in: ovn-kubernetes, cluster-network-operator
```

**Implementation:**
- PostToolUse hook watches for repeated commands/patterns
- Conversational workflow to categorize and scope
- Also supports explicit `/remember <topic>` command

### Session Time-Travel

If you go down a wrong debugging path:

```
you> That last session went nowhere. Can we rewind?

claude> I can restore to these checkpoints:
  1. [2h ago] Coffee shop session - wrong theory about webhooks
  2. [1d ago] Initial analysis - identified pod timeout

  Which checkpoint? [1-2]

you> 2

claude> 🔄 Rewinding to checkpoint 2 (1d ago)...
  ✓ Restored conversation state
  ✓ Restored workspace: feature/ovn-debug @ commit abc1234

  Back to where we identified the pod timeout. Let's try a different approach...
```

**Implementation:**
- Each `/nightnight` creates a git commit in the continuum repo
- Rewind = checkout previous commit of the session folder
- Conversation history and workspace state both restored

### Command Blocklist with Learning

When Claude hits a blocked command:

```
claude> I'm going to run: sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT

⚠️  BLOCKED COMMAND: sudo
This command requires approval.
Allow? [y/n/always]: y

Command executed.
Remember this approval? [y/n]: n
```

**Initial Blocklist:**
- `rm -rf`
- `dd`
- `mkfs.*`
- `iptables` / `nftables`
- `sudo`
- `chmod` / `chown`
- `curl|bash` / `wget|bash`
- `systemctl`

**Behavior:**
- "y" = Allow once
- "always" = Remove from blocklist permanently
- "n" = Block execution

## Security & Isolation

### Filesystem Isolation

**Read-Write Access:**
- Current working directory (where `ccc` was launched)
- `/tmp` (whitelisted)

**Read-Only Mounts:**
- `~/.claude/` (Claude config/auth)
- `~/.config/gcloud/` (GCP credentials for Vertex AI)
- `~/.ssh/continuum_deploy_key` (single-purpose deploy key)

### Credential Isolation

**What Claude CAN access:**
- Continuum repo (via deploy key)
- Your GCP Vertex AI project (same risk as using Claude locally)
- Current working directory (read-write)
- /tmp (read-write)

**What Claude CANNOT access:**
- Your other GitHub repos
- Your SSH keys for other services
- Your broader filesystem
- gh CLI with full GitHub access

**Key Security Decisions:**
- Deploy key grants access ONLY to continuum repo
- No mounting of `~/.config/gh/` (full GitHub access not needed)
- Credentials mounted read-only (cannot be modified by container)
- Worst-case blast radius: Only continuum repo + current working directory

### Lessons from "My agent stole my API keys" Reddit Post

**Problem:** Goal-oriented AI will creatively bypass restrictions. Blocklists are speed bumps, not walls.

**Our Mitigations:**
1. **Scoped credentials:** Deploy key limits to one repo only
2. **Clear disclosure:** Startup banner shows exactly what Claude can access
3. **Minimal mounts:** Only mount what's absolutely necessary
4. **Accept calculated risks:** GCP/Vertex access is same risk as local Claude usage

### Network

- No additional network restrictions (relies on Docker defaults)
- Container can reach: GitHub, quay.io, package repos, OpenShift clusters, etc.
- Future enhancement: Optional firewall allowlist (à la ClaudeBox)

## Skills & Custom Commands

### Built-in CCC Skills

**`/nightnight`**
- Captures current session state (conversation, git branch, uncommitted changes, unpushed commits)
- Pushes wip branch to remote if needed
- Commits snapshot to continuum repo
- Syncs to private git repo

**`/remember [category]`**
- Explicitly captures last exchange or detected pattern
- Prompts for category (openshift-ci.md, jira.md, etc.)
- Asks which repos should auto-load this knowledge
- Commits to continuum repo

**`/set_ccc_repo <url>`**
- Sets continuum repo URL if you forgot to set env var
- Initializes repo structure if first time
- Useful for recovering from missing CONTINUUM_REPO_URL

### Session Management

- **Time-travel:** "Can we rewind?" → shows checkpoint list
- **Session picker:** On startup, shows all available sessions
- **Cross-repo awareness:** Warns if session expects different directory

## Implementation Priorities

### Phase 1: Core Infrastructure
1. Dockerfile with UBI9 + tools
2. Wrapper script (`ccc`) with validation
3. Session manager entrypoint
4. GitHub Actions → quay.io automation

### Phase 2: Session Management
1. Session creation and storage
2. `/nightnight` skill implementation
3. Session restore logic
4. Workspace snapshot/restore (git patches, wip branches)

### Phase 3: Security & Isolation
1. Command blocklist implementation
2. Approval prompt system
3. Startup banner with permission disclosure
4. Deploy key validation

### Phase 4: Knowledge Management
1. Auto-load rules engine
2. `/remember` skill
3. PostToolUse hook for pattern detection
4. Knowledge categorization system

### Phase 5: Advanced Features
1. Session time-travel
2. `/set_ccc_repo` command
3. Session metadata and search
4. Cross-machine sync optimization

## Testing Strategy

### Priority: Security Tests

1. **Filesystem isolation tests**
   - Verify writes outside CWD are blocked
   - Verify /tmp access works
   - Verify parent directory access fails

2. **Credential isolation tests**
   - Verify deploy key only accesses continuum repo
   - Verify no access to ~/.ssh/ directory
   - Verify no access to ~/.config/gh/

3. **Command blocklist tests**
   - Verify blocked commands trigger approval prompts
   - Verify approval workflow
   - Verify "always" removes from blocklist

### Functional Tests

1. **Wrapper script tests**
   - Validation logic (missing deploy key, missing env var)
   - Mount detection and passthrough
   - Environment variable forwarding

2. **Session management tests**
   - Session creation
   - Session restore
   - Workspace snapshot accuracy

3. **Knowledge management tests**
   - Auto-load rules matching
   - Knowledge file updates
   - Continuum repo commits

### Integration Tests

1. End-to-end nightnight → resume flow
2. Cross-machine simulation (different containers)
3. Git conflict handling

## Success Criteria

1. User can run `ccc` and immediately work with Claude
2. `/nightnight` on machine 1 → resume on machine 2 works seamlessly
3. Uncommitted code changes survive the transition
4. Learned knowledge auto-loads in appropriate contexts
5. Security boundaries are clearly communicated and enforced
6. No credential leaks outside intended scope

## Future Enhancements

1. Firewall allowlist (à la ClaudeBox)
2. UID/GID matching for file permissions
3. Session search and filtering
4. Semantic search for knowledge (vector DB)
5. Multi-user team shared knowledge bases
6. Session export/import for collaboration
7. Integration with company-specific MCP servers
