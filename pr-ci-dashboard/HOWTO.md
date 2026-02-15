# Flake Buster - How To Guide

👻🚫 **Flake Buster** is your dashboard for hunting down flaky CI tests in OpenShift PRs.

## Quick Start (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/jluhrsen/workBits/main/pr-ci-dashboard/run.sh | sh
```

Then open **http://localhost:5000** in your browser.

**Want to see the script first?** View it at: [run.sh](https://github.com/jluhrsen/workBits/blob/main/pr-ci-dashboard/run.sh)

Press Ctrl+C to stop and clean up.

### With Custom Search Filters

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

## Configuration

**Script source**: Set `AI_HELPERS_BRANCH` environment variable (default: `refs/pull/177/head`, use `main` after merge)
```bash
export AI_HELPERS_BRANCH=main
```

**Port**: Default is 5000. Edit `server.py` line 111 to change.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "GitHub CLI not authenticated" | Run `gh auth login` |
| "Failed to fetch scripts" | Check internet connection, try `export AI_HELPERS_BRANCH=main` |
| No PRs showing up | Verify search syntax, test query at https://github.com/pulls |
| Slow loading (10-30s) | Normal - scripts query CI systems in real-time |
| Retest stuck | Refresh page, or wait (auto-stops after 5 min) |
| Script timeouts | Check network, increase timeout in `utils/job_executor.py` |

## Advanced Usage

**Run in background:**
```bash
nohup python server.py > dashboard.log 2>&1 &
```

**Access from network:** Server binds to `0.0.0.0:5000` (no auth - trusted networks only)

**Saved queries:** Bookmark search commands for quick access
- Your PRs: `python server.py author:yourusername`
- Specific repo: `python server.py repo:openshift/ovn-kubernetes`

## Getting Help

- Issues: https://github.com/jluhrsen/workBits/issues
- Design doc: `docs/design.md`

Happy flake busting! 👻🚫
