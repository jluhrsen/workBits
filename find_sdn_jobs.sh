#!/bin/bash

# Ensure a job name is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 JOB_NAME"
    exit 1
fi

JOB_NAME="$1"
URL="https://prow.ci.openshift.org/job-history/gs/test-platform-results/pr-logs/directory/${JOB_NAME}"

# Fetch the page
PAGE_CONTENT=$(curl -s "$URL")

# Extract the 'allBuilds' JavaScript array and parse it to get the URL of the most recent successful job
SUCCESSFUL_JOB_URL=$(echo "$PAGE_CONTENT" | \
    awk '/var allBuilds =/,/];/' | \
    sed 's/var allBuilds = //' | sed 's/;$//' | \
    jq -r '.[] | select(.Result == "SUCCESS") | .SpyglassLink' | \
    sort -r | head -n 1)

RESULT="FAIL"
if [ -n "$SUCCESSFUL_JOB_URL" ]; then
    RESULT="PASS"
fi

NETWORK_TYPE="MISSING"
if [[ "$JOB_NAME" == *"ovn"* ]]; then
    NETWORK_TYPE="OVN"
elif [[ "$JOB_NAME" == *"sdn"* ]]; then
    NETWORK_TYPE="SDN"
fi

# Output: JOB_NAME, PASS or FAIL, NETWORK_TYPE or MISSING
echo "$JOB_NAME, $RESULT, $NETWORK_TYPE"
