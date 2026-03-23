"""Service 2: LLM Evaluator
Scores PRs and reviews using Claude Haiku.
Reads raw_data.json (Contract A), outputs scored_data.json (Contract B).
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATA_DIR = Path(__file__).resolve().parent / "data"
INPUT_FILE = DATA_DIR / "raw_data.json"
OUTPUT_FILE = DATA_DIR / "scored_data.json"

MODEL = "claude-haiku-4-5-20251001"
PR_BATCH_SIZE = 6
REVIEW_BATCH_SIZE = 8
MAX_CONCURRENT = 2
MAX_RETRIES = 3

PR_SCORING_PROMPT = """You are an engineering impact evaluator analyzing Pull Requests from the PostHog open-source repository (a product analytics platform).

For EACH PR below, provide scores on a 1-10 scale:

1. complexity: Technical difficulty of the change
   1=trivial (typo, version bump) 5=moderate (new endpoint, logic change) 10=architectural (new subsystem, complex algorithm, data migration)

2. scope_of_impact: How broadly this affects the product
   1=internal/cosmetic 5=single feature area 10=core pipeline, affects all users

3. type_weight: Inherent value of this type of work
   1=dependency bump/formatting 3=docs/config 5=tests/minor bugfix 7=refactor/perf 9=feature 10=critical bugfix/security

4. risk_and_judgment: Engineering judgment required
   1=safe, isolated 5=moderate shared-code risk 10=migration, data integrity, backward-compat

5. novelty: New capability vs maintenance
   1=routine maintenance 5=enhancement of existing 10=net-new capability

Also provide:
- type_classification: exactly one of: feature, bugfix-critical, bugfix-minor, refactor, performance, tests, docs, config-infra, dependencies
- one_line_summary: Single sentence explaining what this PR does and why it matters
- reasoning: 2-3 sentences justifying your scores (an engineering leader should read this and agree)

Note: High line counts do NOT automatically mean high complexity. Auto-generated migrations, vendor updates, and schema dumps should score low even with thousands of lines.

If a PR description is missing, score based on title, file paths, and diff stats. Note limited info in reasoning.

Respond with a JSON array of objects, one per PR, with keys: pr_number, complexity, scope_of_impact, type_weight, risk_and_judgment, novelty, type_classification, one_line_summary, reasoning.

=== PRs to evaluate ===
"""

REVIEW_SCORING_PROMPT = """You are evaluating the quality of code reviews on the PostHog repository.

For each review below, score on a 1-10 scale:

1. review_depth: How substantive was this review?
   1="LGTM"/rubber stamp 5=specific comments on logic 10=identifies architectural issues, suggests alternatives

2. issue_detection: Did the reviewer catch real problems?
   1=no issues raised 5=style/naming issues 10=bugs, race conditions, security

3. constructiveness: Did the review help the author improve?
   1=no actionable feedback 5=pointed out problems 10=pointed out problems AND suggested solutions

Also provide:
- reasoning: 1-2 sentences explaining your assessment

Respond with a JSON array of objects, one per review, with keys: review_id, review_depth, issue_detection, constructiveness, reasoning.

=== Reviews to evaluate ===
"""


def format_pr_for_prompt(pr: dict) -> str:
    files_summary = []
    for f in pr.get("files", [])[:20]:
        files_summary.append(f"  - {f['path']}")
    if len(pr.get("files", [])) > 20:
        remaining = len(pr["files"]) - 20
        dirs = set()
        for f in pr["files"][20:]:
            parts = f["path"].split("/")
            if len(parts) > 1:
                dirs.add(parts[0] + "/")
        files_summary.append(f"  ... ({remaining} more in {', '.join(sorted(dirs))})")

    files_str = "\n".join(files_summary) if files_summary else "  (no file data)"

    labels_str = ", ".join(pr.get("labels", [])) if pr.get("labels") else "none"

    review_summary = []
    for r in pr.get("reviews", [])[:5]:
        state = r["state"]
        body_preview = (r.get("body") or "")[:150]
        if body_preview:
            review_summary.append(f"  - {r['author']}: {state} - \"{body_preview}\"")
        else:
            review_summary.append(f"  - {r['author']}: {state}")
    reviews_str = "\n".join(review_summary) if review_summary else "  (no reviews)"

    body = (pr.get("body") or "").strip()
    body_str = body[:800] if body else "(no description)"

    return f"""PR #{pr['number']}: "{pr['title']}"
Author: {pr['author']}
Labels: [{labels_str}]
Description: {body_str}
Files changed ({pr.get('changed_files', len(pr.get('files', [])))}):
{files_str}
Stats: +{pr.get('additions', 0)} / -{pr.get('deletions', 0)}
Discussion comments: {pr.get('comment_count', 0)}
Reviews:
{reviews_str}
"""


def format_review_for_prompt(review: dict, pr: dict) -> str:
    body = (review.get("body") or "").strip()
    body_str = body[:400] if body else "(empty)"
    return f"""Review on PR #{pr['number']} "{pr['title']}" by @{review['author']}:
State: {review['state']}
Body: "{body_str}"
Inline comments: {review.get('comment_count', 0)}
PR context: +{pr.get('additions', 0)}/-{pr.get('deletions', 0)}, {pr.get('changed_files', 0)} files
"""


def is_trivial_review(review: dict) -> bool:
    body = (review.get("body") or "").strip().lower()
    if not body:
        return True
    trivial_phrases = ["lgtm", "looks good", "lg", "👍", ":+1:", "approved", "ship it", "🚀"]
    return body in trivial_phrases or len(body) < 10


def parse_json_response(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines)
        for i, line in enumerate(lines[1:], 1):
            if line.strip().startswith("```"):
                end = i
                break
        text = "\n".join(lines[start:end])
    return json.loads(text)


async def call_llm(client: anthropic.AsyncAnthropic, prompt: str, sem: asyncio.Semaphore) -> str:
    async with sem:
        for attempt in range(5):
            try:
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            except anthropic.RateLimitError:
                wait = 30 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                await asyncio.sleep(wait)
        raise Exception("Rate limit retries exhausted")


def compute_pr_composite(scores: dict) -> float:
    return round(
        scores["complexity"] * 0.25
        + scores["scope_of_impact"] * 0.30
        + scores["type_weight"] * 0.20
        + scores["risk_and_judgment"] * 0.15
        + scores["novelty"] * 0.10,
        2,
    )


def compute_review_composite(scores: dict) -> float:
    return round(
        scores["review_depth"] * 0.40
        + scores["issue_detection"] * 0.35
        + scores["constructiveness"] * 0.25,
        2,
    )


async def score_pr_batch(
    client: anthropic.AsyncAnthropic,
    batch: list[dict],
    sem: asyncio.Semaphore,
    batch_idx: int,
    total_batches: int,
) -> list[dict]:
    prompt = PR_SCORING_PROMPT
    for pr in batch:
        prompt += format_pr_for_prompt(pr) + "\n---\n"

    for attempt in range(MAX_RETRIES + 1):
        try:
            response_text = await call_llm(client, prompt, sem)
            parsed = parse_json_response(response_text)

            results = []
            pr_map = {pr["number"]: pr for pr in batch}

            for item in parsed:
                pr_num = item.get("pr_number")
                if pr_num not in pr_map:
                    continue

                scores = {
                    "complexity": max(1, min(10, int(item.get("complexity", 5)))),
                    "scope_of_impact": max(1, min(10, int(item.get("scope_of_impact", 5)))),
                    "type_weight": max(1, min(10, int(item.get("type_weight", 5)))),
                    "risk_and_judgment": max(1, min(10, int(item.get("risk_and_judgment", 5)))),
                    "novelty": max(1, min(10, int(item.get("novelty", 5)))),
                }

                pr = pr_map[pr_num]
                results.append({
                    "number": pr_num,
                    "author": pr["author"],
                    "title": pr["title"],
                    "url": f"https://github.com/PostHog/posthog/pull/{pr_num}",
                    "merged_at": pr["merged_at"],
                    "type_classification": item.get("type_classification", "feature"),
                    "scores": scores,
                    "composite": compute_pr_composite(scores),
                    "one_line_summary": item.get("one_line_summary", pr["title"]),
                    "reasoning": item.get("reasoning", ""),
                    "files_changed": [f["path"] for f in pr.get("files", [])],
                    "additions": pr.get("additions", 0),
                    "deletions": pr.get("deletions", 0),
                })

            print(f"  PR batch {batch_idx + 1}/{total_batches}: scored {len(results)}/{len(batch)} PRs")
            return results

        except (json.JSONDecodeError, KeyError) as e:
            if attempt < MAX_RETRIES:
                print(f"  PR batch {batch_idx + 1}: retry {attempt + 1} (parse error: {e})")
                continue
            print(f"  PR batch {batch_idx + 1}: failed after retries, using defaults")
            # Return default scores for the batch
            results = []
            for pr in batch:
                scores = {k: 5 for k in ["complexity", "scope_of_impact", "type_weight", "risk_and_judgment", "novelty"]}
                results.append({
                    "number": pr["number"],
                    "author": pr["author"],
                    "title": pr["title"],
                    "url": f"https://github.com/PostHog/posthog/pull/{pr['number']}",
                    "merged_at": pr["merged_at"],
                    "type_classification": "feature",
                    "scores": scores,
                    "composite": compute_pr_composite(scores),
                    "one_line_summary": pr["title"],
                    "reasoning": "LLM scoring failed; default scores applied.",
                    "files_changed": [f["path"] for f in pr.get("files", [])],
                    "additions": pr.get("additions", 0),
                    "deletions": pr.get("deletions", 0),
                })
            return results


async def score_review_batch(
    client: anthropic.AsyncAnthropic,
    batch: list[tuple[dict, dict]],  # (review, parent_pr) pairs
    pr_composites: dict[int, float],
    sem: asyncio.Semaphore,
    batch_idx: int,
    total_batches: int,
) -> list[dict]:
    prompt = REVIEW_SCORING_PROMPT
    for i, (review, pr) in enumerate(batch):
        prompt += f"[Review ID: {i}]\n"
        prompt += format_review_for_prompt(review, pr) + "\n---\n"

    for attempt in range(MAX_RETRIES + 1):
        try:
            response_text = await call_llm(client, prompt, sem)
            parsed = parse_json_response(response_text)

            results = []
            for item in parsed:
                rid = item.get("review_id")
                if rid is None or rid >= len(batch):
                    continue

                review, pr = batch[rid]
                scores = {
                    "review_depth": max(1, min(10, int(item.get("review_depth", 3)))),
                    "issue_detection": max(1, min(10, int(item.get("issue_detection", 3)))),
                    "constructiveness": max(1, min(10, int(item.get("constructiveness", 3)))),
                }

                pr_comp = pr_composites.get(pr["number"], 5.0)
                composite = compute_review_composite(scores)

                results.append({
                    "reviewer": review["author"],
                    "pr_number": pr["number"],
                    "pr_author": pr["author"],
                    "pr_title": pr["title"],
                    "pr_composite": pr_comp,
                    "submitted_at": review["submitted_at"],
                    "state": review["state"],
                    "scores": scores,
                    "composite": composite,
                    "weighted_composite": round(composite * (pr_comp / 10), 2),
                    "reasoning": item.get("reasoning", ""),
                })

            print(f"  Review batch {batch_idx + 1}/{total_batches}: scored {len(results)}/{len(batch)} reviews")
            return results

        except (json.JSONDecodeError, KeyError) as e:
            if attempt < MAX_RETRIES:
                print(f"  Review batch {batch_idx + 1}: retry {attempt + 1} (parse error: {e})")
                continue
            print(f"  Review batch {batch_idx + 1}: failed after retries, using defaults")
            results = []
            for review, pr in batch:
                scores = {"review_depth": 3, "issue_detection": 3, "constructiveness": 3}
                pr_comp = pr_composites.get(pr["number"], 5.0)
                composite = compute_review_composite(scores)
                results.append({
                    "reviewer": review["author"],
                    "pr_number": pr["number"],
                    "pr_author": pr["author"],
                    "pr_title": pr["title"],
                    "pr_composite": pr_comp,
                    "submitted_at": review["submitted_at"],
                    "state": review["state"],
                    "scores": scores,
                    "composite": composite,
                    "weighted_composite": round(composite * (pr_comp / 10), 2),
                    "reasoning": "LLM scoring failed; default scores applied.",
                })
            return results


async def evaluate():
    print("Loading raw data...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    prs = raw_data["pull_requests"]
    print(f"Loaded {len(prs)} PRs")

    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    # --- Phase 1: Score PRs ---
    print(f"\nPhase 1: Scoring PRs (batches of {PR_BATCH_SIZE})...")
    pr_batches = [prs[i : i + PR_BATCH_SIZE] for i in range(0, len(prs), PR_BATCH_SIZE)]
    total_pr_batches = len(pr_batches)

    pr_tasks = [
        score_pr_batch(client, batch, sem, idx, total_pr_batches)
        for idx, batch in enumerate(pr_batches)
    ]
    pr_results_nested = await asyncio.gather(*pr_tasks)
    all_pr_scores = [item for sublist in pr_results_nested for item in sublist]
    print(f"Scored {len(all_pr_scores)} PRs total")

    # Build PR composite lookup for review weighting
    pr_composites = {ps["number"]: ps["composite"] for ps in all_pr_scores}

    # --- Phase 2: Score Reviews ---
    print(f"\nPhase 2: Scoring reviews...")
    review_pairs = []  # (review, parent_pr) tuples
    trivial_reviews = []

    for pr in prs:
        for review in pr.get("reviews", []):
            if is_trivial_review(review):
                # Assign default scores without LLM call
                pr_comp = pr_composites.get(pr["number"], 5.0)
                scores = {"review_depth": 2, "issue_detection": 1, "constructiveness": 1}
                composite = compute_review_composite(scores)
                trivial_reviews.append({
                    "reviewer": review["author"],
                    "pr_number": pr["number"],
                    "pr_author": pr["author"],
                    "pr_title": pr["title"],
                    "pr_composite": pr_comp,
                    "submitted_at": review["submitted_at"],
                    "state": review["state"],
                    "scores": scores,
                    "composite": composite,
                    "weighted_composite": round(composite * (pr_comp / 10), 2),
                    "reasoning": "Approval/LGTM with no substantive comments",
                })
            else:
                review_pairs.append((review, pr))

    print(f"  {len(trivial_reviews)} trivial reviews (default scores)")
    print(f"  {len(review_pairs)} non-trivial reviews to score (batches of {REVIEW_BATCH_SIZE})")

    review_batches = [
        review_pairs[i : i + REVIEW_BATCH_SIZE]
        for i in range(0, len(review_pairs), REVIEW_BATCH_SIZE)
    ]
    total_review_batches = len(review_batches)

    review_tasks = [
        score_review_batch(client, batch, pr_composites, sem, idx, total_review_batches)
        for idx, batch in enumerate(review_batches)
    ]
    review_results_nested = await asyncio.gather(*review_tasks)
    llm_review_scores = [item for sublist in review_results_nested for item in sublist]

    all_review_scores = trivial_reviews + llm_review_scores
    print(f"Scored {len(all_review_scores)} reviews total")

    # --- Output ---
    result = {
        "metadata": {
            "model_used": MODEL,
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "total_prs_scored": len(all_pr_scores),
            "total_reviews_scored": len(all_review_scores),
        },
        "pr_scores": all_pr_scores,
        "review_scores": all_review_scores,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Saved scored data to {OUTPUT_FILE}")
    return result


def run():
    return asyncio.run(evaluate())


if __name__ == "__main__":
    run()
