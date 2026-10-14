---
name: ci-prow-navigation
description: Use when investigating Prow CI job failures, navigating job histories, fetching build logs and artifacts, or debugging e2e test failures on OpenShift CI
---

# Prow CI Navigation and Investigation

## Overview

OpenShift CI runs on Prow. Jobs produce artifacts stored in GCS. This skill covers how to navigate job histories, find build logs, fetch artifacts, and debug failures for any job type (e2e tests, periodic jobs, presubmits, etc.).

## Key URL Patterns

All Prow jobs follow consistent URL structures. Replace `<JOB_NAME>` with the full job name and `<JOB_ID>` with the numeric run ID.

### Job History and Individual Runs

- **Job history page** (list of recent runs with timestamps, durations, pass/fail):
  `https://prow.ci.openshift.org/job-history/gs/test-platform-results/logs/<JOB_NAME>`

- **Individual job view** (overview page for a single run):
  `https://prow.ci.openshift.org/view/gs/test-platform-results/logs/<JOB_NAME>/<JOB_ID>`

### Artifacts

- **Artifacts root** (browse all artifacts for a run):
  `https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/logs/<JOB_NAME>/<JOB_ID>/artifacts/`

- **Step artifacts** (each CI step has its own subdirectory):
  `.../artifacts/<WORKFLOW_NAME>/<STEP_NAME>/`

- **Build log for a step** (the main output log):
  `.../artifacts/<WORKFLOW_NAME>/<STEP_NAME>/build-log.txt`

- **Job-level metadata** (at the job root, one level above `artifacts/`):
  - `finished.json` - pass/fail result, timestamp
  - `prowjob.json` - full job spec including start/completion times, state, description
  - `podinfo.json` - pod scheduling details

### Fetching Content

For raw text files (build logs, JSON), prefer `curl -sS` over WebFetch as it gives exact content:
```bash
curl -sS 'https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/logs/<JOB_NAME>/<JOB_ID>/artifacts/<WORKFLOW>/<STEP>/build-log.txt'
```

For HTML pages (job history, job view), use WebFetch since they require rendering.

## Investigating a Job Failure

### 1. Find the job

If you have a PR, list its CI jobs:
```bash
gh pr checks <PR_NUM> --repo <ORG>/<REPO>
```

If you have a job name, browse its history via the job history URL pattern above.

If you need to find job names for a repo:
```bash
# List all periodic jobs for a repo
curl -sS 'https://prow.ci.openshift.org/prowjobs.js?repo=<ORG>%2F<REPO>&type=periodic' | \
  jq -r '.items[].spec.job' | sort -u

# Filter by keyword
... | grep '<keyword>'
```

### 2. Get the build log

The most useful artifact is usually `build-log.txt` for the failing step. Browse the artifacts directory to find which step failed, then fetch its log.

Common step directory structures:
- **e2e tests:** `artifacts/<test-name>/e2e-<variant>/build-log.txt`
- **Unit tests / builds:** `artifacts/<test-name>/unit/build-log.txt`
- **Custom steps:** `artifacts/<workflow>/<step-name>/build-log.txt`

### 3. Check job metadata

```bash
# Quick check: did the job pass, and why not?
curl -sS '.../finished.json' | jq .

# Detailed timing and error description
curl -sS '.../prowjob.json' | jq '{
  startTime: .status.startTime,
  completionTime: .status.completionTime,
  state: .status.state,
  description: .status.description
}'
```

Common `description` values for errored (not failed) jobs:
- `"Pod scheduling timeout."` - job pod never started (infra issue)
- `"the test step failed"` - an actual test step failed

### 4. Browse artifacts directory

When you don't know the step structure, browse the artifacts root. Use WebFetch on the gcsweb URL to list directories and files.

For e2e test runs, common useful artifacts beyond build-log.txt:
- `junit*.xml` - structured test results
- `must-gather/` - cluster state dumps
- `openshift-e2e-test/artifacts/` - test-specific outputs

## Matching a Job Run to a Time Window

Job history pages show start times, durations, and status for each run. When trying to find which specific run corresponds to an event:

1. WebFetch the job history page and ask for runs around your target timestamp
2. Duration is a strong signal: short runs (~20s) often indicate early exits; longer runs indicate real work
3. Cross-reference multiple job histories if multiple periodic jobs could be responsible

## PR-Specific CI

```bash
# Get all check statuses on a PR
gh pr checks <PR_NUM> --repo <ORG>/<REPO>

# Get PR comments (bot messages, /retest, etc.)
gh api 'repos/<ORG>/<REPO>/issues/<PR_NUM>/comments' \
  --jq '.[] | {user: .user.login, created_at, body: .body[:300]}'
```

## Downstream Merge Jobs (openshift/ovn-kubernetes)

Three periodic jobs merge upstream ovn-org/ovn-kubernetes into openshift/ovn-kubernetes hourly:

| Job | Keyword |
|-----|---------|
| release-4.22 | `release-4.22-periodics-downstream-merge` |
| release-4.23 | `release-4.23-periodics-downstream-merge` |
| release-5.0 | `release-5.0-periodics-downstream-merge` |

All three target the same `master` branch and can race. The automation script lives at `ci-operator/step-registry/github/downstream-sync/github-downstream-sync-commands.sh` in the `openshift/release` repo (local: `/home/jamoluhrsen/repos/RedHat/openshift/release/`).

PRs are created by `openshift-pr-manager[bot]`. Failure indicators in PR title: `CONFLICT!`, `GO MOD FAILED!`, `TEST ANNOTATIONS FAILED!`. The step name for the build log is `github-downstream-sync`.

To find which of the three jobs created a d/s merge PR:
1. Get the PR creation time
2. Check all three job histories around that time
3. The creating job will have a FAILURE status (script exits 1 on failures) or SUCCESS (clean merge), with a longer duration than the "already exists, exiting" runs
4. Fetch its build log to confirm
