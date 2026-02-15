# Flake Buster - How To Guide

👻🚫 **Flake Buster** is your dashboard for quickly knowing e2e/payload failures in your PRs.

## Quick Start (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/jluhrsen/workBits/main/pr-ci-dashboard/run.sh | sh
```

Then open **http://localhost:5000** in your browser.

**Want to see the script first?** View it at: [run.sh](https://github.com/jluhrsen/workBits/blob/main/pr-ci-dashboard/run.sh)

Press Ctrl+C to stop and clean up.

### With Custom Search Filters (add github search syntax after `sh`)

```bash
curl -fsSL https://raw.githubusercontent.com/jluhrsen/workBits/main/pr-ci-dashboard/run.sh | sh -s -- author:jluhrsen
```

## Prerequisites

- **Python 3.8+** and **GitHub CLI (`gh`)** authenticated
  ```bash
  gh auth login  # If not already authenticated
  gh auth status # Verify
  ```

## Manual Installation

If you prefer not to use the quick start script:

```bash
git clone https://github.com/jluhrsen/workBits.git
cd workBits/pr-ci-dashboard
pip install -r requirements.txt
python server.py
```

Then open **http://localhost:5000**

### Custom Search Examples

Pass GitHub search syntax as arguments:

```bash
python server.py author:jluhrsen
python server.py repo:openshift/ovn-kubernetes
python server.py author:jluhrsen repo:openshift/ovn-kubernetes label:bug
```

Default search: `is:pr is:open archived:false author:openshift-pr-manager[bot]`

## Using the Dashboard

- **Search box**: Enter GitHub search syntax, press Enter
- **PR cards**: Show E2E jobs (left) and Payload jobs (right) with failure counts
- **Retest buttons**: Click to retest individual jobs or all jobs in a section
- **PR links**: Click the red PR number to open on GitHub

Retest buttons show "⏳ Retesting..." and poll until the job starts running.