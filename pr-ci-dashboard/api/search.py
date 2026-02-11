"""PR search via GitHub CLI."""
import subprocess
import json


def search_prs(query: str, page: int = 1, per_page: int = 10) -> dict:
    """
    Search PRs using GitHub CLI.

    Returns:
        {
            "prs": [
                {
                    "number": 123,
                    "title": "...",
                    "owner": "openshift",
                    "repo": "ovn-kubernetes",
                    "author": "user",
                    "created_at": "2024-01-01T00:00:00Z",
                    "state": "OPEN"
                },
                ...
            ],
            "total": 47
        }
    """
    try:
        # Use gh search to find PRs
        # Format: owner/repo#number
        result = subprocess.run(
            ["gh", "search", "prs", query, "--limit", str(per_page), "--json", "number,title,repository,author,createdAt,state"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return {"error": result.stderr, "prs": [], "total": 0}

        raw_prs = json.loads(result.stdout)

        # Transform to our format
        prs = []
        for pr in raw_prs:
            repo_full = pr.get("repository", {})
            owner = repo_full.get("owner", {}).get("login", "")
            repo = repo_full.get("name", "")

            prs.append({
                "number": pr.get("number"),
                "title": pr.get("title", ""),
                "owner": owner,
                "repo": repo,
                "author": pr.get("author", {}).get("login", ""),
                "created_at": pr.get("createdAt", ""),
                "state": pr.get("state", "UNKNOWN")
            })

        return {"prs": prs, "total": len(prs)}

    except Exception as e:
        return {"error": str(e), "prs": [], "total": 0}
