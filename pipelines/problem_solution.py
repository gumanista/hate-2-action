"""
Problem-solution pipeline.

Flow:
1. Extract problems and proposed solutions from user message.
2. Store/refresh semantic entities and embeddings.
3. Link problems to solutions and solutions to orgs/projects via similarity.
4. Rank relevant organizations/projects and generate final reply.
"""

import logging
import math

from db import queries
from utils import llm

from .change_style import resolve_style

logger = logging.getLogger(__name__)

ORG_PROJECT_LINK_THRESHOLD = 0.3
PROBLEM_SOLUTION_LINK_THRESHOLD = 0.35


def _normalize_entities(items: list[dict] | None) -> list[dict]:
    normalized = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        normalized.append(
            {
                "name": name,
                "context": str(item.get("context", "")).strip(),
                "content": str(item.get("content", "")).strip(),
            }
        )
    return normalized


def _embedding_text(entity: dict) -> str:
    return f"{entity['name']}: {entity.get('context', '')} {entity.get('content', '')}".strip()


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _link_solution_to_orgs_and_projects(solution_id: int, embedding: list[float]):
    """Populate organizations_solutions and projects_solutions by vector similarity."""
    orgs_by_emb = queries.find_orgs_by_embedding(embedding, top_n=5)
    projects_by_emb = queries.find_projects_by_embedding(embedding, top_n=5)

    with queries.db_cursor() as cur:
        for org in orgs_by_emb:
            similarity = float(org.get("similarity", 0))
            if similarity < ORG_PROJECT_LINK_THRESHOLD:
                continue
            cur.execute(
                """INSERT INTO organizations_solutions (organization_id, solution_id, similarity_score)
                   VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                (org["organization_id"], solution_id, similarity),
            )

        for project in projects_by_emb:
            similarity = float(project.get("similarity", 0))
            if similarity < ORG_PROJECT_LINK_THRESHOLD:
                continue
            cur.execute(
                """INSERT INTO projects_solutions (project_id, solution_id, similarity_score)
                   VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                (project["project_id"], solution_id, similarity),
            )


def _link_problems_to_solutions(problem_rows: list[dict], solution_rows: list[dict]):
    """Link each problem to its relevant solutions using cosine similarity."""
    if not problem_rows or not solution_rows:
        return

    for problem in problem_rows:
        linked = 0
        best_solution_id = None
        best_score = -1.0

        for solution in solution_rows:
            score = _cosine_similarity(problem["embedding"], solution["embedding"])
            if score > best_score:
                best_score = score
                best_solution_id = solution["solution_id"]
            if score >= PROBLEM_SOLUTION_LINK_THRESHOLD:
                queries.link_problem_solution(
                    problem["problem_id"], solution["solution_id"], score
                )
                linked += 1

        if linked == 0 and best_solution_id is not None:
            queries.link_problem_solution(
                problem["problem_id"], best_solution_id, max(best_score, 0.0)
            )


async def pipeline_problem_solution(
    user_id: int,
    chat_id: int,
    chat_type: str,
    message_text: str,
    tg_message_id: int = None,
) -> str:
    """
    Run core recommendation pipeline:
    complaint text -> structured entities -> semantic linking -> recommended orgs/projects.
    """
    _ = chat_type
    try:
        style = resolve_style(user_id, chat_id)
        history = queries.get_chat_history(chat_id, user_id, limit=6)

        extracted = llm.extract_problems_and_solutions(message_text)
        problems_data = _normalize_entities(extracted.get("problems"))
        solutions_data = _normalize_entities(extracted.get("solutions"))

        problem_rows = []
        for problem in problems_data:
            embedding = llm.get_embedding(_embedding_text(problem))
            problem_id = queries.upsert_problem(
                problem["name"],
                problem["context"],
                problem["content"],
                embedding,
            )
            problem_rows.append({"problem_id": problem_id, "embedding": embedding})

        solution_rows = []
        for solution in solutions_data:
            embedding = llm.get_embedding(_embedding_text(solution))
            solution_id = queries.upsert_solution(
                solution["name"],
                solution["context"],
                solution["content"],
                embedding,
            )
            solution_rows.append({"solution_id": solution_id, "embedding": embedding})

            try:
                _link_solution_to_orgs_and_projects(solution_id, embedding)
            except Exception as e:
                logger.warning(f"Could not link solution to orgs/projects: {e}")

        _link_problems_to_solutions(problem_rows, solution_rows)
        problem_ids = [row["problem_id"] for row in problem_rows]

        orgs = queries.find_orgs_via_solutions(problem_ids)
        projects = queries.find_projects_via_solutions(problem_ids)

        if not orgs and not projects:
            fallback_text = " ".join(_embedding_text(p) for p in problems_data) or message_text
            fallback_embedding = llm.get_embedding(fallback_text)
            orgs = queries.find_orgs_by_embedding(fallback_embedding, top_n=3)
            projects = queries.find_projects_by_embedding(fallback_embedding, top_n=3)

        reply = llm.generate_reply(message_text, style, orgs, projects, history)

        queries.save_message(
            chat_id,
            user_id,
            message_text,
            reply,
            tg_message_id=tg_message_id,
            pipeline_used="process_message",
        )
        return reply
    except Exception as e:
        logger.error(f"problem_solution pipeline error: {e}", exc_info=True)
        return "⚠️ Під час обробки повідомлення сталася помилка. Спробуй ще раз."
