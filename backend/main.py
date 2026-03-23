"""Orchestrator: runs gather -> evaluate -> aggregate in sequence.
Copies results.json to frontend/public/ when done.
"""

import shutil
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
FRONTEND_PUBLIC = Path(__file__).resolve().parent.parent / "frontend" / "public"


def main():
    skip_gather = "--skip-gather" in sys.argv
    skip_eval = "--skip-eval" in sys.argv

    if not skip_gather:
        print("=" * 60)
        print("Step 1/3: Gathering data from GitHub...")
        print("=" * 60)
        from gather import gather
        gather()
    else:
        print("Skipping gather (using existing raw_data.json)")

    if not skip_eval:
        print("\n" + "=" * 60)
        print("Step 2/3: Evaluating with LLM...")
        print("=" * 60)
        from evaluate import run
        run()
    else:
        print("Skipping evaluation (using existing scored_data.json)")

    print("\n" + "=" * 60)
    print("Step 3/3: Aggregating results...")
    print("=" * 60)
    from aggregate import aggregate
    aggregate()

    # Copy results to frontend
    results_src = DATA_DIR / "results.json"
    if results_src.exists() and FRONTEND_PUBLIC.exists():
        dest = FRONTEND_PUBLIC / "results.json"
        shutil.copy2(results_src, dest)
        print(f"\nCopied results.json to {dest}")
    elif not FRONTEND_PUBLIC.exists():
        print(f"\nWarning: Frontend public dir not found at {FRONTEND_PUBLIC}")
        print("Copy backend/data/results.json to frontend/public/results.json manually.")

    print("\nPipeline complete!")


if __name__ == "__main__":
    main()
