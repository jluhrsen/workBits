import argparse
import requests
import json

parser = argparse.ArgumentParser(description='Find Jira sprint ID by name.')
parser.add_argument('sprint_name', type=str, help='Name of the sprint to find')
args = parser.parse_args()
sprint_name = args.sprint_name

try:
    with open('./jira_token', 'r') as file:
        access_token = file.read().strip()
except FileNotFoundError:
    print(f"Error: The file ./jira_token was not found.")
    exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)

JIRA_URL = 'https://issues.redhat.com'
BOARD_ID = '19143'
sprints_url = f'{JIRA_URL}/rest/agile/1.0/board/{BOARD_ID}/sprint'
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

# Fetch sprints for the specified board
start_at = 0
max_results = 50
sprints = []

while True:
    response = requests.get(f'{sprints_url}?startAt={start_at}&maxResults={max_results}', headers=headers)
    if response.status_code == 200:
        data = response.json().get('values', [])
        if not data:
            break
        sprints.extend(data)
        start_at += max_results
        if response.json().get('isLast', False):
            break
    else:
        print(f'Failed to fetch sprints: {response.status_code} - {response.text}')
        print(f'Response: {response.json()}')
        exit(1)

# Check if any sprints were fetched
if sprints:
    for sprint in sprints:
        if sprint['name'] == sprint_name:
            sprint_id = sprint['id']
            print(f'Sprint ID for "{sprint_name}": {sprint_id}')
            break
    else:
        print(f'No sprint found with the name "{sprint_name}"')
else:
    print(f'No sprints were fetched.')

