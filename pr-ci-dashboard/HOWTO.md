# Flake Buster - How To Guide

👻🚫 **Flake Buster** is your dashboard for hunting down flaky CI tests in OpenShift PRs.

## Prerequisites

Before you start, make sure you have:

1. **Python 3.8 or higher**
   ```bash
   python3 --version
   ```

2. **GitHub CLI (`gh`) installed and authenticated**
   ```bash
   # Install gh (if needed)
   # https://cli.github.com/manual/installation

   # Authenticate
   gh auth login

   # Verify authentication
   gh auth status
   ```

3. **Access to OpenShift repos**
   - You need read access to the OpenShift repositories you want to monitor
   - The dashboard uses `gh` CLI under the hood, so if `gh` works, the dashboard will too

## Installation

1. **Clone this repository**
   ```bash
   git clone https://github.com/jluhrsen/workBits.git
   cd workBits/pr-ci-dashboard
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify bash scripts are available**

   The dashboard fetches bash scripts from the `openshift-eng/ai-helpers` repository. By default, it pulls from PR #177 (which contains the scripts). Once that PR merges, you can switch to the main branch.

   **To use a different branch/ref:**
   ```bash
   export AI_HELPERS_BRANCH=main
   # Or for a specific PR:
   export AI_HELPERS_BRANCH=refs/pull/177/head
   ```

## Running the Dashboard

### Basic Usage

Start the server with default search (open PRs from openshift-pr-manager bot):

```bash
python server.py
```

Then open your browser to: **http://localhost:5000**

### Custom Search Filters

You can append search filters as command-line arguments:

**Search PRs by author:**
```bash
python server.py author:jluhrsen
```

**Search PRs in a specific repo:**
```bash
python server.py repo:openshift/ovn-kubernetes
```

**Combine multiple filters:**
```bash
python server.py author:jluhrsen repo:openshift/ovn-kubernetes
```

**Custom query (replaces default):**
```bash
python server.py is:pr is:open repo:openshift/release label:bugfix
```

### Default Search

The default search query is:
```
is:pr is:open archived:false author:openshift-pr-manager[bot]
```

This shows all open PRs created by the CI bot, which typically have the most CI test activity.

## Using the Dashboard

### Search for PRs

1. The search box at the top accepts GitHub search syntax
2. Click **Search** or press Enter to find PRs
3. Click **Refresh** in the sidebar to reload the current search

### View Job Status

Each PR card shows:
- **E2E Jobs** - End-to-end test jobs (left panel)
- **Payload Jobs** - Payload test jobs (right panel)
- Failed job count and running job count in the headers
- Click the ▶ arrow to expand and see individual jobs

### Retest Failed Jobs

When jobs fail, you can retest them:

1. **Individual job:** Click the **Retest** button next to a failed job
2. **All jobs in a section:** Click **Retest All E2E** or **Retest All Payload**

The button will change to "⏳ Retesting..." and the dashboard will poll every 5 seconds to track when the job starts running. Once it starts, it disappears from the failed list.

### PR Links

Click the **#123** PR number (in red) to open the PR on GitHub.

## Configuration

### Change the Script Source

By default, scripts are fetched from PR #177. To change this:

```bash
export AI_HELPERS_BRANCH=main
python server.py
```

Or edit `utils/script_fetcher.py` line 9 to change the default:
```python
AI_HELPERS_BRANCH = os.environ.get('AI_HELPERS_BRANCH', 'main')  # Changed from refs/pull/177/head
```

### Change the Port

The default port is 5000. To use a different port, edit `server.py` line 111:
```python
app.run(host='0.0.0.0', port=8080, debug=True)  # Changed from 5000
```

## Troubleshooting

### "GitHub CLI not authenticated"

**Problem:** Auth banner shows at the top

**Solution:**
```bash
gh auth login
```

Follow the prompts to authenticate with GitHub.

### "Failed to fetch scripts"

**Problem:** Dashboard fails to start with script fetch error

**Solutions:**
1. Check your internet connection
2. Verify the branch exists: `export AI_HELPERS_BRANCH=main`
3. Try using a different branch: `export AI_HELPERS_BRANCH=refs/pull/177/head`

### No PRs showing up

**Problem:** Search returns empty results

**Solutions:**
1. Check your search query syntax (use GitHub search syntax)
2. Verify you have access to the repos you're searching
3. Test the query on GitHub.com first: https://github.com/pulls
4. Try a broader search: `is:pr is:open`

### Jobs stuck with "Retesting..." button

**Problem:** Retest button stays grayed out forever

**Cause:** The job may have been removed from the CI configuration (this happens when old release versions are deprecated)

**Solution:**
1. Refresh the page to reset button states
2. The polling will automatically stop after 5 minutes
3. Check if the job still exists in the [openshift/release](https://github.com/openshift/release) repository

### Slow job status loading

**Problem:** E2E/Payload sections show "loading..." for a long time

**Cause:** The bash scripts take 10-30 seconds to fetch job data from GitHub/Prow

**Solution:** This is normal! The scripts are querying CI systems in real-time. Be patient.

### Scripts timeout

**Problem:** Job status shows errors or timeouts

**Solution:** The scripts have a 30-second timeout. If they fail:
1. Check your network connection
2. Try again (sometimes CI systems are slow)
3. Increase the timeout in `utils/job_executor.py` lines 24 and 67:
   ```python
   timeout=60  # Increase from 30 to 60 seconds
   ```

## Advanced Usage

### Run in the background

```bash
nohup python server.py > dashboard.log 2>&1 &
```

### Access from other machines

The server binds to `0.0.0.0` so you can access it from other machines on your network:

```
http://your-machine-ip:5000
```

**Security note:** This dashboard has no authentication. Only run it on trusted networks.

### Monitoring specific teams

Create saved queries in your browser bookmarks:

- Your team's PRs: `is:pr is:open author:yourusername`
- Your repo: `is:pr is:open repo:openshift/your-repo`
- Critical bugs: `is:pr is:open label:bugzilla/severity-urgent`

## Tips & Tricks

1. **Keyboard shortcuts:** Press Enter in the search box to search quickly

2. **Share URLs:** The search query is set via command-line args, so share your startup command with teammates

3. **Monitor CI health:** Use the bot search to see overall CI health across all repos

4. **Track regressions:** Watch for jobs that fail consecutively (shown in parentheses)

5. **Batch retesting:** Use "Retest All" to quickly retry all failed jobs in a section

## Getting Help

- **Issues:** https://github.com/jluhrsen/workBits/issues
- **Source:** https://github.com/jluhrsen/workBits/tree/main/pr-ci-dashboard
- **Design Doc:** See `docs/design.md` for architecture details

## What's Next?

Future enhancements may include:
- AI-powered failure analysis (the grayed-out "Analyze" buttons)
- Display passed/successful tests
- Historical failure tracking
- Email/Slack notifications
- Multi-user authentication

Happy flake busting! 👻🚫
