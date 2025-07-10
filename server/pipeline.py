#!/usr/bin/env python3
from server.problem_detector import detect_problems
from server.embed_and_match    import match_embeddings
from server.output_generator   import generate_output

from server.database import Database


def run(message: str) -> str:
    """
    Orchestrates the three stages:
      1) detect problems in the message,
      2) match embeddings to get recommended projects,
      3) generate the final LLM reply.
    Returns the chatbot’s reply text.
    """
    with Database() as db:
        # 1. Detect and persist problems
        problem_ids = detect_problems(db, message)

        # 2. Compute embeddings & retrieve top matches
        _, project_ids = match_embeddings(db, problem_ids)

        # 3. Generate and return the final reply
        return generate_output(db, -1, problem_ids, project_ids=project_ids)
