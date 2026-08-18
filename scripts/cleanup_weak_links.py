#!/usr/bin/env python3
"""
cleanup_weak_links.py — One-off data fix for the force-link bug.

Before the fix, `_link_problems_to_solutions` (pipelines/problem_solution.py)
linked every problem to its best-scoring solution even when that score was
below PROBLEM_SOLUTION_LINK_THRESHOLD, producing weak `problems_solutions`
rows that fed irrelevant orgs/projects into recommendations. The code no
longer creates these links, but rows written before the fix are still in the
database and keep affecting any problem reused via upsert_problem's 0.92
near-duplicate match. This script deletes those pre-existing weak rows.

Safe to run more than once (a no-op once nothing is below threshold).

Usage:
  python scripts/cleanup_weak_links.py           # show what would be deleted
  python scripts/cleanup_weak_links.py --apply   # actually delete
"""
import argparse
import os
import sys

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.config import DEFAULT_DATABASE_URL, get_database_url
from pipelines.problem_solution import PROBLEM_SOLUTION_LINK_THRESHOLD

load_dotenv()
DATABASE_URL = get_database_url(DEFAULT_DATABASE_URL)


def main():
    parser = argparse.ArgumentParser(description="Delete weak problems_solutions links")
    parser.add_argument("--apply", action="store_true", help="Actually delete (default: dry run)")
    args = parser.parse_args()

    try:
        conn = psycopg2.connect(DATABASE_URL)
    except psycopg2.OperationalError as exc:
        print("Could not connect to PostgreSQL.")
        print(f"DATABASE_URL: {DATABASE_URL}")
        raise SystemExit(1) from exc

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT COUNT(*) AS n FROM problems_solutions WHERE similarity_score < %s",
        (PROBLEM_SOLUTION_LINK_THRESHOLD,),
    )
    count = cur.fetchone()["n"]

    if count == 0:
        print("No weak links found. Nothing to do.")
        conn.close()
        return

    if not args.apply:
        print(f"Dry run: {count} problems_solutions row(s) have similarity_score < {PROBLEM_SOLUTION_LINK_THRESHOLD}.")
        print("Re-run with --apply to delete them.")
        conn.close()
        return

    cur.execute(
        "DELETE FROM problems_solutions WHERE similarity_score < %s",
        (PROBLEM_SOLUTION_LINK_THRESHOLD,),
    )
    conn.commit()
    print(f"Deleted {count} weak problems_solutions row(s).")
    conn.close()


if __name__ == "__main__":
    main()
