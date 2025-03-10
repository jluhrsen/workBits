import argparse
import time
import requests

# to find the new sprint ID, run the find_new_sprint_id.py script in
# this project
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('new_sprint_id', type=str, help='ID of the new sprint')
args = parser.parse_args()
new_sprint_id = args.new_sprint_id

try:
    with open('./jira_token', 'r') as file:
        access_token = file.read().strip()
except FileNotFoundError:
    print(f"Error: The file ./jira_token was not found.")
    exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)

jira_url = 'https://issues.redhat.com'
user = 'jluhrsen@redhat.com'
api_url = f'{jira_url}/rest/api/2/search'
jql_query = 'text ~ "check network related component readiness" AND assignee = jluhrsen and Sprint = 69734'
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}
params = {
    'jql': jql_query,
    'maxResults': 10  # Adjust as needed
}

response = requests.get(f'{jira_url}/rest/api/2/myself', headers=headers)
time.sleep(0.5)

if response.status_code == 200:
    user_info = response.json()
    # print("Account ID:", user_info)


def clone_and_assign_issue(issue_key, issue_summary):
    create_issue_url = f'{jira_url}/rest/api/2/issue'
    issue_data = {
        "fields": {
           "project": {
               "key": "SDN"
           },
           "issuetype": {
               "name": "Story"
           },
           "summary": issue_summary,
           "assignee": {
               "name": "jluhrsen"
           },
           # story points
           "customfield_12310243": 1,
           "priority": {
               "name": "Normal"
           }
        }
    }
    clone_response = requests.post(create_issue_url, headers=headers, json=issue_data)
    time.sleep(0.5)

    if clone_response.status_code == 201:
        new_issue = clone_response.json()
        new_issue_key = new_issue['key']

        add_to_sprint_url = f'{jira_url}/rest/agile/1.0/sprint/{new_sprint_id}/issue'
        sprint_data = {
            "issues": [new_issue_key]
        }
        sprint_response = requests.post(add_to_sprint_url, headers=headers, json=sprint_data)
        time.sleep(0.5)
        if sprint_response.status_code == 204:
            print(f"Successfully cloned {issue_key} to {new_issue_key} and assigned to sprint {new_sprint_id}.")
        else:
            print(f"Failed to add {new_issue_key} to sprint. Response: {sprint_response.text}")
    else:
        print(f"Failed to clone {issue_key}. Response: {clone_response.text}")

# Make the GET request to search for issues
response = requests.get(api_url, headers=headers, params=params)
time.sleep(0.5)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    issues = response.json()['issues']
    # Loop through the issues and print details
    for issue in issues:
        print(f"Issue ID: {issue['id']}, Key: {issue['key']}, Summary: {issue['fields']['summary']}")
        clone_and_assign_issue(issue['key'], issue['fields']['summary'])
else:
    # Print the error if the request failed
    print(f"Failed to fetch issues, status code: {response.status_code}, response: {response.text}")

