import argparse
import time
import requests

parser = argparse.ArgumentParser(description='Clone a Jira issue multiple times with sprint info.')
parser.add_argument('sprint_id', type=str, help='ID of the target sprint')
args = parser.parse_args()
sprint_id = args.sprint_id

try:
    with open('./jira_token', 'r') as file:
        access_token = file.read().strip()
except Exception as e:
    print(f"Error reading token: {e}")
    exit(1)

jira_url = 'https://issues.redhat.com'
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

# Get the sprint name
sprint_info_url = f'{jira_url}/rest/agile/1.0/sprint/{sprint_id}'
sprint_response = requests.get(sprint_info_url, headers=headers)
if sprint_response.status_code != 200:
    print(f"Failed to fetch sprint info. Response: {sprint_response.text}")
    exit(1)

sprint_name = sprint_response.json()['name']
print(f"Target sprint: {sprint_name}")
time.sleep(0.5)

# Get the source issue details
source_issue_key = "CORENET-6030"
issue_url = f'{jira_url}/rest/api/2/issue/{source_issue_key}'
issue_response = requests.get(issue_url, headers=headers)
if issue_response.status_code != 200:
    print(f"Failed to fetch source issue. Response: {issue_response.text}")
    exit(1)

issue_data = issue_response.json()
base_summary = issue_data['fields']['summary']
description = issue_data['fields'].get('description', '')
story_points = issue_data['fields'].get('customfield_12310243', 1)

time.sleep(0.5)

# Define clones
checklist = [
    ("week1 check1", "jluhrsen"),
    ("week1 check2", "anusaxen"),
    ("week2 check1", "jluhrsen"),
    ("week2 check2", "anusaxen"),
    ("week3 check1", "jluhrsen"),
    ("week3 check2", "anusaxen"),
]

# Create clones
for check_label, assignee in checklist:
    new_summary = base_summary.replace("[GENERIC_TO_BE_CLONED]", f"[{check_label} {sprint_name}]")
    create_issue_url = f'{jira_url}/rest/api/2/issue'
    new_issue_data = {
        "fields": {
            "project": {"key": "CORENET"},
            "issuetype": {"name": "Story"},
            "summary": new_summary,
            "description": description,
            "assignee": {"name": assignee},
            "priority": {"name": "Normal"}
        }
    }

    create_response = requests.post(create_issue_url, headers=headers, json=new_issue_data)
    time.sleep(0.5)

    if create_response.status_code == 201:
        new_issue_key = create_response.json()['key']
        sprint_add_url = f'{jira_url}/rest/agile/1.0/sprint/{sprint_id}/issue'
        sprint_response = requests.post(sprint_add_url, headers=headers, json={"issues": [new_issue_key]})
        time.sleep(0.5)

        if sprint_response.status_code == 204:
            print(f"Created {new_issue_key} assigned to {assignee}:\n  {new_summary}")
        else:
            print(f"Failed to add {new_issue_key} to sprint. Response: {sprint_response.text}")
    else:
        print(f"Failed to create issue. Response: {create_response.text}")
