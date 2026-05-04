---
name: jira
description: Interact with Jira - query issues, create tickets, update status, search on redhat.atlassian.net
---

# Jira Cloud Integration Reference

Use this skill when interacting with Jira — querying issues, creating tickets, updating status, searching, or any Atlassian Jira Cloud operations on `redhat.atlassian.net`.

## Authentication

**Token-based authentication** via curl:
```bash
curl -u "jluhrsen@redhat.com:$(cat ~/repos/workBits/atlassian_token)" \
  -H "Content-Type: application/json" \
  <JIRA_API_ENDPOINT>
```

- Token file: `~/repos/workBits/atlassian_token`
- Email: `jluhrsen@redhat.com`
- Format: `email:api_token` (email + colon + token from file)
- Base URL: `https://redhat.atlassian.net/rest/api/3/`

## Key Operations

### JQL Search
```bash
curl -u "jluhrsen@redhat.com:$(cat ~/repos/workBits/atlassian_token)" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "jql": "project = OCPBUGS AND status = Open",
    "maxResults": 50,
    "fields": ["summary", "status", "assignee", "created"]
  }' \
  "https://redhat.atlassian.net/rest/api/3/search/jql"
```

### Get Issue
```bash
curl -u "jluhrsen@redhat.com:$(cat ~/repos/workBits/atlassian_token)" \
  "https://redhat.atlassian.net/rest/api/3/issue/OCPBUGS-12345"
```

### Create Issue
```bash
curl -u "jluhrsen@redhat.com:$(cat ~/repos/workBits/atlassian_token)" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "project": {"key": "OCPBUGS"},
      "summary": "Bug summary",
      "description": {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Description"}]}]
      },
      "issuetype": {"name": "Bug"}
    }
  }' \
  "https://redhat.atlassian.net/rest/api/3/issue"
```

### Add Comment
```bash
curl -u "jluhrsen@redhat.com:$(cat ~/repos/workBits/atlassian_token)" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "body": {
      "type": "doc",
      "version": 1,
      "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Comment text"}]}]
    }
  }' \
  "https://redhat.atlassian.net/rest/api/3/issue/OCPBUGS-12345/comment"
```

### Transition Issue (Change Status)
```bash
# First get available transitions
curl -u "jluhrsen@redhat.com:$(cat ~/repos/workBits/atlassian_token)" \
  "https://redhat.atlassian.net/rest/api/3/issue/OCPBUGS-12345/transitions"

# Then transition to new status
curl -u "jluhrsen@redhat.com:$(cat ~/repos/workBits/atlassian_token)" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "transition": {"id": "transition_id_from_above"}
  }' \
  "https://redhat.atlassian.net/rest/api/3/issue/OCPBUGS-12345/transitions"
```

### Assign Issue
```bash
curl -u "jluhrsen@redhat.com:$(cat ~/repos/workBits/atlassian_token)" \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "user_account_id"
  }' \
  "https://redhat.atlassian.net/rest/api/3/issue/OCPBUGS-12345/assignee"
```

### List Projects
```bash
curl -u "jluhrsen@redhat.com:$(cat ~/repos/workBits/atlassian_token)" \
  "https://redhat.atlassian.net/rest/api/3/project"
```

## Key Projects

- **OCPBUGS** - OpenShift Bugs
- **CORENET** - OpenShift Core Networking

## Important Notes

- **Atlassian Document Format (ADF)** is required for `description` and `body` fields in issues and comments
- ADF structure:
  ```json
  {
    "type": "doc",
    "version": 1,
    "content": [
      {
        "type": "paragraph",
        "content": [
          {"type": "text", "text": "Your text here"}
        ]
      }
    ]
  }
  ```
- Always check token file exists before making API calls
- Use `-sS` with curl for clean output (silent but show errors)
- JQL queries support complex filtering: `project = OCPBUGS AND assignee = currentUser() AND status != Closed`

## Common JQL Patterns

- My open issues: `assignee = currentUser() AND status != Closed`
- Recent bugs: `project = OCPBUGS AND created >= -7d ORDER BY created DESC`
- High priority: `project = OCPBUGS AND priority = High AND status = Open`
- By component: `project = OCPBUGS AND component = "OVN Kubernetes"`
