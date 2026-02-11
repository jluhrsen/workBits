# PR CI Dashboard

Dashboard to see PR job failures and retest them.

## Features

- Search PRs using GitHub query syntax
- View failed e2e and payload jobs with consecutive failure counts
- One-click retest via local `gh` CLI
- Progressive loading for fast UX
- Grayed-out "Analyze" button (future enhancement)

## Prerequisites

1. **Python 3.8+**
2. **GitHub CLI** - Install from https://cli.github.com
3. **GitHub CLI authenticated** - Run: `gh auth login`

## Installation

```bash
# Clone repository
cd /home/jamoluhrsen/repos/RedHat/workbits/pr-ci-dashboard

# Install dependencies
pip install -r requirements.txt
```

## Usage

Start the dashboard with optional search parameters:

```bash
# Basic usage (default search)
python server.py

# Add custom search parameters
python server.py --author:jluhrsen --repo:openshift/ovn-kubernetes

# Multiple parameters
python server.py --author:jluhrsen --label:bug is:draft
```

Then visit: **http://localhost:5000**

### Default Search

The dashboard defaults to:
```
is:pr is:open archived:false author:openshift-pr-manager[bot]
```

CLI arguments are appended to this base query.

## How It Works

1. **Server starts** → Fetches bash scripts from GitHub PR #177
2. **User searches** → GitHub CLI finds matching PRs
3. **For each PR** → Executes e2e-retest.sh and payload-retest.sh
4. **Parses output** → Extracts failed/running jobs
5. **User clicks Retest** → Posts `/test` or `/payload-job` comment via `gh`

## Architecture

- **Backend**: Flask server with subprocess execution
- **Frontend**: Vanilla HTML/CSS/JavaScript (Red Hat theme)
- **Scripts**: Fetched from https://github.com/openshift-eng/ai-helpers/pull/177
- **Auth**: Local `gh` CLI (no OAuth needed)

## Project Structure

```
pr-ci-dashboard/
├── server.py                 # Flask app entry point
├── api/
│   ├── search.py            # PR search via gh
│   ├── jobs.py              # Job status fetching
│   └── retest.py            # Post retest comments
├── parsers/
│   ├── e2e_parser.py        # Parse e2e-retest.sh output
│   └── payload_parser.py    # Parse payload-retest.sh output
├── utils/
│   ├── script_fetcher.py    # Fetch scripts from GitHub
│   ├── job_executor.py      # Execute bash scripts
│   └── gh_auth.py           # Check gh CLI auth
├── static/
│   └── app.js               # Frontend JavaScript
├── templates/
│   └── index.html           # Dashboard HTML
└── docs/
    └── design.md            # Design document
```

## Configuration

### Environment Variables

- `AI_HELPERS_BRANCH`: GitHub branch/ref to fetch scripts from (default: refs/pull/177/head)
  - Development (current): refs/pull/177/head
  - Production (after merge): main

## Troubleshooting

**"GitHub CLI not authenticated"**
```bash
gh auth login
```

**"Failed to fetch scripts"**
- Check internet connection
- Verify GitHub is accessible
- Check PR #177 still exists

**Scripts timeout**
- Increase timeout in `utils/job_executor.py` (default 30s)
- PRs with many jobs may take longer

**Retest button disabled**
- Check `gh auth status` in terminal
- Re-authenticate if needed

## Future Enhancements

- "Analyze" button - AI-powered failure pattern detection
- Auto-refresh toggle
- URL state persistence
- Deployment to Red Hat internal platform

## Documentation

See [docs/design.md](docs/design.md) for the complete design document.

## License

See LICENSE for details.
