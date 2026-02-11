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

Apache 2.0 License - see LICENSE file.
