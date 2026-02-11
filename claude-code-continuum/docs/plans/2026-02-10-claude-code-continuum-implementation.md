# Claude Code Continuum Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a containerized Claude Code environment with cross-machine session continuity via git-backed persistence.

**Architecture:** UBI9 Docker image with pre-installed dev tools, bash wrapper for setup/validation, Python session manager for continuum sync/restore, and Claude skills for snapshot/knowledge management.

**Tech Stack:** Docker (UBI9), Bash (wrapper), Python 3.11+ (session manager), Git (persistence), GitHub Actions (CI/CD)

---

## Phase 1: Core Infrastructure

### Task 1.1: Project Structure & Basic Files

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `LICENSE`

**Step 1: Create README with project overview**

```markdown
# Claude Code Continuum (CCC)

Your sandboxed Claude Code environment—pause anywhere, resume everywhere from your private git repo.

## Quick Start

```bash
# Set up continuum repo
export CONTINUUM_REPO_URL=git@github.com:yourusername/claude-continuum-private.git

# Create deploy key
ssh-keygen -t ed25519 -f ~/.ssh/continuum_deploy_key
# Add public key to your GitHub repo settings

# Pull and run
docker pull quay.io/jluhrsen/claude-code-continuum:latest
./ccc
```

## Features

- 🌌 Cross-machine session continuity
- 🛌 Effortless snapshots with `/nightnight`
- 🧠 Auto-learning knowledge base
- 🔒 Scoped security with deploy keys
- 📦 Zero-friction Docker wrapper

## Documentation

See [Design Document](docs/plans/2026-02-10-claude-code-continuum-design.md) for architecture details.

## License

MIT License - see LICENSE file.
```

**Step 2: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# Docker
*.tar

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Secrets
*.key
*.pem
continuum_deploy_key*

# Testing
.pytest_cache/
.coverage
htmlcov/
```

**Step 3: Copy LICENSE from workBits root**

```bash
cp ../LICENSE .
```

**Step 4: Commit**

```bash
git add README.md .gitignore LICENSE
git commit -m "chore: initialize project structure

Add README, gitignore, and MIT license

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 1.2: Wrapper Script Foundation

**Files:**
- Create: `ccc`
- Create: `tests/test_ccc_wrapper.bats`

**Step 1: Write failing test for wrapper validation**

Create `tests/test_ccc_wrapper.bats`:

```bash
#!/usr/bin/env bats

setup() {
    export TEST_HOME="/tmp/ccc-test-$$"
    mkdir -p "$TEST_HOME"
    export CONTINUUM_REPO_URL=""
}

teardown() {
    rm -rf "$TEST_HOME"
}

@test "ccc fails when CONTINUUM_REPO_URL set but no deploy key" {
    export CONTINUUM_REPO_URL="git@github.com:test/repo.git"
    export HOME="$TEST_HOME"

    run ./ccc --version

    [ "$status" -eq 1 ]
    [[ "$output" =~ "deploy key not found" ]]
}

@test "ccc runs without CONTINUUM_REPO_URL (local mode)" {
    export HOME="$TEST_HOME"

    # Mock docker to just echo
    function docker() { echo "docker called: $@"; }
    export -f docker

    run ./ccc --help

    [ "$status" -eq 0 ]
}
```

**Step 2: Run test to verify it fails**

Run: `bats tests/test_ccc_wrapper.bats`
Expected: FAIL with "ccc: command not found" or similar

**Step 3: Write minimal wrapper implementation**

Create `ccc`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# CCC - Claude Code Continuum Wrapper
# Manages Docker setup, credential mounting, and validation

VERSION="0.1.0"
CONTAINER_IMAGE="${CCC_IMAGE:-quay.io/jluhrsen/claude-code-continuum:latest}"
CONTAINER_USER="claude"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

info() {
    echo -e "${GREEN}✓ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Validate setup before running
validate_setup() {
    # Check if continuum repo is configured
    if [[ -n "${CONTINUUM_REPO_URL:-}" ]]; then
        # User wants cloud sync, check for deploy key
        KEY_FILE="${CONTINUUM_KEY_PATH:-$HOME/.ssh/continuum_deploy_key}"

        if [[ ! -f "$KEY_FILE" ]]; then
            error "CONTINUUM_REPO_URL is set but deploy key not found!"
            echo ""
            echo "Setup instructions:"
            echo "  1. Create deploy key: ssh-keygen -t ed25519 -f ~/.ssh/continuum_deploy_key"
            echo "  2. Add public key (~/.ssh/continuum_deploy_key.pub) to GitHub repo settings"
            echo "  3. Run ccc again"
            echo ""
            echo "Alternatively, unset CONTINUUM_REPO_URL to use local-only mode."
            return 1
        fi

        info "Deploy key found: $KEY_FILE"
    else
        warn "CONTINUUM_REPO_URL not set - running in local-only mode"
        warn "Sessions will not sync across machines"
    fi

    return 0
}

# Build Docker run command with appropriate mounts
build_docker_cmd() {
    local docker_args=()

    # Basic container setup
    docker_args+=(--rm -it)
    docker_args+=(--name "ccc-$$")

    # Mount current directory as /workspace (read-write)
    docker_args+=(-v "$(pwd):/workspace")
    docker_args+=(-w /workspace)

    # Whitelist /tmp
    docker_args+=(-v /tmp:/tmp)

    # Mount Claude authentication (read-only)
    if [[ -d "$HOME/.claude" ]]; then
        docker_args+=(-v "$HOME/.claude:/home/$CONTAINER_USER/.claude:ro")
    fi

    # Mount GCP credentials for Vertex AI (read-only)
    if [[ -d "$HOME/.config/gcloud" ]]; then
        docker_args+=(-v "$HOME/.config/gcloud:/home/$CONTAINER_USER/.config/gcloud:ro")
    fi

    # Mount continuum deploy key if configured (read-only)
    if [[ -n "${CONTINUUM_REPO_URL:-}" ]]; then
        KEY_FILE="${CONTINUUM_KEY_PATH:-$HOME/.ssh/continuum_deploy_key}"
        docker_args+=(-v "$KEY_FILE:/home/$CONTAINER_USER/.ssh/continuum_key:ro")
    fi

    # Pass through Claude-related env vars
    [[ -n "${CLAUDE_CODE_USE_VERTEX:-}" ]] && docker_args+=(-e CLAUDE_CODE_USE_VERTEX)
    [[ -n "${GCP_ID:-}" ]] && docker_args+=(-e GCP_ID)
    [[ -n "${CLOUD_ML_REGION:-}" ]] && docker_args+=(-e CLOUD_ML_REGION)
    [[ -n "${ANTHROPIC_API_KEY:-}" ]] && docker_args+=(-e ANTHROPIC_API_KEY)
    [[ -n "${ANTHROPIC_VERTEX_PROJECT_ID:-}" ]] && docker_args+=(-e ANTHROPIC_VERTEX_PROJECT_ID)

    # Pass through continuum repo URL
    [[ -n "${CONTINUUM_REPO_URL:-}" ]] && docker_args+=(-e CONTINUUM_REPO_URL)

    echo "${docker_args[@]}"
}

# Main execution
main() {
    # Handle --version flag
    if [[ "${1:-}" == "--version" ]]; then
        echo "ccc version $VERSION"
        exit 0
    fi

    # Handle --help flag
    if [[ "${1:-}" == "--help" ]]; then
        cat <<EOF
ccc - Claude Code Continuum

Usage: ccc [claude-options]

Environment Variables:
  CONTINUUM_REPO_URL        Git URL for session storage (optional)
  CONTINUUM_KEY_PATH        Path to deploy key (default: ~/.ssh/continuum_deploy_key)
  CCC_IMAGE                 Container image (default: quay.io/jluhrsen/claude-code-continuum:latest)
  CLAUDE_CODE_USE_VERTEX    Use Vertex AI (optional)
  GCP_ID                    GCP project ID (optional)
  CLOUD_ML_REGION           GCP region (optional)

Examples:
  ccc                                          # Start interactive session picker
  ccc --dangerously-skip-permissions -r        # Resume last session with auto-approve

For more info: https://github.com/jluhrsen/workBits/tree/main/claude-code-continuum
EOF
        exit 0
    fi

    # Validate setup
    if ! validate_setup; then
        exit 1
    fi

    # Build docker command
    local docker_args
    read -ra docker_args <<< "$(build_docker_cmd)"

    # Run container
    exec docker run "${docker_args[@]}" "$CONTAINER_IMAGE" "$@"
}

main "$@"
```

**Step 4: Make wrapper executable**

```bash
chmod +x ccc
```

**Step 5: Run tests to verify they pass**

Run: `bats tests/test_ccc_wrapper.bats`
Expected: PASS (2 tests)

**Step 6: Commit**

```bash
git add ccc tests/test_ccc_wrapper.bats
git commit -m "feat: add ccc wrapper script with validation

- Validates deploy key when CONTINUUM_REPO_URL is set
- Auto-mounts Claude/GCP credentials
- Passes through environment variables
- Includes basic tests for validation logic

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 1.3: Dockerfile - Base Image & System Packages

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

**Step 1: Create .dockerignore**

```
.git
.github
tests/
docs/
README.md
*.md
.gitignore
venv/
__pycache__/
*.pyc
.pytest_cache/
```

**Step 2: Write Dockerfile base layer**

Create `Dockerfile`:

```dockerfile
# Claude Code Continuum
# Containerized Claude Code environment with cross-machine session continuity

FROM registry.access.redhat.com/ubi9/ubi:latest

LABEL maintainer="jluhrsen"
LABEL description="Claude Code Continuum - pause anywhere, resume everywhere"
LABEL version="0.1.0"

# Create non-root user
ARG USER_NAME=claude
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID $USER_NAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USER_NAME

# Install system packages
RUN dnf install -y \
    git \
    vim \
    zsh \
    curl \
    wget \
    make \
    gcc \
    gcc-c++ \
    tar \
    gzip \
    unzip \
    && dnf clean all

# Install Node.js (required for Claude Code CLI)
RUN curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - && \
    dnf install -y nodejs && \
    dnf clean all

# Switch to non-root user
USER $USER_NAME
WORKDIR /home/$USER_NAME

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Set up basic shell
ENV SHELL=/usr/bin/zsh
SHELL ["/usr/bin/zsh", "-c"]

CMD ["/usr/bin/zsh"]
```

**Step 3: Build Docker image to verify base works**

Run: `docker build -t ccc-test:base .`
Expected: Successful build

**Step 4: Test basic functionality**

Run: `docker run --rm ccc-test:base claude --version`
Expected: Output showing Claude Code version

**Step 5: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: add Dockerfile with UBI9 base and Claude CLI

- UBI9 base image
- Non-root claude user
- Node.js 20 and Claude Code CLI
- Basic system packages (git, vim, zsh)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 1.4: Dockerfile - Development Tools (Go, Make, etc.)

**Files:**
- Modify: `Dockerfile`

**Step 1: Add Go installation to Dockerfile**

Add before the USER switch:

```dockerfile
# Install Go (latest stable)
ARG GO_VERSION=1.22.0
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o go.tar.gz && \
    tar -C /usr/local -xzf go.tar.gz && \
    rm go.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/home/${USER_NAME}/go"
ENV PATH="${GOPATH}/bin:${PATH}"
```

**Step 2: Add golangci-lint installation**

Add after USER switch:

```dockerfile
# Install golangci-lint
RUN curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin
```

**Step 3: Add OpenShift/Kubernetes CLI tools**

Add after golangci-lint:

```dockerfile
# Install oc (OpenShift CLI)
RUN curl -fsSL "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/openshift-client-linux.tar.gz" -o oc.tar.gz && \
    tar -xzf oc.tar.gz -C /tmp && \
    sudo mv /tmp/oc /usr/local/bin/ && \
    sudo mv /tmp/kubectl /usr/local/bin/ && \
    rm oc.tar.gz

# Install gh CLI
RUN curl -fsSL "https://cli.github.com/packages/rpm/gh-cli.repo" | sudo tee /etc/yum.repos.d/gh-cli.repo && \
    sudo dnf install -y gh && \
    sudo dnf clean all
```

**Step 4: Build and test**

Run: `docker build -t ccc-test:tools .`
Expected: Successful build

Run: `docker run --rm ccc-test:tools go version`
Expected: Go version output

Run: `docker run --rm ccc-test:tools golangci-lint --version`
Expected: golangci-lint version output

Run: `docker run --rm ccc-test:tools oc version --client`
Expected: oc client version

**Step 5: Commit**

```bash
git add Dockerfile
git commit -m "feat: add development tools to Dockerfile

- Go 1.22.0
- golangci-lint
- oc/kubectl (OpenShift/K8s CLI)
- gh CLI

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 1.5: Sanitized .zshrc Configuration

**Files:**
- Create: `container-files/.zshrc`
- Modify: `Dockerfile`

**Step 1: Create sanitized .zshrc**

Create `container-files/.zshrc`:

```bash
# Claude Code Continuum - Container .zshrc
# Sanitized version for containerized environment

# Path to oh-my-zsh installation
export ZSH="/home/claude/.oh-my-zsh"

# Theme
ZSH_THEME="powerlevel10k/powerlevel10k"

# History settings
setopt inc_append_history
setopt share_history

# Plugins (removed macOS/brew specific)
plugins=(git colored-man-pages colorize pip python zsh-syntax-highlighting zsh-autosuggestions)

source $ZSH/oh-my-zsh.sh

# Editor
export EDITOR='vim'

# Useful aliases
alias du='dust'
alias find='fd'
alias h='history 1'
alias rgh='history 1 | rg'

# Git aliases
alias grr='git review --reviewers'
alias grm='git rebase master'
alias grum='git rebase upstream/master'
alias gfum='git fetch upstream && git merge upstream/master'

# Git functions
unalias gfa 2>/dev/null || true
gfa() {
  git fetch --all --prune
  for b in master release-4.21 release-4.20 release-4.19 release-4.18 release-4.17 release-4.16; do
    git checkout "$b" &&
    git reset --hard "upstream/$b" &&
    git push origin "$b"
  done
}

# Go environment
export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin
export PATH=$PATH:/usr/local/go/bin

# Tab completion
autoload -Uz compinit && compinit

# Paste optimization for zsh-autosuggestions
pasteinit() {
  OLD_SELF_INSERT=${${(s.:.)widgets[self-insert]}[2,3]}
  zle -N self-insert url-quote-magic
}

pastefinish() {
  zle -N self-insert $OLD_SELF_INSERT
}
zstyle :bracketed-paste-magic paste-init pasteinit
zstyle :bracketed-paste-magic paste-finish pastefinish
```

**Step 2: Update Dockerfile to install oh-my-zsh and copy .zshrc**

Add after USER switch and before npm install:

```dockerfile
# Install oh-my-zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# Install Powerlevel10k theme
RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k

# Install zsh plugins
RUN git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting && \
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

# Copy sanitized .zshrc
COPY --chown=$USER_NAME:$USER_NAME container-files/.zshrc /home/$USER_NAME/.zshrc
```

**Step 3: Build and test**

Run: `docker build -t ccc-test:zsh .`
Expected: Successful build

Run: `docker run --rm -it ccc-test:zsh zsh -c "echo \$SHELL && alias | head -5"`
Expected: Shows /usr/bin/zsh and aliases

**Step 4: Commit**

```bash
git add container-files/.zshrc Dockerfile
git commit -m "feat: add sanitized .zshrc with oh-my-zsh

- oh-my-zsh with Powerlevel10k theme
- Syntax highlighting and autosuggestions
- Git aliases and functions
- Optimized for container environment

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 1.6: Session Manager Entrypoint (Python)

**Files:**
- Create: `container-files/session_manager.py`
- Create: `tests/test_session_manager.py`
- Modify: `Dockerfile`

**Step 1: Write failing test for session manager banner**

Create `tests/test_session_manager.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Add container-files to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'container-files'))

from session_manager import SessionManager

def test_banner_shows_workspace_path():
    """Test that banner displays current workspace path"""
    with patch.dict(os.environ, {'CONTINUUM_REPO_URL': ''}):
        manager = SessionManager()
        banner = manager.generate_banner('/workspace/test-repo')

        assert '/workspace/test-repo' in banner
        assert 'READ/WRITE ACCESS' in banner

def test_banner_shows_continuum_repo_when_set():
    """Test that banner shows continuum repo URL when configured"""
    test_url = 'git@github.com:test/continuum.git'
    with patch.dict(os.environ, {'CONTINUUM_REPO_URL': test_url}):
        manager = SessionManager()
        banner = manager.generate_banner('/workspace')

        assert test_url in banner

def test_banner_shows_local_mode_when_no_repo():
    """Test that banner shows local-only mode when no repo configured"""
    with patch.dict(os.environ, {'CONTINUUM_REPO_URL': ''}):
        manager = SessionManager()
        banner = manager.generate_banner('/workspace')

        assert 'local only' in banner.lower() or 'CONTINUUM_REPO_URL not set' in banner
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_manager.py -v`
Expected: FAIL with "No module named 'session_manager'"

**Step 3: Write minimal session manager implementation**

Create `container-files/session_manager.py`:

```python
#!/usr/bin/env python3
"""
Claude Code Continuum - Session Manager

Handles session listing, restoration, and continuum repo sync.
"""

import os
import sys
from pathlib import Path
from typing import Optional

class SessionManager:
    """Manages CCC sessions and continuum repository synchronization"""

    def __init__(self):
        self.continuum_repo_url = os.environ.get('CONTINUUM_REPO_URL', '')
        self.workspace_path = Path('/workspace')
        self.continuum_path = Path.home() / '.continuum'

        # Detect Claude account info
        self.claude_account = self._detect_claude_account()

    def _detect_claude_account(self) -> str:
        """Detect which Claude account/auth method is being used"""
        if os.environ.get('CLAUDE_CODE_USE_VERTEX'):
            gcp_id = os.environ.get('GCP_ID', 'unknown')
            return f"Vertex AI ({gcp_id})"
        elif os.environ.get('ANTHROPIC_API_KEY'):
            return "Anthropic API (direct)"
        else:
            return "Unknown"

    def generate_banner(self, workspace_path: str) -> str:
        """Generate startup banner with permissions and configuration"""
        lines = [
            "🌌 Claude Code Continuum",
            "━" * 60,
            f"⚠️  READ/WRITE ACCESS: {workspace_path} (and below)",
            "⚠️  Whitelisted: /tmp",
        ]

        if self.continuum_repo_url:
            lines.append(f"⚠️  Continuum repo: {self.continuum_repo_url}")
        else:
            lines.append("ℹ️  CONTINUUM_REPO_URL not set - sessions local only")
            lines.append("ℹ️  To enable cloud sync:")
            lines.append("    1. Create private git repo")
            lines.append("    2. Set: export CONTINUUM_REPO_URL=git@github.com:you/continuum.git")
            lines.append("    3. Or use: /set_ccc_repo <url> in this session")

        lines.append(f"ℹ️  Claude account: {self.claude_account}")
        lines.append("━" * 60)

        return "\n".join(lines)

    def run(self):
        """Main entrypoint - show banner and start Claude"""
        # Get current workspace
        workspace = os.getcwd()

        # Show banner
        print(self.generate_banner(workspace))
        print()

        # For now, just launch Claude directly
        # TODO: Add session picker, sync, restore logic
        os.execvp('claude', ['claude'] + sys.argv[1:])

def main():
    manager = SessionManager()
    manager.run()

if __name__ == '__main__':
    main()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_session_manager.py -v`
Expected: PASS (3 tests)

**Step 5: Update Dockerfile to use session_manager.py as entrypoint**

Add at the end of Dockerfile:

```dockerfile
# Copy session manager
COPY --chown=$USER_NAME:$USER_NAME container-files/session_manager.py /home/$USER_NAME/session_manager.py
RUN chmod +x /home/$USER_NAME/session_manager.py

# Set entrypoint
ENTRYPOINT ["/home/claude/session_manager.py"]
CMD ["--dangerously-skip-permissions"]
```

**Step 6: Build and test**

Run: `docker build -t ccc-test:session .`
Expected: Successful build

Run: `docker run --rm ccc-test:session --help 2>&1 | head -20`
Expected: Shows banner followed by Claude help

**Step 7: Commit**

```bash
git add container-files/session_manager.py tests/test_session_manager.py Dockerfile
git commit -m "feat: add session manager entrypoint with banner

- Python session manager displays permissions banner
- Auto-detects Claude account type
- Shows continuum repo status
- Tests for banner generation
- Set as Docker entrypoint

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 1.7: GitHub Actions - Build and Push to Quay.io

**Files:**
- Create: `.github/workflows/build-push.yml`
- Create: `.github/workflows/test.yml`

**Step 1: Create test workflow**

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-cov

      - name: Run Python tests
        run: pytest tests/ -v --cov=container-files --cov-report=term

      - name: Install bats
        run: |
          git clone https://github.com/bats-core/bats-core.git
          cd bats-core
          sudo ./install.sh /usr/local

      - name: Run wrapper script tests
        run: bats tests/test_ccc_wrapper.bats
```

**Step 2: Create build and push workflow**

Create `.github/workflows/build-push.yml`:

```yaml
name: Build and Push to Quay.io

on:
  push:
    branches: [main]
    tags:
      - 'v*'
  workflow_dispatch:

env:
  IMAGE_NAME: quay.io/jluhrsen/claude-code-continuum

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Quay.io
        uses: docker/login-action@v3
        with:
          registry: quay.io
          username: ${{ secrets.QUAY_USERNAME }}
          password: ${{ secrets.QUAY_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=sha-
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Step 3: Create GitHub secrets documentation**

Add to README.md:

```markdown
## Development

### GitHub Actions Setup

For automated builds to Quay.io, configure these GitHub secrets:
- `QUAY_USERNAME`: Your Quay.io username
- `QUAY_PASSWORD`: Your Quay.io password or robot token

### Running Tests

```bash
# Python tests
pytest tests/ -v

# Wrapper script tests (requires bats)
bats tests/test_ccc_wrapper.bats
```
```

**Step 4: Commit**

```bash
git add .github/workflows/build-push.yml .github/workflows/test.yml README.md
git commit -m "ci: add GitHub Actions for testing and Quay.io builds

- Test workflow runs pytest and bats tests
- Build workflow pushes to quay.io/jluhrsen/claude-code-continuum
- Multi-platform builds (amd64, arm64)
- Automatic tagging (latest, sha, semver)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 2: Session Management

### Task 2.1: Continuum Repository Structure

**Files:**
- Create: `container-files/continuum.py`
- Create: `tests/test_continuum.py`

**Step 1: Write failing test for continuum repo initialization**

Create `tests/test_continuum.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'container-files'))

from continuum import ContinuumRepo

@pytest.fixture
def temp_continuum():
    """Create temporary continuum directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

def test_init_creates_directory_structure(temp_continuum):
    """Test that init creates expected directory structure"""
    repo = ContinuumRepo(str(temp_continuum))
    repo.init()

    assert (temp_continuum / 'sessions').exists()
    assert (temp_continuum / 'knowledge').exists()
    assert (temp_continuum / 'config').exists()
    assert (temp_continuum / 'config' / 'blocklist.txt').exists()
    assert (temp_continuum / 'config' / 'auto-load-rules.yaml').exists()

def test_init_creates_default_blocklist(temp_continuum):
    """Test that init creates blocklist with expected commands"""
    repo = ContinuumRepo(str(temp_continuum))
    repo.init()

    blocklist_file = temp_continuum / 'config' / 'blocklist.txt'
    content = blocklist_file.read_text()

    assert 'rm -rf' in content
    assert 'sudo' in content
    assert 'chmod' in content
    assert 'dd' in content

def test_list_sessions_empty(temp_continuum):
    """Test listing sessions when none exist"""
    repo = ContinuumRepo(str(temp_continuum))
    repo.init()

    sessions = repo.list_sessions()
    assert sessions == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_continuum.py -v`
Expected: FAIL with "No module named 'continuum'"

**Step 3: Write minimal continuum repo implementation**

Create `container-files/continuum.py`:

```python
#!/usr/bin/env python3
"""
Continuum Repository Management

Handles initialization, syncing, and management of the continuum git repository.
"""

import os
import yaml
from pathlib import Path
from typing import List, Dict, Any
import subprocess

class ContinuumRepo:
    """Manages the continuum repository structure and operations"""

    DEFAULT_BLOCKLIST = [
        "# CCC Command Blocklist",
        "# Commands that require approval before execution",
        "",
        "rm -rf",
        "dd",
        "mkfs.*",
        "iptables",
        "nftables",
        "sudo",
        "chmod",
        "chown",
        "curl.*|.*bash",
        "wget.*|.*bash",
        "systemctl",
    ]

    DEFAULT_AUTO_LOAD_RULES = {
        'rules': [
            {
                'repos': ['*'],
                'load': ['git-workflows.md']
            }
        ]
    }

    def __init__(self, path: str):
        self.path = Path(path)
        self.sessions_dir = self.path / 'sessions'
        self.knowledge_dir = self.path / 'knowledge'
        self.config_dir = self.path / 'config'

    def init(self):
        """Initialize continuum repository structure"""
        # Create directories
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create default blocklist
        blocklist_file = self.config_dir / 'blocklist.txt'
        if not blocklist_file.exists():
            blocklist_file.write_text('\n'.join(self.DEFAULT_BLOCKLIST) + '\n')

        # Create default auto-load rules
        rules_file = self.config_dir / 'auto-load-rules.yaml'
        if not rules_file.exists():
            with open(rules_file, 'w') as f:
                yaml.dump(self.DEFAULT_AUTO_LOAD_RULES, f, default_flow_style=False)

        # Create default knowledge files
        self._create_default_knowledge()

    def _create_default_knowledge(self):
        """Create default knowledge markdown files"""
        default_files = {
            'git-workflows.md': '# Git Workflows\n\nCommon git patterns and workflows.\n',
            'openshift-ci.md': '# OpenShift CI\n\nProw jobs, CI/CD workflows, artifact hunting.\n',
            'kubernetes.md': '# Kubernetes\n\nK8s and OVN networking patterns.\n',
            'jira.md': '# Jira\n\nBug tracking workflows and patterns.\n',
            'golang-patterns.md': '# Go Patterns\n\nGo best practices and common patterns.\n',
        }

        for filename, content in default_files.items():
            file_path = self.knowledge_dir / filename
            if not file_path.exists():
                file_path.write_text(content)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions"""
        if not self.sessions_dir.exists():
            return []

        sessions = []
        for session_dir in self.sessions_dir.iterdir():
            if session_dir.is_dir():
                metadata_file = session_dir / 'metadata.json'
                if metadata_file.exists():
                    import json
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                    sessions.append(metadata)

        return sessions

    def clone_or_pull(self, repo_url: str) -> bool:
        """Clone continuum repo if not exists, otherwise pull latest"""
        try:
            if (self.path / '.git').exists():
                # Already cloned, pull latest
                subprocess.run(
                    ['git', '-C', str(self.path), 'pull'],
                    check=True,
                    capture_output=True
                )
            else:
                # Clone repo
                self.path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ['git', 'clone', repo_url, str(self.path)],
                    check=True,
                    capture_output=True,
                    env={**os.environ, 'GIT_SSH_COMMAND': 'ssh -i ~/.ssh/continuum_key -o StrictHostKeyChecking=no'}
                )

                # If freshly cloned and empty, initialize structure
                if not self.sessions_dir.exists():
                    self.init()
                    subprocess.run(
                        ['git', '-C', str(self.path), 'add', '.'],
                        check=True
                    )
                    subprocess.run(
                        ['git', '-C', str(self.path), 'commit', '-m', 'Initialize continuum structure'],
                        check=True
                    )
                    subprocess.run(
                        ['git', '-C', str(self.path), 'push'],
                        check=True,
                        env={**os.environ, 'GIT_SSH_COMMAND': 'ssh -i ~/.ssh/continuum_key -o StrictHostKeyChecking=no'}
                    )

            return True
        except subprocess.CalledProcessError as e:
            print(f"Error syncing continuum repo: {e}")
            return False
```

**Step 4: Add pyyaml dependency note to README**

Add to README.md development section:

```markdown
### Dependencies

Container requires:
- Python 3.11+
- pyyaml (for auto-load rules)

Install for local testing:
```bash
pip install pyyaml pytest pytest-cov
```
```

**Step 5: Run tests to verify they pass**

Run: `pip install pyyaml && pytest tests/test_continuum.py -v`
Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add container-files/continuum.py tests/test_continuum.py README.md
git commit -m "feat: add continuum repository management

- Initialize directory structure (sessions, knowledge, config)
- Create default blocklist and auto-load rules
- Clone/pull continuum repo with deploy key
- List available sessions
- Tests for initialization

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 2.2: Integrate Continuum Sync into Session Manager

**Files:**
- Modify: `container-files/session_manager.py`
- Modify: `tests/test_session_manager.py`
- Modify: `Dockerfile`

**Step 1: Write failing test for continuum sync**

Add to `tests/test_session_manager.py`:

```python
def test_sync_continuum_when_url_set(tmp_path):
    """Test that session manager syncs continuum when URL is configured"""
    continuum_dir = tmp_path / '.continuum'

    with patch.dict(os.environ, {
        'CONTINUUM_REPO_URL': 'git@github.com:test/continuum.git',
        'HOME': str(tmp_path)
    }):
        with patch('session_manager.ContinuumRepo') as mock_repo:
            manager = SessionManager()
            manager.sync_continuum()

            # Should have attempted to clone or pull
            mock_repo.return_value.clone_or_pull.assert_called_once()

def test_no_sync_when_url_not_set(tmp_path):
    """Test that session manager skips sync when no URL configured"""
    with patch.dict(os.environ, {'CONTINUUM_REPO_URL': '', 'HOME': str(tmp_path)}):
        with patch('session_manager.ContinuumRepo') as mock_repo:
            manager = SessionManager()
            manager.sync_continuum()

            # Should not attempt sync
            mock_repo.return_value.clone_or_pull.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_manager.py::test_sync_continuum_when_url_set -v`
Expected: FAIL with "AttributeError: 'SessionManager' object has no attribute 'sync_continuum'"

**Step 3: Update session_manager.py to integrate continuum**

Add import at top:

```python
from continuum import ContinuumRepo
```

Add method to SessionManager class:

```python
def sync_continuum(self) -> bool:
    """Sync continuum repository if configured"""
    if not self.continuum_repo_url:
        return False

    print("📡 Syncing continuum repository...")
    repo = ContinuumRepo(str(self.continuum_path))
    success = repo.clone_or_pull(self.continuum_repo_url)

    if success:
        print("✓ Continuum synced")
    else:
        print("⚠️  Warning: Failed to sync continuum repository")

    return success

def list_sessions(self):
    """List available sessions from continuum"""
    repo = ContinuumRepo(str(self.continuum_path))
    return repo.list_sessions()
```

Update the `run` method:

```python
def run(self):
    """Main entrypoint - show banner, sync, and start Claude"""
    workspace = os.getcwd()

    # Show banner
    print(self.generate_banner(workspace))
    print()

    # Sync continuum if configured
    if self.continuum_repo_url:
        self.sync_continuum()
        print()

    # For now, just launch Claude directly
    # TODO: Add session picker and restore logic
    os.execvp('claude', ['claude'] + sys.argv[1:])
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_session_manager.py -v`
Expected: PASS (all tests)

**Step 5: Update Dockerfile to install pyyaml**

Add before session_manager.py copy:

```dockerfile
# Install Python dependencies
USER root
RUN dnf install -y python3-pip && dnf clean all
USER $USER_NAME
RUN pip3 install --user pyyaml
```

**Step 6: Build and test**

Run: `docker build -t ccc-test:sync .`
Expected: Successful build

**Step 7: Commit**

```bash
git add container-files/session_manager.py tests/test_session_manager.py Dockerfile
git commit -m "feat: integrate continuum sync into session manager

- Sync continuum repo on startup when URL configured
- Show sync status in startup flow
- Install pyyaml in container
- Tests for sync behavior

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: Security & Isolation

### Task 3.1: Command Blocklist Implementation

**Files:**
- Create: `container-files/blocklist.py`
- Create: `tests/test_blocklist.py`

**Step 1: Write failing test for blocklist matching**

Create `tests/test_blocklist.py`:

```python
import pytest
from pathlib import Path
import tempfile
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'container-files'))

from blocklist import CommandBlocklist

@pytest.fixture
def temp_blocklist():
    """Create temporary blocklist file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("rm -rf\n")
        f.write("sudo\n")
        f.write("chmod\n")
        f.write("dd\n")
        f.write("mkfs.*\n")
        temp_path = f.name

    yield temp_path
    os.unlink(temp_path)

def test_exact_match_blocked(temp_blocklist):
    """Test that exact command match is blocked"""
    blocklist = CommandBlocklist(temp_blocklist)

    assert blocklist.is_blocked("sudo apt install vim")
    assert blocklist.is_blocked("rm -rf /tmp/test")
    assert blocklist.is_blocked("chmod 777 file.txt")

def test_pattern_match_blocked(temp_blocklist):
    """Test that regex patterns are matched"""
    blocklist = CommandBlocklist(temp_blocklist)

    assert blocklist.is_blocked("mkfs.ext4 /dev/sda1")
    assert blocklist.is_blocked("mkfs /dev/sda1")

def test_allowed_commands_pass(temp_blocklist):
    """Test that non-blocked commands pass through"""
    blocklist = CommandBlocklist(temp_blocklist)

    assert not blocklist.is_blocked("ls -la")
    assert not blocklist.is_blocked("git status")
    assert not blocklist.is_blocked("make test")

def test_remove_from_blocklist(temp_blocklist):
    """Test removing command from blocklist"""
    blocklist = CommandBlocklist(temp_blocklist)

    assert blocklist.is_blocked("sudo test")
    blocklist.remove_pattern("sudo")
    assert not blocklist.is_blocked("sudo test")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_blocklist.py -v`
Expected: FAIL with "No module named 'blocklist'"

**Step 3: Write blocklist implementation**

Create `container-files/blocklist.py`:

```python
#!/usr/bin/env python3
"""
Command Blocklist Management

Checks commands against blocklist patterns and manages approvals.
"""

import re
from pathlib import Path
from typing import List, Optional

class CommandBlocklist:
    """Manages command blocklist for security approval prompts"""

    def __init__(self, blocklist_file: str):
        self.blocklist_file = Path(blocklist_file)
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> List[str]:
        """Load blocklist patterns from file"""
        if not self.blocklist_file.exists():
            return []

        patterns = []
        with open(self.blocklist_file) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    patterns.append(line)

        return patterns

    def is_blocked(self, command: str) -> Optional[str]:
        """
        Check if command matches any blocklist pattern

        Returns:
            The matching pattern if blocked, None if allowed
        """
        for pattern in self.patterns:
            # Support both exact matches and regex patterns
            try:
                if re.search(pattern, command):
                    return pattern
            except re.error:
                # If not valid regex, try exact substring match
                if pattern in command:
                    return pattern

        return None

    def remove_pattern(self, pattern: str):
        """Remove pattern from blocklist (for 'always allow')"""
        if pattern in self.patterns:
            self.patterns.remove(pattern)
            self._save_patterns()

    def _save_patterns(self):
        """Save current patterns back to file"""
        with open(self.blocklist_file, 'w') as f:
            f.write("# CCC Command Blocklist\n")
            f.write("# Commands that require approval before execution\n\n")
            for pattern in self.patterns:
                f.write(f"{pattern}\n")

    def prompt_approval(self, command: str, pattern: str) -> tuple[bool, bool]:
        """
        Prompt user for approval of blocked command

        Returns:
            (approved, remember) - whether to allow, and whether to remember choice
        """
        print(f"\n⚠️  BLOCKED COMMAND: {pattern}")
        print(f"Command: {command}")
        print("This command requires approval.")

        while True:
            response = input("Allow? [y/n/always]: ").lower().strip()

            if response == 'y':
                return (True, False)
            elif response == 'n':
                return (False, False)
            elif response == 'always':
                return (True, True)
            else:
                print("Please enter 'y', 'n', or 'always'")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_blocklist.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add container-files/blocklist.py tests/test_blocklist.py
git commit -m "feat: add command blocklist implementation

- Load and check commands against blocklist patterns
- Support regex and exact match patterns
- Remove patterns for 'always allow'
- Approval prompt system
- Comprehensive tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Implementation Notes

**Remaining Tasks:**

This plan covers the foundation (Phase 1), basic session management (Phase 2 partial), and security foundations (Phase 3 partial). The complete implementation requires:

**Phase 2 Completion (Session Management):**
- Task 2.3: Session creation and snapshot
- Task 2.4: /nightnight skill implementation
- Task 2.5: Session restore logic
- Task 2.6: Workspace git operations (patches, wip branches)

**Phase 3 Completion (Security):**
- Task 3.2: Integrate blocklist into Claude Code execution
- Task 3.3: Claude Code hook for command interception
- Task 3.4: Security tests (filesystem, credentials, blocklist)

**Phase 4 (Knowledge Management):**
- Task 4.1: Auto-load rules engine
- Task 4.2: /remember skill
- Task 4.3: PostToolUse hook for pattern detection
- Task 4.4: Knowledge file management

**Phase 5 (Advanced Features):**
- Task 5.1: Session time-travel
- Task 5.2: /set_ccc_repo command
- Task 5.3: Enhanced session picker UI
- Task 5.4: Session metadata and search

**Testing Priority:**
- Security tests are highest priority
- Each phase should have integration tests
- End-to-end workflow testing

**Commit Strategy:**
- Small, logical commits after each step
- All tests passing before commit
- Clear commit messages with Co-Authored-By

**Next Steps:**
The plan should be executed phase-by-phase, with code review checkpoints after each major phase completes.
