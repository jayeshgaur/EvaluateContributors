# Engineering Impact Dashboard

Identifies the top 5 most impactful engineers at [PostHog](https://github.com/PostHog/posthog) by analyzing 90 days of GitHub activity — not by counting lines of code or commits, but by evaluating the **quality and substance** of each contribution using LLM-scored metrics.

**Live dashboard:** [_[Vercel deployment URL]_](https://workweave-gules.vercel.app/)

---

## How It Works

Every merged PR and code review is scored by Claude Haiku across multiple dimensions (complexity, scope, risk, novelty, review depth, etc.). These scores feed into four pillars that compose a final 0-100 impact score:

| Pillar | Weight | What It Captures |
|---|---|---|
| **Contribution Impact** | 40% | Quality of authored PRs — a single high-impact feature outweighs 20 trivial fixes |
| **Review Impact** | 25% | Depth and value of code reviews, weighted by the importance of the PR being reviewed |
| **Collaboration Velocity** | 20% | How quickly an engineer reviews others' code and incorporates feedback |
| **Codebase Breadth** | 15% | Range of codebase areas touched (frontend, backend, analytics, etc.) |

Every score is **verifiable**: click any engineer to see their top PRs with individual dimension scores, LLM reasoning, and direct GitHub links for manual spot-checking.

---

## Architecture

```
gather.py ──raw_data.json──> evaluate.py ──scored_data.json──> aggregate.py ──results.json──> Next.js Frontend
```

Four decoupled services connected by JSON contracts:

| Service | File | What It Does |
|---|---|---|
| **Gatherer** | `backend/gather.py` | Fetches 90 days of merged PRs from PostHog via GitHub GraphQL Search API |
| **Evaluator** | `backend/evaluate.py` | Scores each PR (5 dimensions) and review (3 dimensions) using Claude Haiku |
| **Aggregator** | `backend/aggregate.py` | Computes per-engineer pillar scores, normalizes, ranks top 5 |
| **Frontend** | `frontend/` | Next.js + Tailwind single-page dashboard, reads static JSON |

**Tech stack:** Python 3.11+, Next.js 16, Tailwind CSS, Claude Haiku (via Anthropic SDK), GitHub GraphQL API

---

## Setup & Usage

### Prerequisites
- Python 3.11+
- Node.js 18+
- GitHub personal access token (read access to public repos)
- Anthropic API key

### 1. Clone & configure
```bash
git clone git@github.com:jayeshgaur/EvaluateContributors.git
cd EvaluateContributors
cp .env.example .env
# Edit .env with your GITHUB_TOKEN and ANTHROPIC_API_KEY
```

### 2. Install dependencies
```bash
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

### 3. Run the pipeline
```bash
cd backend
python main.py              # Runs: gather -> evaluate -> aggregate
# Or run individual steps:
python gather.py             # Just fetch GitHub data
python main.py --skip-gather # Skip fetch, re-run evaluation + aggregation
python main.py --skip-gather --skip-eval  # Just re-aggregate
```

The pipeline outputs `backend/data/results.json` and copies it to `frontend/public/results.json`.

### 4. Preview locally
```bash
cd frontend
npm run dev
# Open http://localhost:3000
```

### 5. Deploy to Vercel
Deploy. The dashboard is fully static — no API calls at runtime.

---

## Scoring Methodology

### PR Scoring (5 dimensions, each 1-10)
Each merged PR is evaluated by the LLM on:
- **Complexity** — Technical difficulty (typo fix = 1, new subsystem = 10)
- **Scope of Impact** — How broadly it affects the product (cosmetic = 1, core pipeline = 10)
- **Type Weight** — Inherent value of the work (dep bump = 1, feature/critical bugfix = 10)
- **Risk & Judgment** — Engineering judgment required (safe/isolated = 1, data migration = 10)
- **Novelty** — New capability vs maintenance (routine = 1, net-new = 10)

**PR composite:** `complexity*0.25 + scope*0.30 + type_weight*0.20 + risk*0.15 + novelty*0.10`

### Review Scoring (3 dimensions, each 1-10)
Each non-trivial code review is scored on:
- **Review Depth** — Rubber stamp (1) vs architectural feedback (10)
- **Issue Detection** — No issues raised (1) vs caught real bugs (10)
- **Constructiveness** — No actionable feedback (1) vs problems + solutions (10)

Reviews are weighted by the importance of the parent PR: reviewing a critical PR deeply counts more.

### Final Score
```
final = contribution*0.40 + review*0.25 + velocity*0.20 + breadth*0.15
```
Normalized to 0-100 across all engineers.

---

## Future Improvements

### 1. Smarter LLM Calling
The current approach sends one LLM call per batch of 6 PRs with raw PR metadata. This works but is suboptimal:

- **Pre-process before sending to LLM.** Strip boilerplate from PR descriptions (template headers, checklists), remove auto-generated file paths (lock files, snapshots), and truncate diffs to the most informative parts. This reduces token count per call significantly.
- **Group similar PRs.** PRs touching the same subsystem could be batched together, giving the LLM better context for relative scoring within a domain.
- **Cache scored results.** If a PR was already scored in a previous run, skip it. Only score new/updated PRs. This makes re-runs near-instant.
- **Two-pass scoring.** First pass: fast heuristic classification (feature vs docs vs deps) to separate high-value PRs from trivial ones. Second pass: LLM-score only the high-value subset with a more capable model (Sonnet) for better reasoning quality.

### 2. Data Cleaning Before Evaluation
The gatherer currently dumps raw GitHub API data into JSON. Better preprocessing would improve LLM accuracy and reduce cost:

- **Normalize file paths** to canonical codebase zones before sending to the LLM, so it doesn't waste tokens parsing paths.
- **Deduplicate reviews** at the data layer — same reviewer on the same PR should be merged into a single review record capturing the full arc (requested changes -> approved).
- **Pre-classify PR types heuristically** using labels, file paths, and title patterns (e.g., `chore:`, `fix:`, `feat:`) before LLM scoring. The LLM then validates/overrides rather than classifying from scratch.
- **Filter trivial PRs** (< 5 lines changed, only touching config/lock files) before they ever reach the LLM — assign minimum scores deterministically.

### 3. Better Metrics
The current four-pillar model captures the basics but misses some dimensions of engineering impact:

- **Cross-PR impact analysis.** Track PR dependency chains — an engineer whose foundational PR unblocks 5 subsequent PRs by others has outsized impact not captured by individual PR scores.
- **Issue linkage.** Connect PRs to GitHub issues to measure bug fix rate, feature delivery throughput, and whether the engineer is working on high-priority items.
- **Team-level contribution.** Identify engineers who mentor others through PR reviews that lead to measurable code quality improvements over time.
- **Temporal consistency.** Distinguish sustained contributors from burst contributors — an engineer consistently shipping weekly has different impact than one big PR followed by silence.
- **Domain expertise scoring.** Rather than just breadth, measure depth — an engineer who becomes the domain expert for a critical subsystem and maintains it reliably is highly impactful.
