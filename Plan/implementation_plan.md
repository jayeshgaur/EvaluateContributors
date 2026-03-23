# Engineering Impact Dashboard - Implementation Plan

## Context

**Problem:** Weave's coding assessment — analyze PostHog's GitHub repo (last 90 days) to identify the top 5 most impactful engineers. The key constraint: simple counts (LOC, commits, PRs) are NOT impact. They want creative, verifiable analysis. Single-page interactive dashboard deployed on Vercel.

**Core Insight:** Impact = the degree to which an engineer moves the product forward AND makes the team around them more effective. We decompose this into *direct contribution quality* and *multiplier effect* (reviews, unblocking, collaboration).

---

## Architecture Overview

Four independent services connected by JSON contracts:

```
Service 1 (gather.py) --raw_data.json--> Service 2 (evaluate.py) --scored_data.json--> Service 3 (aggregate.py) --results.json--> Service 4 (Next.js Frontend)
```

---

## Data Contracts

### Contract A: raw_data.json (Gatherer -> Evaluator)
- metadata: repo, collected_at, period_start/end, total_prs, excluded_bots
- pull_requests[]: number, title, body, author, author_avatar_url, labels, created_at, merged_at, additions, deletions, changed_files, files[{path, additions, deletions}], reviews[{author, state, body, submitted_at, comment_count}], comment_count

### Contract B: scored_data.json (Evaluator -> Aggregator)
- metadata: model_used, scored_at, total_prs_scored, total_reviews_scored
- pr_scores[]: number, author, title, url, merged_at, type_classification, scores{complexity, scope_of_impact, type_weight, risk_and_judgment, novelty}, composite, one_line_summary, reasoning, files_changed, additions, deletions
- review_scores[]: reviewer, pr_number, pr_author, pr_title, pr_composite, submitted_at, state, scores{review_depth, issue_detection, constructiveness}, composite, weighted_composite, reasoning

### Contract C: results.json (Aggregator -> Frontend)
- metadata: generated_at, period, total_prs_analyzed, total_engineers, model_used
- methodology: summary, pillars{contribution_impact, review_impact, collaboration_velocity, codebase_breadth}, final_formula
- engineers[]: rank, login, avatar_url, final_score, pillars{contribution_impact, review_impact, collaboration_velocity, codebase_breadth}, top_prs[], top_reviews[]

---

## Four Pillars of Impact

1. **Contribution Impact (40%)** - Sum of PR quality scores (complexity*0.25 + scope*0.30 + type_weight*0.20 + risk*0.15 + novelty*0.10)
2. **Review Impact (25%)** - Sum of review quality scores weighted by parent PR importance
3. **Collaboration Velocity (20%)** - Median review turnaround time + feedback responsiveness
4. **Codebase Breadth (15%)** - Number of distinct codebase zones touched

**Final Score:** contribution*0.40 + review*0.25 + velocity*0.20 + breadth*0.15 (0-100 scale)
