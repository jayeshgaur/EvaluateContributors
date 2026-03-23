"""Service 1: GitHub Data Gatherer
Fetches 90 days of merged PRs from PostHog/posthog via GraphQL Search API.
Outputs raw_data.json (Contract A).
"""

import os
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO_OWNER = "PostHog"
REPO_NAME = "posthog"
DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_FILE = DATA_DIR / "raw_data.json"
DAYS_BACK = 90

BOT_PATTERNS = ["[bot]", "dependabot", "github-actions", "posthog-bot", "codecov"]

GRAPHQL_URL = "https://api.github.com/graphql"

# Use search API to get ALL merged PRs in date range (avoids UPDATED_AT ordering bug)
SEARCH_QUERY = """
query($searchQuery: String!, $cursor: String) {
  search(
    query: $searchQuery,
    type: ISSUE,
    first: 100,
    after: $cursor
  ) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        number
        title
        body
        author {
          login
          avatarUrl
        }
        labels(first: 10) {
          nodes { name }
        }
        createdAt
        mergedAt
        additions
        deletions
        changedFiles
        files(first: 50) {
          nodes {
            path
            additions
            deletions
          }
        }
        reviews(first: 30) {
          nodes {
            author { login }
            state
            body
            submittedAt
            comments { totalCount }
          }
        }
        comments {
          totalCount
        }
      }
    }
  }
}
"""


def is_bot(login: str) -> bool:
    if not login:
        return True
    login_lower = login.lower()
    return any(pattern in login_lower for pattern in BOT_PATTERNS)


def run_query(client: httpx.Client, query: str, variables: dict) -> dict:
    response = client.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    return data


def fetch_all_prs() -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    search_query = f"repo:{REPO_OWNER}/{REPO_NAME} is:pr is:merged merged:>={cutoff_str}"

    all_prs = []
    cursor = None
    page = 0
    seen_numbers = set()

    with httpx.Client() as client:
        while True:
            page += 1
            print(f"  Fetching page {page}...")

            variables = {"searchQuery": search_query}
            if cursor:
                variables["cursor"] = cursor

            data = run_query(client, SEARCH_QUERY, variables)
            search_result = data["data"]["search"]
            nodes = search_result["nodes"]

            for node in nodes:
                if not node:  # search can return null nodes
                    continue

                number = node.get("number")
                if not number or number in seen_numbers:
                    continue
                seen_numbers.add(number)

                author_login = node.get("author", {}).get("login") if node.get("author") else None
                if not author_login or is_bot(author_login):
                    continue

                avatar_url = node.get("author", {}).get("avatarUrl", "") if node.get("author") else ""

                files = []
                if node.get("files") and node["files"].get("nodes"):
                    for f in node["files"]["nodes"]:
                        files.append({
                            "path": f["path"],
                            "additions": f["additions"],
                            "deletions": f["deletions"],
                        })

                reviews = []
                if node.get("reviews") and node["reviews"].get("nodes"):
                    for r in node["reviews"]["nodes"]:
                        reviewer = r.get("author", {}).get("login") if r.get("author") else None
                        if not reviewer or is_bot(reviewer):
                            continue
                        reviews.append({
                            "author": reviewer,
                            "state": r["state"],
                            "body": (r.get("body") or "")[:500],
                            "submitted_at": r["submittedAt"],
                            "comment_count": r.get("comments", {}).get("totalCount", 0),
                        })

                labels = []
                if node.get("labels") and node["labels"].get("nodes"):
                    labels = [l["name"] for l in node["labels"]["nodes"]]

                pr = {
                    "number": number,
                    "title": node["title"],
                    "body": (node.get("body") or "")[:1500],
                    "author": author_login,
                    "author_avatar_url": avatar_url,
                    "labels": labels,
                    "created_at": node["createdAt"],
                    "merged_at": node["mergedAt"],
                    "additions": node.get("additions", 0),
                    "deletions": node.get("deletions", 0),
                    "changed_files": node.get("changedFiles", 0),
                    "files": files,
                    "reviews": reviews,
                    "comment_count": node.get("comments", {}).get("totalCount", 0),
                }
                all_prs.append(pr)

            print(f"    Found {len(all_prs)} PRs so far...")

            page_info = search_result["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

            # Respect rate limits
            time.sleep(1)

    return all_prs


def gather():
    print(f"Gathering merged PRs from {REPO_OWNER}/{REPO_NAME} (last {DAYS_BACK} days)...")

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    prs = fetch_all_prs()

    # Sort by merged date descending
    prs.sort(key=lambda x: x["merged_at"], reverse=True)

    result = {
        "metadata": {
            "repo": f"{REPO_OWNER}/{REPO_NAME}",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "period_start": cutoff.strftime("%Y-%m-%d"),
            "period_end": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total_prs": len(prs),
            "excluded_bots": BOT_PATTERNS,
        },
        "pull_requests": prs,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Done! Saved {len(prs)} PRs to {OUTPUT_FILE}")
    return result


if __name__ == "__main__":
    gather()
