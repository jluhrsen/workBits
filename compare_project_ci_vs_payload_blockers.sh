#!/bin/bash

if [ $# -lt 3 ]; then
    echo "Usage: $0 <release_version> <release_repo_path> <project_name>"
    exit 1
fi

release_version=$1
release_repo_path=$2
project_name=$3

mapfile -t trt_jobs < <(curl -s "https://raw.githubusercontent.com/openshift/release/master/core-services/release-controller/_releases/release-ocp-${release_version}.json" | jq -r '.verify | to_entries[] | select(.value.optional != true) | .value.prowJob.name')

nurp_trt_jobs=()
for job in "${trt_jobs[@]}"; do
    # e2e-aws-ovn-hypershift-conformance has a weird name and we need to hard code it to be right here
    # so the final report is right
    if [[ "$job" == "periodic-ci-openshift-hypershift-release-4.16-periodics-e2e-aws-ovn-conformance" ]]; then
        nurp_trt_job="e2e-aws-ovn-hypershift-conformance"
    else
        nurp_trt_job=$(echo "$job" | sed -n 's/.*4.16-\(.*\)/\1/p')
    fi
    nurp_trt_jobs+=("$nurp_trt_job")
done

mapfile -t project_jobs < <(yq ".presubmits.\"openshift/${project_name}\"[].name" "${release_repo_path}/ci-operator/jobs/openshift/${project_name}/openshift-${project_name}-master-presubmits.yaml")

nurp_project_jobs=()
for job in "${project_jobs[@]}"; do
    nurp_project_job=$(echo "$job" | sed -n 's/.*master-\(.*\)"$/\1/p')
    if [[ "$nurp_project_job" =~ "upgrade-from-stable" ]]; then
        nurp_project_job=$(echo "$nurp_project_job" | sed "s/^${release_version}-//")
    fi
    nurp_project_jobs+=("$nurp_project_job")
done

excluded_jobs=("install-analysis-all" "overall-analysis-all" "e2e-metal-ipi-sdn-bm")
missing_jobs=0
for job in "${nurp_trt_jobs[@]}"; do
    if printf '%s\n' "${excluded_jobs[@]}" | grep -q -P "^${job}$"; then
        continue
    fi
    if [[ ! " ${nurp_project_jobs[*]} " =~ " ${job} " ]]; then
        echo "Missing job: $job"
        ((missing_jobs++))
    fi
done

if [ "$missing_jobs" -eq 0 ]; then
    echo "All jobs are present in the YAML file."
else
    echo "There are $missing_jobs missing jobs."
fi