---
name: ci-prow-navigation
description: Navigate Prow CI job failures, histories, logs, and artifacts for OpenShift CI debugging
---

# Prow CI Navigation Reference

Use this skill when investigating Prow CI job failures, navigating job histories, fetching build logs and artifacts, or debugging e2e test failures on OpenShift CI.

## URL Patterns

### Job History
- Pattern: `https://prow.ci.openshift.org/job-history/gs/test-platform-results/logs/<JOB_NAME>`
- Example: `https://prow.ci.openshift.org/job-history/gs/test-platform-results/logs/periodic-ci-openshift-ovn-kubernetes-release-4.17-periodics-e2e-metal-ipi-ovn-dualstack`

### Individual Job Run
- Pattern: `https://prow.ci.openshift.org/view/gs/test-platform-results/logs/<JOB_NAME>/<BUILD_ID>`
- Build ID is typically a 19-digit number (timestamp-based)

### Artifacts Browser (GCSWeb)
- Pattern: `https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/logs/<JOB_NAME>/<BUILD_ID>/artifacts/`
- Navigate to specific artifacts by appending paths

### Build Log
- Pattern: `https://prow.ci.openshift.org/view/gs/test-platform-results/logs/<JOB_NAME>/<BUILD_ID>`
- Look for `build-log.txt` link on the page

### Job Metadata
- Pattern: `https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/logs/<JOB_NAME>/<BUILD_ID>/prowjob.json`
- Contains job configuration, timestamps, status, environment variables

## Investigation Workflow

1. **Find the job**: Start with job history URL to see recent runs
2. **Get build log**: Navigate to specific build ID and fetch build-log.txt
3. **Check metadata**: Fetch prowjob.json for job configuration
4. **Browse artifacts**: Use gcsweb to explore test outputs, must-gather, etc.

## PR-Specific CI

- Use `gh pr checks <PR_NUMBER>` to see CI status for a PR
- Check PR comments for `/test` and `/retest` bot responses
- Job links from PR checks point to Prow job URLs

## Downstream Merge Jobs

OpenShift maintains periodic jobs that merge upstream ovn-org/ovn-kubernetes into openshift/ovn-kubernetes:

- `periodic-ci-openshift-ovn-kubernetes-release-4.22-downstream-merge`
- `periodic-ci-openshift-ovn-kubernetes-release-4.23-downstream-merge`
- `periodic-ci-openshift-ovn-kubernetes-release-5.0-downstream-merge`

## Fetching Content

- **Prefer `curl -sS`** for raw text files (logs, JSON, etc.)
- **Use WebFetch** for HTML pages that need parsing
- Always specify full URLs with `https://`

## Common Artifacts

- `build-log.txt` - Main job execution log
- `prowjob.json` - Job metadata
- `artifacts/` - Test outputs, must-gather, installer logs
- `artifacts/*/pods/` - Pod logs organized by namespace
- `artifacts/e2e-*-test/` - E2E test-specific artifacts
