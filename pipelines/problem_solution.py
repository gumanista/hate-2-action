"""
Problem-solution pipeline.

Purpose:
- Transform an unstructured complaint into actionable recommendations
  (organizations and projects) through entity extraction + semantic linking.

Inputs:
- Identity/context: `user_id`, `chat_id`, optional `tg_message_id`.
- Message payload: free-form `message_text`.
- Chat style context is resolved through `resolve_style(...)`.

Data flow:
1. Extract structured `problems` and `solutions` from text using LLM.
2. Normalize entity payloads to a strict schema: `name`, `context`, `content`.
3. Build embeddings and upsert problems/solutions into DB.
4. Create graph links:
   - solution -> organizations/projects by vector similarity threshold.
   - problem -> solutions by cosine similarity threshold, with best-match fallback.
5. Retrieve candidate organizations/projects via problem->solution links.
6. If graph retrieval is empty, run direct embedding fallback search.
7. Generate final styled response using message, candidates, and chat history.
8. Persist message/reply pair with `pipeline_used="process_message"`.

Reliability behavior:
- Similarity thresholds prevent weak links from polluting join tables.
- Linking failures for individual solutions are logged as warnings without
  aborting full response generation.
- Any unhandled exception returns a safe generic error to the user.
"""

# Import logging to capture pipeline warnings/errors.
import logging
# Import math for vector norm calculation in cosine similarity.
import math

# Import DB query layer used for semantic entity persistence and retrieval.
from db import queries
# Import LLM utilities for extraction, embeddings, and reply generation.
from utils import llm

# Reuse style resolver to keep response tone consistent.
from .change_style import resolve_style

# Create module-level logger instance.
logger = logging.getLogger(__name__)

# Minimum similarity required to connect solutions with orgs/projects.
ORG_PROJECT_LINK_THRESHOLD = 0.3
# Minimum similarity required to connect problems with solutions.
PROBLEM_SOLUTION_LINK_THRESHOLD = 0.35


# Normalize extracted entity objects into strict dict shape used downstream.
def _normalize_entities(items: list[dict] | None) -> list[dict]:
    # Prepare output list.
    normalized = []
    # Iterate over provided items; treat None as empty list.
    for item in items or []:
        # Skip non-dictionary items produced by malformed extraction.
        if not isinstance(item, dict):
            # Continue with next item.
            continue
        # Read and normalize entity name.
        name = str(item.get("name", "")).strip()
        # Ignore entries without a meaningful name.
        if not name:
            # Continue with next item.
            continue
        # Append normalized entity fields with guaranteed string values.
        normalized.append(
            {
                # Canonical entity name used for identity and display.
                "name": name,
                # Short contextual details around the entity mention.
                "context": str(item.get("context", "")).strip(),
                # Additional free-form content/details from extraction.
                "content": str(item.get("content", "")).strip(),
            }
        )
    # Return cleaned/normalized entities list.
    return normalized


# Build text payload used for embedding entity semantics.
def _embedding_text(entity: dict) -> str:
    # Combine name, context, and content into one sentence-like string.
    return (
        f"{entity['name']}: {entity.get('context', '')} {entity.get('content', '')}"
    ).strip()


# Compute cosine similarity between two equal-length vectors.
def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    # Return zero similarity for missing vectors or mismatched dimensions.
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        # Invalid vector input cannot be compared.
        return 0.0
    # Compute dot product for angle comparison.
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    # Compute L2 norm (vector magnitude) for first vector.
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    # Compute L2 norm (vector magnitude) for second vector.
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    # Avoid division by zero when one vector has zero magnitude.
    if norm_a == 0 or norm_b == 0:
        # Degenerate vectors get zero similarity.
        return 0.0
    # Return cosine similarity in range approximately [-1, 1].
    return dot / (norm_a * norm_b)


# Link a solution to nearby organizations and projects via embedding similarity.
def _link_solution_to_orgs_and_projects(solution_id: int, embedding: list[float]):
    """Populate organizations_solutions and projects_solutions by vector similarity."""
    # Find top matching organizations for this solution embedding.
    orgs_by_emb = queries.find_orgs_by_embedding(embedding, top_n=5)
    # Find top matching projects for this solution embedding.
    projects_by_emb = queries.find_projects_by_embedding(embedding, top_n=5)

    # Open transactional cursor for inserting many link rows efficiently.
    with queries.db_cursor() as cur:
        # Iterate organization candidates and keep only sufficiently similar ones.
        for org in orgs_by_emb:
            # Extract similarity score from row (default 0 when missing).
            similarity = float(org.get("similarity", 0))
            # Skip weak semantic matches.
            if similarity < ORG_PROJECT_LINK_THRESHOLD:
                # Continue checking next organization.
                continue
            # Insert relationship row between organization and solution.
            cur.execute(
                """INSERT INTO organizations_solutions (organization_id, solution_id, similarity_score)
                   VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                # Use IDs from match row and computed similarity score.
                (org["organization_id"], solution_id, similarity),
            )

        # Iterate project candidates and keep only sufficiently similar ones.
        for project in projects_by_emb:
            # Extract similarity score from row (default 0 when missing).
            similarity = float(project.get("similarity", 0))
            # Skip weak semantic matches.
            if similarity < ORG_PROJECT_LINK_THRESHOLD:
                # Continue checking next project.
                continue
            # Insert relationship row between project and solution.
            cur.execute(
                """INSERT INTO projects_solutions (project_id, solution_id, similarity_score)
                   VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                # Use IDs from match row and computed similarity score.
                (project["project_id"], solution_id, similarity),
            )


# Link each problem with one or more relevant solutions using cosine similarity.
def _link_problems_to_solutions(problem_rows: list[dict], solution_rows: list[dict]):
    """Link each problem to its relevant solutions using cosine similarity."""
    # Nothing to link when either side is empty.
    if not problem_rows or not solution_rows:
        # Exit early.
        return

    # Process each persisted problem embedding.
    for problem in problem_rows:
        # Counter for links created above threshold.
        linked = 0
        # Track best-matching solution id for fallback linking.
        best_solution_id = None
        # Track best similarity score observed for fallback linking.
        best_score = -1.0

        # Compare current problem against every available solution.
        for solution in solution_rows:
            # Compute semantic closeness between problem and solution embeddings.
            score = _cosine_similarity(problem["embedding"], solution["embedding"])
            # Keep strongest candidate even when below threshold.
            if score > best_score:
                # Update best score.
                best_score = score
                # Update best solution id.
                best_solution_id = solution["solution_id"]
            # Persist link when score meets threshold.
            if score >= PROBLEM_SOLUTION_LINK_THRESHOLD:
                # Insert/link pair in join table via query helper.
                queries.link_problem_solution(
                    problem["problem_id"], solution["solution_id"], score
                )
                # Increment number of persisted links for this problem.
                linked += 1

        # Guarantee at least one link using strongest candidate as fallback.
        if linked == 0 and best_solution_id is not None:
            # Persist fallback link, clamping negative values to zero.
            queries.link_problem_solution(
                problem["problem_id"], best_solution_id, max(best_score, 0.0)
            )


# Main semantic recommendation pipeline for complaint/problem messages.
async def pipeline_problem_solution(
    # Telegram user identifier.
    user_id: int,
    # Telegram chat identifier.
    chat_id: int,
    # Telegram chat type (not used yet but kept for interface consistency).
    chat_type: str,
    # Raw user message text describing frustration/problem.
    message_text: str,
    # Optional Telegram message id for traceability.
    tg_message_id: int = None,
) -> str:
    """
    Run core recommendation pipeline:
    complaint text -> structured entities -> semantic linking -> recommended orgs/projects.
    """
    # Explicitly mark unused parameter while preserving shared function signature.
    _ = chat_type
    try:
        # Resolve response style for this user/chat.
        style = resolve_style(user_id, chat_id)
        # Load recent chat history to improve contextual reply generation.
        history = queries.get_chat_history(chat_id, user_id, limit=6)

        # Extract structured problems and solutions from free-form user text.
        extracted = llm.extract_problems_and_solutions(message_text)
        # Normalize extracted problems into consistent shape.
        problems_data = _normalize_entities(extracted.get("problems"))
        # Normalize extracted solutions into consistent shape.
        solutions_data = _normalize_entities(extracted.get("solutions"))

        # Collect persisted problem rows with ids and embeddings.
        problem_rows = []
        # Persist each normalized problem entity.
        for problem in problems_data:
            # Compute embedding vector for this problem entity.
            embedding = llm.get_embedding(_embedding_text(problem))
            # Upsert problem into DB and get stable problem id.
            problem_id = queries.upsert_problem(
                # Problem name.
                problem["name"],
                # Problem context text.
                problem["context"],
                # Problem content text.
                problem["content"],
                # Problem embedding vector.
                embedding,
            )
            # Store for later linking stage.
            problem_rows.append({"problem_id": problem_id, "embedding": embedding})

        # Collect persisted solution rows with ids and embeddings.
        solution_rows = []
        # Persist each normalized solution entity.
        for solution in solutions_data:
            # Compute embedding vector for this solution entity.
            embedding = llm.get_embedding(_embedding_text(solution))
            # Upsert solution into DB and get stable solution id.
            solution_id = queries.upsert_solution(
                # Solution name.
                solution["name"],
                # Solution context text.
                solution["context"],
                # Solution content text.
                solution["content"],
                # Solution embedding vector.
                embedding,
            )
            # Store for later linking stage.
            solution_rows.append({"solution_id": solution_id, "embedding": embedding})

            try:
                # Link this solution to nearby orgs/projects via vector similarity.
                _link_solution_to_orgs_and_projects(solution_id, embedding)
            except Exception as e:
                # Do not fail whole pipeline if linking stage has partial errors.
                logger.warning(f"Could not link solution to orgs/projects: {e}")

        # Link saved problems to saved solutions.
        _link_problems_to_solutions(problem_rows, solution_rows)
        # Extract problem ids for retrieval queries.
        problem_ids = [row["problem_id"] for row in problem_rows]

        # Retrieve organizations linked indirectly via matched solutions.
        orgs = queries.find_orgs_via_solutions(problem_ids)
        # Retrieve projects linked indirectly via matched solutions.
        projects = queries.find_projects_via_solutions(problem_ids)

        # If graph-based retrieval produced nothing, do direct embedding fallback.
        if not orgs and not projects:
            # Build fallback text from normalized problems, else use raw message.
            fallback_text = " ".join(_embedding_text(p) for p in problems_data) or message_text
            # Compute fallback embedding for direct nearest-neighbor search.
            fallback_embedding = llm.get_embedding(fallback_text)
            # Retrieve nearest organizations directly by embedding.
            orgs = queries.find_orgs_by_embedding(fallback_embedding, top_n=3)
            # Retrieve nearest projects directly by embedding.
            projects = queries.find_projects_by_embedding(fallback_embedding, top_n=3)

        # Generate final user-facing reply using style, matches, and conversation history.
        reply = llm.generate_reply(message_text, style, orgs, projects, history)

        # Persist message pair and pipeline marker for history and analytics.
        queries.save_message(
            # Chat context id.
            chat_id,
            # User context id.
            user_id,
            # Original user message.
            message_text,
            # Generated reply text.
            reply,
            # Optional Telegram message id.
            tg_message_id=tg_message_id,
            # Pipeline marker for analytics/debugging.
            pipeline_used="process_message",
        )
        # Return generated reply.
        return reply
    except Exception as e:
        # Log unexpected pipeline failure with stack trace.
        logger.error(f"problem_solution pipeline error: {e}", exc_info=True)
        # Return safe fallback message for end user.
        return "⚠️ Під час обробки повідомлення сталася помилка. Спробуй ще раз."
