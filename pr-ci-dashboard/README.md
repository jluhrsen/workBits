# PR CI Dashboard

Dashboard to see PR job failures and retest them.

## Quick Start

```bash
python server.py --author:jluhrsen --repo:openshift/ovn-kubernetes
```

Visit http://localhost:5000

## Configuration

### Environment Variables

- `AI_HELPERS_BRANCH`: GitHub branch/ref to fetch scripts from (default: refs/pull/177/head)
  - Development (current): refs/pull/177/head
  - Production (after merge): main

## Documentation

See [docs/design.md](docs/design.md) for the complete design document.

