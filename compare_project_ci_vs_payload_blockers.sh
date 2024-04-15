#!/bin/bash

# TODO: make the release version a command line arg

# Step 1: Get all the payload blocking jobs. just need the nurps though
mapfile -t trt_jobs < <(curl -s "https://raw.githubusercontent.com/openshift/release/master/core-services/release-controller/_releases/release-ocp-4.16.json" | jq -r '.verify | to_entries[] | select(.value.optional != true) | .value.prowJob.name')

nurp_trt_jobs=()
for job in "${trt_jobs[@]}"; do
    nurp_trt_job=$(echo "$job" | sed -n 's/.*4.16-\(.*\)/\1/p')
    nurp_trt_jobs+=("$nurp_trt_job")
done

# TODO: don't hard code this to CNO and make full path to yaml file a CLI arg

# Step 2: Get all CNO presubmits. just the nurps.
mapfile -t cno_jobs < <(yq '.presubmits."openshift/cluster-network-operator"[].name' ../openshift/release/ci-operator/jobs/openshift/cluster-network-operator/openshift-cluster-network-operator-master-presubmits.yaml)

nurp_cno_jobs=()
for job in "${cno_jobs[@]}"; do
    nurp_cno_job=$(echo "$job" | sed -n 's/.*master-\(.*\)"$/\1/p')
    nurp_cno_jobs+=("$nurp_cno_job")
done

echo "JAMO: trt"
printf '%s\n' "${nurp_trt_jobs[@]}"
echo "JAMO: cno"
printf '%s\n' "${nurp_cno_jobs[@]}"

# Step 3: Check that all trt_jobs are listed in CNO jobs
missing_jobs=0
for job in "${nurp_trt_jobs[@]}"; do
    if [[ ! " ${nurp_cno_jobs[*]} " =~ " ${job} " ]]; then
        echo "Missing job: $job"
        ((missing_jobs++))
    fi
done

# Final output based on check
if [ "$missing_jobs" -eq 0 ]; then
    echo "All jobs are present in the YAML file."
else
    echo "There are $missing_jobs missing jobs."
fi
