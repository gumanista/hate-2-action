#!/usr/bin/env python3
from src.problem_detector import detect_problems
from src.embed_and_match    import match_embeddings
from src.output_generator   import generate_output

def process_message(message_id: int,
                    db_file: str = "donation.db") -> str:
    """
    Orchestrates the three stages:
      1) detect problems in the message,
      2) match embeddings to get recommended projects,
      3) generate the final LLM reply.

    Returns the chatbot’s reply text.
    """
    # 1. Detect and persist problems
    problem_ids = detect_problems(db_file, message_id)

    # 2. Compute embeddings & retrieve top matches
    _, project_ids = match_embeddings(db_file, problem_ids)

    # 3. Generate and return the final reply
    return generate_output(db_file, message_id, problem_ids, project_ids)

if __name__ == "__main__":
    import sys

    db     = sys.argv[1] if len(sys.argv) > 1 else "donation.db"
    msg_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    reply = process_message(msg_id, db)
    print(reply)
