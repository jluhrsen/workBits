---
name: jira
description: Use when interacting with Jira - querying issues, creating tickets, updating status, searching, or any Atlassian Jira Cloud operations
---

# Jira Cloud Integration

## Configuration

- **Instance:** `https://redhat.atlassian.net`
- **Username:** `jluhrsen@redhat.com`
- **Token file:** `/home/jamoluhrsen/repos/RedHat/workBits/atlassian_token`
- **API base:** `https://redhat.atlassian.net/rest/api/3`
- **Account ID:** `712020:b94122c9-36dc-4439-a554-3b2f0a115212`
- **Dashboard:** "My Sprint & Backlog" (ID 24616) — sprint and backlog view
- **Key projects:** OCPBUGS (OpenShift Bugs), CORENET (OpenShift Core Networking)

## Authentication

All requests use `curl -u` with the username and API token (strip trailing newline from token file):

```bash
TOKEN=$(cat /home/jamoluhrsen/repos/RedHat/workBits/atlassian_token | tr -d '\n')

curl -s -u "jluhrsen@redhat.com:$TOKEN" \
     -H "Content-Type: application/json" \
     "https://redhat.atlassian.net/rest/api/3/..."
```

## Common Operations

### Search issues (JQL)

**Must use POST to `/rest/api/3/search/jql`** (the old GET `/search` endpoint has been removed):

```bash
curl -s -X POST -u "jluhrsen@redhat.com:$TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "jql": "project = MYPROJECT AND status = Open",
       "maxResults": 50,
       "fields": ["summary", "status", "assignee", "priority", "created"]
     }' \
     "https://redhat.atlassian.net/rest/api/3/search/jql"
```

### Get a single issue

```bash
curl -s -u "jluhrsen@redhat.com:$TOKEN" \
     "https://redhat.atlassian.net/rest/api/3/issue/PROJECT-123"
```

### Create an issue

```bash
curl -s -X POST -u "jluhrsen@redhat.com:$TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "fields": {
         "project": {"key": "PROJECT"},
         "summary": "Issue title",
         "description": {
           "type": "doc",
           "version": 1,
           "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Description here"}]}]
         },
         "issuetype": {"name": "Bug"}
       }
     }' \
     "https://redhat.atlassian.net/rest/api/3/issue"
```

### Add a comment

```bash
curl -s -X POST -u "jluhrsen@redhat.com:$TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "body": {
         "type": "doc",
         "version": 1,
         "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Comment text"}]}]
       }
     }' \
     "https://redhat.atlassian.net/rest/api/3/issue/PROJECT-123/comment"
```

### Transition an issue (change status)

First get available transitions:
```bash
curl -s -u "jluhrsen@redhat.com:$TOKEN" \
     "https://redhat.atlassian.net/rest/api/3/issue/PROJECT-123/transitions"
```

Then apply one:
```bash
curl -s -X POST -u "jluhrsen@redhat.com:$TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"transition": {"id": "31"}}' \
     "https://redhat.atlassian.net/rest/api/3/issue/PROJECT-123/transitions"
```

### List projects

```bash
curl -s -u "jluhrsen@redhat.com:$TOKEN" \
     "https://redhat.atlassian.net/rest/api/3/project/search?maxResults=50"
```

### Assign an issue

```bash
curl -s -X PUT -u "jluhrsen@redhat.com:$TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"accountId": "ACCOUNT_ID"}' \
     "https://redhat.atlassian.net/rest/api/3/issue/PROJECT-123/assignee"
```

## Notes

- API v3 uses Atlassian Document Format (ADF) for description/comment bodies (the JSON `doc` format shown above)
- JQL reference: `project`, `status`, `assignee`, `priority`, `created`, `updated`, `labels`, `component`, `sprint`, `fixVersion`
- Use `maxResults` and `startAt` for pagination
- Rate limits apply; batch operations should include small delays
