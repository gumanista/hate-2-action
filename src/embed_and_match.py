# src/embed_and_match.py

import json
import os
from typing import List, Tuple

from langchain_community.embeddings import OpenAIEmbeddings
from src.telegram.database import Database

VECTOR_DIM = 1536  # Embedding dimension size for OpenAI embeddings

def _populate_solutions_and_projects(db: Database, embedder: OpenAIEmbeddings):
    """
    On the first run, compute embeddings for *all* rows in `solutions` and `projects`,
    and insert them into vec_solutions / vec_projects.
    """
    cur = db.conn.cursor()

    # Populate vec_solutions if empty
    cur.execute("SELECT COUNT(*) FROM vec_solutions;")
    count_vs = cur.fetchone()[0]
    if count_vs == 0:
        cur.execute("SELECT solution_id, context FROM solutions;")
        rows = cur.fetchall()
        for solution_id, context_text in rows:
            vec = embedder.embed_documents([context_text])[0]
            cur.execute(
                "INSERT OR REPLACE INTO vec_solutions(solution_id, embedding) VALUES (?, json(?));",
                (solution_id, json.dumps(vec))
            )
        db.conn.commit()

    # Populate vec_projects if empty
    cur.execute("SELECT COUNT(*) FROM vec_projects;")
    count_vp = cur.fetchone()[0]
    if count_vp == 0:
        cur.execute("SELECT project_id, description FROM projects;")
        rows = cur.fetchall()
        for project_id, description_text in rows:
            vec = embedder.embed_documents([description_text])[0]
            cur.execute(
                "INSERT OR REPLACE INTO vec_projects(project_id, embedding) VALUES (?, json(?));",
                (project_id, json.dumps(vec))
            )
        db.conn.commit()


def _populate_projects_solutions(db: Database, k_proj: int = 5):
    """
    On the first run (or whenever projects_solutions is empty), match *every* solution
    to its top-k_proj projects and insert into projects_solutions.
    """
    cur = db.conn.cursor()

    # Check if projects_solutions is already populated
    cur.execute("SELECT COUNT(*) FROM projects_solutions;")
    count_ps = cur.fetchone()[0]
    if count_ps == 0:
        # Fetch all solution_ids
        cur.execute("SELECT solution_id FROM solutions;")
        all_solutions = [row[0] for row in cur.fetchall()]

        for sid in all_solutions:
            sql = f"""
            WITH target AS (
              SELECT embedding
              FROM vec_solutions
              WHERE solution_id = {sid}
            )
            INSERT OR IGNORE INTO projects_solutions(project_id, solution_id, similarity_score)
            SELECT
              vp.project_id       AS project_id,
              {sid}               AS solution_id,
              1.0 - distance      AS similarity_score
            FROM vec_projects AS vp, target
            WHERE vp.embedding
                  MATCH target.embedding
                AND k = {k_proj};
            """
            cur.executescript(sql)

        db.conn.commit()


def _embed_and_match_new_problems(
    db: Database,
    embedder: OpenAIEmbeddings,
    problem_ids: List[int],
    k: int = 5  # Top 5 solutions to match
) -> List[int]:
    """
    For each problem_id in problem_ids (all of which should have is_processed = 0),
    1) Compute its embedding, insert into vec_problems.
    2) Run a vec0 KNN query (k nearest solutions), insert into problems_solutions.
    Returns a flat list of *all* solution_ids matched to these problems.
    """
    cur = db.conn.cursor()
    matched_solution_ids = []

    for pid in problem_ids:
        # Fetch the problem text
        cur.execute("SELECT context FROM problems WHERE problem_id = ?", (pid,))
        row = cur.fetchone()
        if row is None:
            continue
        problem_text = row[0]

        # Embed and insert into vec_problems
        vec = embedder.embed_documents([problem_text])[0]
        cur.execute(
            "INSERT OR REPLACE INTO vec_problems(problem_id, embedding) VALUES (?, json(?));",
            (pid, json.dumps(vec))
        )
        db.conn.commit()

        # KNN query: “problem” → top k “solutions”
        sql = f"""
        WITH target AS (
          SELECT embedding
          FROM vec_problems
          WHERE problem_id = {pid}
        )
        INSERT OR IGNORE INTO problems_solutions(problem_id, solution_id, similarity_score)
        SELECT
          {pid}               AS problem_id,
          vs.solution_id      AS solution_id,
          1.0 - distance      AS similarity_score
        FROM vec_solutions AS vs, target
        WHERE vs.embedding
              MATCH target.embedding
            AND k = {k};  -- Select top k solutions
        """
        cur.executescript(sql)
        db.conn.commit()

        # Collect top k solution_ids
        cur.execute(
            "SELECT solution_id FROM problems_solutions WHERE problem_id = ? ORDER BY similarity_score DESC LIMIT ?",
            (pid, k)
        )
        rows = cur.fetchall()
        matched_solution_ids.extend(r[0] for r in rows)

        # Mark problem as processed
        cur.execute("UPDATE problems SET is_processed = 1 WHERE problem_id = ?;", (pid,))
        db.conn.commit()

    # Deduplicate while preserving order
    seen = set()
    unique_solution_ids = []
    for sid in matched_solution_ids:
        if sid not in seen:
            seen.add(sid)
            unique_solution_ids.append(sid)

    return unique_solution_ids


def _collect_project_ids_for_solutions(
    db: Database,
    solution_ids: List[int],
    top_n: int = 5  # Top 5 projects
) -> List[int]:
    if not solution_ids:
        return []

    cur = db.conn.cursor()
    placeholders = ",".join("?" for _ in solution_ids)

    # Fetch all matching rows, ordered by similarity_score DESC
    query = f"""
      SELECT project_id
      FROM projects_solutions
      WHERE solution_id IN ({placeholders})
      ORDER BY similarity_score DESC
      LIMIT {top_n};  -- Select top n projects
    """
    cur.execute(query, solution_ids)
    rows = cur.fetchall()

    seen = set()
    unique_project_ids = []
    for (pid,) in rows:
        if pid not in seen:
            seen.add(pid)
            unique_project_ids.append(pid)

    return unique_project_ids


def match_embeddings(
    db_path: str,
    problem_ids: List[int],
    k: int = 5  # Top 5 solutions and projects
) -> Tuple[List[int], List[int]]:
    """
    1) Connect to SQLite, load vec0.
    2) Create vec_solutions / vec_projects / vec_problems (if missing).
    3) On the first run, embed + insert *all* solutions and projects, then populate projects_solutions.
    4) For each new problem_id, embed + KNN-match against solutions → populate problems_solutions.
    5) Return (sol_ids, proj_ids):
         • sol_ids = all solution_ids matched to the given problem_ids (deduped, in descending similarity order).
         • proj_ids = all project_ids matched to those solution_ids (deduped, in descending similarity order).
    """
    with Database(db_path) as db:
        # Create the necessary tables if missing
        db.create_vec_tables_if_missing()

        # Initialize the embedding model
        embedder = OpenAIEmbeddings()

        # First-run: populate all solution/project embeddings if needed
        _populate_solutions_and_projects(db, embedder)

        # First-run: populate projects_solutions if needed
        _populate_projects_solutions(db, k_proj=3)

        # For each newly detected problem, embed & match → solutions
        sol_ids = _embed_and_match_new_problems(db, embedder, problem_ids, k)

        # Collect all matching project_ids for the selected solutions
        proj_ids = _collect_project_ids_for_solutions(db, sol_ids, top_n=k)

    return sol_ids, proj_ids
