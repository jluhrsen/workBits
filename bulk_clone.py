import requests
import json

print("set new sprint ID and comment out this exit. better yet, make sprint id a command line arg")
exit(1)

new_sprint_id = '60065'
jira_url = 'https://issues.redhat.com'
user = 'jluhrsen@redhat.com'
access_token = 'redacted'
api_url = f'{jira_url}/rest/api/2/search'
jql_query = 'text ~ "check network related component readiness" AND assignee = jluhrsen and Sprint = 57544'
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}
params = {
    'jql': jql_query,
    'maxResults': 10  # Adjust as needed
}

response = requests.get(f'{jira_url}/rest/api/2/myself', headers=headers)

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
    if clone_response.status_code == 201:
        new_issue = clone_response.json()
        new_issue_key = new_issue['key']

        add_to_sprint_url = f'{jira_url}/rest/agile/1.0/sprint/{new_sprint_id}/issue'
        sprint_data = {
            "issues": [new_issue_key]
        }
        sprint_response = requests.post(add_to_sprint_url, headers=headers, json=sprint_data)
        if sprint_response.status_code == 204:
            print(f"Successfully cloned {issue_key} to {new_issue_key} and assigned to sprint {new_sprint_id}.")
        else:
            print(f"Failed to add {new_issue_key} to sprint. Response: {sprint_response.text}")
    else:
        print(f"Failed to clone {issue_key}. Response: {clone_response.text}")

# Make the GET request to search for issues
response = requests.get(api_url, headers=headers, params=params)

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

