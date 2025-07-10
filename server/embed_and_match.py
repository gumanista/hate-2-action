from typing import List, Tuple
from langchain_openai import OpenAIEmbeddings
from server.database import Database
def match_embeddings(
        db: Database,
        problem_ids: List[int],
        solution_ids: List[int],
        k: int = 5,
        k_proj: int = 3
) -> Tuple[List[int], List[int]]:
    """
    1) Create vec_solutions / vec_projects / vec_problems (if missing).
    2) Embed any new solutions and projects.
    3) Match any new solutions against all projects.
    4) For each new problem_id, embed + KNN-match against solutions → populate problems_solutions.
    5) Return (sol_ids, proj_ids):
         • sol_ids = all solution_ids matched to the given problem_ids (deduped, in descending similarity order).
         • proj_ids = all project_ids matched to those solution_ids (deduped, in descending similarity order).
    """
    embedder = OpenAIEmbeddings()
    new_sol_ids, _ = db.embed_new_solutions_and_projects(embedder)
    db.match_new_solutions_to_projects(new_sol_ids, k_proj)
    matched_sol_ids = db.embed_and_match_new_problems(embedder, problem_ids, k)
    all_sol_ids = sorted(list(set(solution_ids + matched_sol_ids)))
    proj_ids = db.collect_project_ids_for_solutions(all_sol_ids, top_n=k)
    return all_sol_ids, proj_ids

