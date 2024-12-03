import requests
import json
import re
import pandas as pd
from datetime import datetime, timezone

BASE_URL = "https://prow.ci.openshift.org"
JOB_HISTORY_URL = f"{BASE_URL}/job-history/gs/test-platform-results/pr-logs/directory/pull-ci-openshift-ovn-kubernetes-master-images"
CUTOFF_DATE = datetime(2024, 5, 1, tzinfo=timezone.utc)


def fetch_page(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def extract_all_builds(page_source):
    # Extract `allBuilds` JSON data
    match = re.search(r"var allBuilds = (\[.*?\]);", page_source, re.DOTALL)
    if not match:
        raise ValueError("Could not find allBuilds data in page source")
    all_builds_json = match.group(1)
    return json.loads(all_builds_json)


def get_older_runs_link(page_source):
    # Extract the "Older Runs" link
    match = re.search(r'<a href="(/job-history/[^"]+?)">&lt;- Older Runs</a>', page_source)
    if match:
        return BASE_URL + match.group(1)
    return None


def convert_duration_to_seconds(duration_str):
    """Convert a duration like '5m37s' to total seconds."""
    match = re.match(r'(?:(\d+)m)?(?:(\d+)s)?', duration_str)
    if not match:
        return None
    minutes = int(match.group(1)) if match.group(1) else 0
    seconds = int(match.group(2)) if match.group(2) else 0
    return minutes * 60 + seconds


def fetch_build_times(log_url):
    """Fetch and parse build times from the log."""
    try:
        response = requests.get(log_url)
        response.raise_for_status()
        log_content = response.text

        build_times = {}
        matches = re.findall(r"Build (\S+?) succeeded after (\d+m\d+s)", log_content)
        for build_name, duration in matches:
            build_times[build_name] = convert_duration_to_seconds(duration)

        return build_times
    except Exception as e:
        print(f"Error fetching log from {log_url}: {e}")
        return {}


def parse_build_data(builds):
    build_data = []
    for build in builds:
        if build.get("Result") != "SUCCESS":
            continue

        job_id = build.get("ID")
        started = build.get("Started")
        duration = build.get("Duration")
        spyglass_link = BASE_URL + build.get("SpyglassLink")

        refs = build.get("Refs", {})
        pulls = refs.get("pulls", [])
        pr_number = pulls[0]["number"] if pulls else "N/A"

        # Convert start time to day of the week and time of day
        start_datetime = datetime.fromisoformat(started.replace("Z", "+00:00"))
        if start_datetime < CUTOFF_DATE:
            continue  # Skip builds earlier than the cutoff date

        day_of_week = start_datetime.strftime("%A")
        time_of_day = start_datetime.strftime("%H:%M:%S")
        human_readable_date = start_datetime.strftime("%Y-%m-%d")

        # Construct log URL
        log_url = (
            f"https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs"
            f"/test-platform-results/pr-logs/pull/openshift_ovn-kubernetes/{pr_number}"
            f"/pull-ci-openshift-ovn-kubernetes-master-images/{job_id}/build-log.txt"
        )

        # Fetch build times from the log
        build_times = fetch_build_times(log_url)
        build_src = build_times.get("src-amd64", None)
        build_base = build_times.get("ovn-kubernetes-base-amd64", None)
        build_microshift = build_times.get("ovn-kubernetes-microshift-amd64", None)
        build_ovn = build_times.get("ovn-kubernetes-amd64", None)

        build_data.append({
            "Job ID": job_id,
            "PR Number": pr_number,
            "Duration (ns)": duration,
            "Day of Week": day_of_week,
            "Time of Day": time_of_day,
            "Human Readable Date": human_readable_date,
            "Spyglass Link": spyglass_link,
            "Log URL": log_url,
            "Build src-amd64 (s)": build_src,
            "Build ovn-kubernetes-base-amd64 (s)": build_base,
            "Build ovn-kubernetes-microshift-amd64 (s)": build_microshift,
            "Build ovn-kubernetes-amd64 (s)": build_ovn,
            "Start DateTime": start_datetime,  # For debugging or further processing
        })
    return build_data


def main():
    url = JOB_HISTORY_URL
    all_data = []

    while url:
        print(f"Fetching page: {url}")
        page_source = fetch_page(url)

        # Extract builds and older runs link
        builds = extract_all_builds(page_source)
        page_data = parse_build_data(builds)

        # Add valid builds to the master list
        all_data.extend(page_data)

        # Check if we should stop (based on dates)
        if page_data and min(item["Start DateTime"] for item in page_data) < CUTOFF_DATE:
            break

        # Follow the "Older Runs" link
        url = get_older_runs_link(page_source)

    # Remove 'Start DateTime' from output before saving
    for item in all_data:
        del item["Start DateTime"]

    # Save data to a CSV
    df = pd.DataFrame(all_data)
    df.to_csv("build_data.csv", index=False)
    print("Data saved to build_data.csv")


if __name__ == "__main__":
    main()
