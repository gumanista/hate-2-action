from typing import List, Tuple
from langchain_community.embeddings import OpenAIEmbeddings
from src.database import Database

def match_embeddings(
    db_path: str,
    problem_ids: List[int],
    k: int = 5,
    k_proj: int = 3
) -> Tuple[List[int], List[int]]:
    """
    1) Connect to SQLite, load vec0.
    2) Create vec_solutions / vec_projects / vec_problems (if missing).
    3) Embed any new solutions and projects.
    4) Match any new solutions against all projects.
    5) For each new problem_id, embed + KNN-match against solutions → populate problems_solutions.
    6) Return (sol_ids, proj_ids):
         • sol_ids = all solution_ids matched to the given problem_ids (deduped, in descending similarity order).
         • proj_ids = all project_ids matched to those solution_ids (deduped, in descending similarity order).
    """
    with Database(db_path) as db:
        db.create_vec_tables_if_missing()
        embedder = OpenAIEmbeddings()
        new_sol_ids, _ = db.embed_new_solutions_and_projects(embedder)
        db.match_new_solutions_to_projects(new_sol_ids, k_proj)
        sol_ids = db.embed_and_match_new_problems(embedder, problem_ids, k)
        proj_ids = db.collect_project_ids_for_solutions(sol_ids, top_n=k)
        return sol_ids, proj_ids

