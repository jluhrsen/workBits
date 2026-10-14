---
name: ci:analyze-payload-aggregate
description: Analyzes OpenShift CI payload aggregate jobs from GitHub PR comments. Extracts individual prow jobs from aggregate runs and searches test cases in junit XMLs.
---

# CI Payload Aggregate Analyzer

This skill navigates from a GitHub PR comment containing a `/payload-aggregate` bot response through to individual prow job test results.

## Usage

```
/ci:analyze-payload-aggregate <pr-number> [test-pattern] [--comment-filter <text>] [--limit <N>]
```

## Parameters

- `pr-number`: GitHub PR number (required)
- `test-pattern`: Regex pattern to search for in test case names (optional, searches all if omitted)
- `--comment-filter`: Text to filter which aggregate comment to use (optional, uses most recent if omitted)
- `--limit`: Maximum number of individual jobs to analyze (optional, analyzes all if omitted)

## Examples

1. **Find test matching pattern in latest aggregate**:
   ```
   /ci:analyze-payload-aggregate 3018 "network must go Progressing=True"
   ```

2. **Filter by specific job name**:
   ```
   /ci:analyze-payload-aggregate 3018 "Progressing=True" --comment-filter "e2e-aws-ovn-upgrade-ipsec"
   ```

3. **Limit analysis to first 5 jobs**:
   ```
   /ci:analyze-payload-aggregate 3018 --limit 5
   ```

## Implementation

### Step 1: Get PR comments and find aggregate job links

```bash
# Get comments after a specific date (to filter recent activity)
gh pr view <pr-number> --json comments --jq '.comments[] | select(.createdAt > "<date>") | {author: .author.login, createdAt: .createdAt, body: .body}' | jq -s '.'

# Extract bot responses with aggregate links
# Look for pattern: "See details on https://pr-payload-tests.ci.openshift.org/runs/ci/<id>"
```

Filter for `openshift-ci` bot comments containing `pr-payload-tests.ci.openshift.org/runs/ci/`.

### Step 2 & 3: Get individual job links

Two possible patterns:

**Pattern 1: Direct individual jobs** (most common)
The aggregate run page directly shows individual job links:
```bash
aggregate_run_url="https://pr-payload-tests.ci.openshift.org/runs/ci/<id>"
curl -s "$aggregate_run_url" | grep -o 'https://prow.ci.openshift.org/view/gs/test-platform-results/logs/[^"]*' | grep -v aggregator
```

**Pattern 2: Via aggregator prow job** (less common)
Some runs have an intermediate aggregator job. Get individual jobs from job-run-summary.html:
```bash
aggregate_run_url="https://pr-payload-tests.ci.openshift.org/runs/ci/<id>"
aggregate_job_url=$(curl -s "$aggregate_run_url" | grep -o 'https://prow.ci.openshift.org/view/gs/test-platform-results/logs/aggregator-[^"]*' | head -1)

# If aggregator job exists, extract individual jobs from job-run-summary.html
if [ -n "$aggregate_job_url" ]; then
    job_id=$(echo "$aggregate_job_url" | grep -o '[0-9]\{19\}$')
    job_name=$(echo "$aggregate_job_url" | sed 's|.*/logs/||' | cut -d'/' -f1)
    summary="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/logs/${job_name}/${job_id}/artifacts/release-analysis-prpqr-aggregator/openshift-release-analysis-prpqr-aggregator/artifacts/release-analysis-aggregator/job-run-summary.html"
    curl -s "$summary" | grep -o 'https://prow.ci.openshift.org/view/gs/test-platform-results/logs/[^"]*'
fi
```

### Step 4: Find test artifacts in each job

For each individual job, the junit XMLs are in a step directory with a varying number:

```bash
job_url="<individual-job-url>"
job_path=$(echo "$job_url" | sed 's|https://prow.ci.openshift.org/view/gs/test-platform-results/||')
base_url="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/${job_path}/artifacts/"

# Find the e2e step directory
# Matches: e2e-aws-ovn-upgrade/, e2e-aws-ovn-upgrade-ipsec-2/, etc.
step_dir=$(curl -s "$base_url" | grep -o 'href="[^"]*/"' | grep '/artifacts/e2e-' | head -1 | cut -d'"' -f2)

# Construct junit XML directory
junit_dir="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com${step_dir}openshift-e2e-test/artifacts/junit/"

# List XML files
curl -s "$junit_dir" | grep -o 'href="[^"]*\.xml"' | cut -d'"' -f2
```

### Step 5: Search test cases in XMLs

Common junit XML files to check:
- `e2e-monitor-tests__*.xml` - Monitor tests during upgrade
- `junit_operator.xml` - Operator tests
- `junit_nodes.xml` - Node tests
- Other e2e test XMLs

Search pattern in XML (case-insensitive):
```bash
xml_url="<full-xml-url>"
# Use grep -i for case-insensitive matching
curl -s "$xml_url" | grep '<testcase' | grep -i "<test-pattern>"
```

To check pass/fail status:
```bash
# Test passed if no <failure> tag within the testcase
curl -s "$xml_url" | grep -i '<testcase.*<pattern>.*>' | grep -q '<failure>' && echo "FAIL" || echo "PASS"
```

## Return Format

Return a summary table:

```
PR #3018 Payload Aggregate Analysis
=====================================
Aggregate Job: <job-name>
Individual Jobs Analyzed: <count>

Test Pattern: "<pattern>"
Total Matches: <count>
Pass: <count>
Fail: <count>

Details:
- Job <id>: <status>
- Job <id>: <status>
...
```

## Notes

- The step directory number (e.g., `-4`, `-8`) varies per job run
- Monitor test XMLs only exist for jobs that ran upgrade tests
- Some jobs may not have junit XMLs if they failed early
- Use `gh pr view` to access PR data - requires GitHub CLI authentication
