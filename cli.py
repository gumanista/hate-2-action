#!/usr/bin/env python3
import os
import sys
import sqlite3
import argparse

# ─── Make sure Python can import from “src/” ─────────────────────────────────
# (Since embed_and_match.py and problem_detector.py live in src/, we add that
# directory to sys.path at runtime.)
ROOT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(ROOT_DIR, "src")
sys.path.insert(0, SRC_DIR)

from src.embed_and_match import match_embeddings
from src.problem_detector import detect_problems
from src.output_generator import generate_output
from src.database import Database

DB_PATH = os.getenv("DB_PATH", "donation.db")


def cmd_init(args):
    """
    Precompute & save all embeddings for:
      1) solutions → vec_solutions
      2) projects  → vec_projects
      3) projects↔solutions → projects_solutions
    This calls match_embeddings with an empty list of problem IDs to trigger the “first-run” logic
    in embed_and_match.py (which populates all solution/project embeddings and the projects_solutions table).
    """
    print("🔨 Initializing embeddings for solutions & projects…")
    # Calling match_embeddings with an empty list forces initial population of solution/project embeddings
    _, _ = match_embeddings(DB_PATH, [])
    print("✅ Done: Embeddings for solutions & projects are ready.")


def cmd_run_id(args):
    """
    1) Fetch any unprocessed problems (is_processed = 0)
    2) Call match_embeddings(...) to embed & match them
    3) Print out which problems were processed and the aggregated recommended project_ids
    """
    with Database(DB_PATH) as db:
        cur = db.conn.cursor()
        cur.execute("SELECT problem_id FROM problems WHERE is_processed = 0;")
        rows = cur.fetchall()
        problem_ids = [r[0] for r in rows]
    if not problem_ids:
        print("— No new problems to process.")
        return

    print("🔍 Matching unprocessed problems…")
    sol_ids, proj_ids = match_embeddings(DB_PATH, problem_ids)

    print(f"⚙️  Problems processed: {problem_ids}")
    if proj_ids:
        print(f"🏷  Recommended projects (aggregated): {proj_ids}")
    else:
        print("— No matching projects found for these problems.")


def cmd_run(args):
    """
    Step‐by‐step pipeline:
    1) Insert a new message into `messages(...)` → get message_id.
    2) Detect problems for that message (inserting them into `problems`).
    3) Fetch all unprocessed problems (including the newly inserted ones) and pass them to match_embeddings().
    4) Link recommended project_ids into `message_projects(message_id, project_id)`.
    5) Print the recommended project_ids so that output_generator.py can be run separately.
    """
    with Database(DB_PATH) as db:
        # Step 1: Insert into messages
        message_id = db.add_message(args.user_id, args.username, args.chat_title, args.text)
        print(f"✉️  Stored new message as message_id={message_id}. Running problem detection…")

        # Step 2: Detect problems for this message
        problem_ids = detect_problems(DB_PATH, message_id)

        print("🔍 Matching new and existing unprocessed problems…")
        # Fetch all unprocessed problems (including the ones we just inserted)
        cur = db.conn.cursor()
        cur.execute("SELECT problem_id FROM problems WHERE is_processed = 0;")
        rows = cur.fetchall()
        all_problem_ids = [r[0] for r in rows]

        if all_problem_ids:
            sol_ids, proj_ids = match_embeddings(DB_PATH, all_problem_ids)
        else:
            sol_ids, proj_ids = [], []

        # Step 4: Link this message_id → recommended projects
        if proj_ids:
            for proj_id in proj_ids:
                cur.execute(
                    "INSERT OR IGNORE INTO message_projects (message_id, project_id) VALUES (?, ?)",
                    (message_id, proj_id)
                )
            db.conn.commit()
            print(f"🏷  Linked message {message_id} to projects: {proj_ids}")
        else:
            print("— No projects recommended for this message.")

        # Step 5: Generate and store the output using output_generator.py
        print("📝 Generating output for this message…")
        reply_text = generate_output(
            db_file=DB_PATH,
            message_id=message_id,
            problem_ids=problem_ids,
            project_ids=proj_ids,
            answer_style=args.answer_style
        )
        print(f"🗨️  Generated reply: {reply_text}")


def main():
    parser = argparse.ArgumentParser(prog="cli.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -------------------------------------------------------------------------
    p_init = subparsers.add_parser(
        "init",
        help="Precompute & save ALL embeddings for solutions & projects (first‐run)."
    )
    p_init.set_defaults(func=cmd_init)

    # -------------------------------------------------------------------------
    p_run_id = subparsers.add_parser(
        "run-id",
        help="Process any unprocessed problems (is_processed = 0)."
    )
    p_run_id.set_defaults(func=cmd_run_id)

    # -------------------------------------------------------------------------
    p_run = subparsers.add_parser(
        "run",
        help="Insert a new message & run the detection→matching pipeline."
    )
    p_run.add_argument("text", help="Raw message text to insert & process")
    p_run.add_argument("--user-id", type=int, default=0, help="User ID to store")
    p_run.add_argument("--username", default="", help="Username to store")
    p_run.add_argument("--chat-title", default="", help="Chat title to store")
    p_run.add_argument(
        "--answer-style",
        default="empathetic",
        help="Style of the answer to generate (e.g., 'empathetic', 'rude')."
    )
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
