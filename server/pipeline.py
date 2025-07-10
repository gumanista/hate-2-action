#!/usr/bin/env python3
from server.problem_detector import detect_problems
from server.embed_and_match import match_embeddings
from server.output_generator import generate_output

from server.database import Database


def run(message: str) -> dict:
    """
    Orchestrates the three stages:
      1) detect problems in the message,
      2) match embeddings to get recommended projects,
      3) generate the final LLM reply.
    Returns the chatbot’s reply text.
    """
    with Database() as db:
        # TODO: user_id, user_username, and chat_title are hardcoded.
        # They should be passed from the request.
        message_id = db.add_message(
            user_id=0,
            user_username="api_user",
            chat_title=None,
            text=message
        )
        if message_id is None:
            # Or handle this error more gracefully
            raise ValueError("Failed to save message to the database.")

        # 1. Detect and persist problems
        problem_ids, solution_ids = detect_problems(db, message)

        # 2. Compute embeddings & retrieve top matches
        all_solution_ids, project_ids = match_embeddings(db, problem_ids, solution_ids)

        # 3. Generate and return the final reply
        return generate_output(db, message_id, problem_ids, all_solution_ids, project_ids)
