"""Service 3: Aggregator
Computes per-engineer composite scores from scored PR and review data.
Reads scored_data.json (Contract B), outputs results.json (Contract C).
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

DATA_DIR = Path(__file__).resolve().parent / "data"
INPUT_FILE = DATA_DIR / "scored_data.json"
RAW_DATA_FILE = DATA_DIR / "raw_data.json"
OUTPUT_FILE = DATA_DIR / "results.json"

# Pillar weights
W_CONTRIBUTION = 0.40
W_REVIEW = 0.25
W_VELOCITY = 0.20
W_BREADTH = 0.15

# PostHog codebase zones (non-overlapping)
ZONE_PREFIXES = [
    ("frontend/", "Frontend (React/TS)"),
    ("posthog/api/", "Backend API"),
    ("posthog/models/", "Data Models"),
    ("ee/", "Enterprise/Analytics"),
    ("plugin-server/", "Plugin System"),
    ("posthog/tasks/", "Background Tasks"),
    ("posthog/management/", "Django Management"),
    ("posthog/queries/", "Query Engine"),
    ("posthog/hogql/", "HogQL"),
    ("rust/", "Rust Services"),
]

TOP_N = 5


def get_zone(file_path: str) -> str | None:
    for prefix, zone_name in ZONE_PREFIXES:
        if file_path.startswith(prefix):
            return prefix
    return None


def parse_iso(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def compute_velocity_from_raw(raw_data: dict) -> dict[str, dict]:
    """Compute review turnaround and feedback incorporation times from raw PR data."""
    review_turnarounds = defaultdict(list)  # reviewer -> [hours]
    feedback_times = defaultdict(list)  # pr_author -> [hours]

    for pr in raw_data.get("pull_requests", []):
        pr_created = parse_iso(pr["created_at"])
        reviews = pr.get("reviews", [])

        for review in reviews:
            reviewer = review["author"]
            submitted = parse_iso(review["submitted_at"])

            # Review turnaround: time from PR creation to review
            # (approximation — ideally we'd use review request time, but GraphQL doesn't expose it easily)
            hours = (submitted - pr_created).total_seconds() / 3600
            if 0 < hours < 720:  # ignore if > 30 days (stale)
                review_turnarounds[reviewer].append(hours)

        # Feedback incorporation: time between CHANGES_REQUESTED and next review's APPROVED
        changes_requested_at = None
        for review in sorted(reviews, key=lambda r: r["submitted_at"]):
            if review["state"] == "CHANGES_REQUESTED":
                changes_requested_at = parse_iso(review["submitted_at"])
            elif review["state"] == "APPROVED" and changes_requested_at:
                hours = (parse_iso(review["submitted_at"]) - changes_requested_at).total_seconds() / 3600
                if 0 < hours < 720:
                    feedback_times[pr["author"]].append(hours)
                changes_requested_at = None

    result = {}
    all_users = set(review_turnarounds.keys()) | set(feedback_times.keys())
    for user in all_users:
        rt_hours = review_turnarounds.get(user, [])
        fi_hours = feedback_times.get(user, [])
        result[user] = {
            "median_review_turnaround_hours": round(median(rt_hours), 1) if rt_hours else None,
            "median_feedback_incorporation_hours": round(median(fi_hours), 1) if fi_hours else None,
        }
    return result


def velocity_score(median_hours: float | None, max_hours: float = 48) -> float:
    """Convert median hours to a 0-100 score. Lower hours = higher score."""
    if median_hours is None:
        return 50.0  # neutral default
    clamped = max(0, min(median_hours, max_hours))
    return round(100 * (1 - clamped / max_hours), 1)


def normalize_scores(values: dict[str, float]) -> dict[str, float]:
    """Normalize to 0-100 where max gets 100."""
    if not values:
        return {}
    max_val = max(values.values())
    if max_val == 0:
        return {k: 0.0 for k in values}
    return {k: round(v / max_val * 100, 1) for k, v in values.items()}


def aggregate():
    print("Loading scored data...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        scored_data = json.load(f)

    print("Loading raw data for velocity calculations...")
    with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    pr_scores = scored_data["pr_scores"]
    review_scores = scored_data["review_scores"]

    # --- Pillar 1: Contribution Impact ---
    print("Computing Pillar 1: Contribution Impact...")
    contribution_raw = defaultdict(float)
    contribution_prs = defaultdict(list)
    contribution_types = defaultdict(lambda: defaultdict(int))
    author_avatars = {}

    for ps in pr_scores:
        author = ps["author"]
        contribution_raw[author] += ps["composite"]
        contribution_prs[author].append(ps)
        contribution_types[author][ps.get("type_classification", "feature")] += 1
        # Track avatar from first PR seen
        if author not in author_avatars:
            # Extract avatar from raw data
            for pr in raw_data["pull_requests"]:
                if pr["author"] == author:
                    author_avatars[author] = pr.get("author_avatar_url", "")
                    break

    contribution_normalized = normalize_scores(contribution_raw)

    # --- Pillar 2: Review Impact ---
    print("Computing Pillar 2: Review Impact...")
    review_raw = defaultdict(float)
    review_items = defaultdict(list)

    for rs in review_scores:
        reviewer = rs["reviewer"]
        review_raw[reviewer] += rs["weighted_composite"]
        review_items[reviewer].append(rs)

    review_normalized = normalize_scores(review_raw)

    # --- Pillar 3: Collaboration Velocity ---
    print("Computing Pillar 3: Collaboration Velocity...")
    velocity_data = compute_velocity_from_raw(raw_data)

    velocity_scores_map = {}
    for user, vdata in velocity_data.items():
        rt_score = velocity_score(vdata["median_review_turnaround_hours"])
        fi_score = velocity_score(vdata["median_feedback_incorporation_hours"])
        velocity_scores_map[user] = round(rt_score * 0.6 + fi_score * 0.4, 1)

    # --- Pillar 4: Codebase Breadth ---
    print("Computing Pillar 4: Codebase Breadth...")
    total_zones = len(set(prefix for prefix, _ in ZONE_PREFIXES))
    user_zones = defaultdict(set)

    for ps in pr_scores:
        author = ps["author"]
        for fp in ps.get("files_changed", []):
            zone = get_zone(fp)
            if zone:
                user_zones[author].add(zone)

    breadth_scores = {}
    for user, zones in user_zones.items():
        breadth_scores[user] = round(len(zones) / total_zones * 100, 1)

    # --- Final Score ---
    print("Computing final scores...")
    all_users = set(contribution_normalized.keys()) | set(review_normalized.keys())

    engineer_scores = {}
    for user in all_users:
        c = contribution_normalized.get(user, 0)
        r = review_normalized.get(user, 0)
        v = velocity_scores_map.get(user, 50)
        b = breadth_scores.get(user, 0)

        final = round(c * W_CONTRIBUTION + r * W_REVIEW + v * W_VELOCITY + b * W_BREADTH, 1)
        engineer_scores[user] = {
            "final_score": final,
            "contribution": c,
            "review": r,
            "velocity": v,
            "breadth": b,
        }

    # Rank and take top N
    ranked = sorted(engineer_scores.items(), key=lambda x: x[1]["final_score"], reverse=True)

    engineers = []
    for rank, (user, scores) in enumerate(ranked[:TOP_N], 1):
        # Get top PRs
        user_prs = sorted(contribution_prs.get(user, []), key=lambda x: x["composite"], reverse=True)
        top_prs = []
        for ps in user_prs[:5]:
            top_prs.append({
                "number": ps["number"],
                "title": ps["title"],
                "url": ps["url"],
                "type_classification": ps.get("type_classification", "feature"),
                "composite": ps["composite"],
                "scores": ps["scores"],
                "one_line_summary": ps.get("one_line_summary", ps["title"]),
                "reasoning": ps.get("reasoning", ""),
            })

        # Get top reviews (deduplicate by PR — keep best review per PR)
        user_reviews = sorted(review_items.get(user, []), key=lambda x: x["weighted_composite"], reverse=True)
        top_reviews = []
        seen_pr_numbers = set()
        for rs in user_reviews:
            if rs["pr_number"] in seen_pr_numbers:
                continue
            seen_pr_numbers.add(rs["pr_number"])
            top_reviews.append({
                "pr_number": rs["pr_number"],
                "pr_title": rs["pr_title"],
                "url": f"https://github.com/PostHog/posthog/pull/{rs['pr_number']}",
                "weighted_composite": rs["weighted_composite"],
                "scores": rs["scores"],
                "reasoning": rs.get("reasoning", ""),
            })
            if len(top_reviews) >= 3:
                break

        # Dominant type
        types = contribution_types.get(user, {})
        dominant_type = max(types, key=types.get) if types else "feature"

        # Velocity details
        vdata = velocity_data.get(user, {})

        # Zones touched
        zones = sorted(user_zones.get(user, set()))

        avatar = author_avatars.get(user, f"https://github.com/{user}.png")

        engineers.append({
            "rank": rank,
            "login": user,
            "avatar_url": avatar,
            "final_score": scores["final_score"],
            "pillars": {
                "contribution_impact": {
                    "score": scores["contribution"],
                    "raw_total": round(contribution_raw.get(user, 0), 1),
                    "pr_count": len(contribution_prs.get(user, [])),
                    "dominant_type": dominant_type,
                },
                "review_impact": {
                    "score": scores["review"],
                    "raw_total": round(review_raw.get(user, 0), 1),
                    "review_count": len(review_items.get(user, [])),
                },
                "collaboration_velocity": {
                    "score": scores["velocity"],
                    "median_review_turnaround_hours": vdata.get("median_review_turnaround_hours"),
                    "median_feedback_incorporation_hours": vdata.get("median_feedback_incorporation_hours"),
                },
                "codebase_breadth": {
                    "score": scores["breadth"],
                    "zones_touched": zones,
                    "zones_total": total_zones,
                },
            },
            "top_prs": top_prs,
            "top_reviews": top_reviews,
        })

    # Build result
    metadata = raw_data.get("metadata", {})
    result = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": {
                "start": metadata.get("period_start", ""),
                "end": metadata.get("period_end", ""),
            },
            "total_prs_analyzed": len(pr_scores),
            "total_engineers": len(all_users),
            "model_used": scored_data.get("metadata", {}).get("model_used", "unknown"),
        },
        "methodology": {
            "summary": "Impact scored across 4 pillars: Contribution (40%), Review (25%), Velocity (20%), Breadth (15%)",
            "pillars": {
                "contribution_impact": {
                    "weight": W_CONTRIBUTION,
                    "description": "Sum of PR quality scores (complexity, scope, type, risk, novelty). Quality over quantity.",
                    "pr_formula": "complexity*0.25 + scope*0.30 + type_weight*0.20 + risk*0.15 + novelty*0.10",
                },
                "review_impact": {
                    "weight": W_REVIEW,
                    "description": "Sum of review quality scores, weighted by the importance of the PR being reviewed.",
                    "review_formula": "(depth*0.40 + detection*0.35 + constructiveness*0.25) * pr_impact/10",
                },
                "collaboration_velocity": {
                    "weight": W_VELOCITY,
                    "description": "How quickly an engineer reviews others' code and incorporates feedback on their own.",
                },
                "codebase_breadth": {
                    "weight": W_BREADTH,
                    "description": "Number of distinct codebase zones (frontend, backend API, models, analytics, etc.) touched.",
                },
            },
            "final_formula": "contribution*0.40 + review*0.25 + velocity*0.20 + breadth*0.15 -> 0-100",
        },
        "engineers": engineers,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Top {TOP_N} engineers saved to {OUTPUT_FILE}")
    for eng in engineers:
        print(f"  #{eng['rank']} {eng['login']}: {eng['final_score']}")

    return result


if __name__ == "__main__":
    aggregate()
