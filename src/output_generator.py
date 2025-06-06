import os
import sqlite3
from typing import List, Tuple

from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

DEFAULT_TOP_N = 5
MODEL_NAME = "gpt-4o-mini"


def generate_output(
    db_file: str,
    message_id: int,
    problem_ids: List[int],
    project_ids: List[int],
    top_n: int = DEFAULT_TOP_N
) -> str:
    """
    1) Fetch original message text from `messages`.
    2) Fetch detected problem names & contexts for each problem_id.
    3) Fetch project details (name, description, website, contact_email) for each project_id (limiting to top_n).
    4) Construct a single prompt that includes:
       - The user’s original message
       - A numbered list of detected problems
       - A numbered list of candidate projects (with metadata)
       - Clear instructions asking the LLM to write a concise, empathetic response.
    5) Use LangChain’s ChatOpenAI to generate the reply.
    6) Insert that reply into `responses(message_id, text)`.
    7) Return the reply text.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # ── 1) Fetch original message text ─────────────────────────────────────────
    cur.execute("SELECT text FROM messages WHERE message_id = ?", (message_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"No message found with message_id = {message_id}")
    message_text = row[0]

    # ── 2) Fetch problem names & contexts ─────────────────────────────────────
    problems_data: List[Tuple[str, str]] = []
    if problem_ids:
        placeholder = ",".join("?" for _ in problem_ids)
        query = f"SELECT name, context FROM problems WHERE problem_id IN ({placeholder})"
        cur.execute(query, tuple(problem_ids))
        problems_data = cur.fetchall()
    else:
        problems_data = []

    # ── 3) Fetch project details ──────────────────────────────────────────────
    projects_data: List[Tuple[str, str, str, str]] = []
    if project_ids:
        selected_ids = project_ids[:top_n]
        placeholder = ",".join("?" for _ in selected_ids)
        query = (
            f"SELECT name, description, website, contact_email "
            f"FROM projects WHERE project_id IN ({placeholder})"
        )
        cur.execute(query, tuple(selected_ids))
        projects_data = cur.fetchall()
    else:
        projects_data = []

    conn.close()

    # ── 4) Build the LLM prompt ────────────────────────────────────────────────
    prompt_lines: List[str] = []
    prompt_lines.append(
        "You are an assistant that helps users by recommending relevant projects "
        "to address their problems. Be concise, empathetic, and clear.\n"
    )
    prompt_lines.append("Original user message:")
    prompt_lines.append(f"\"\"\"{message_text}\"\"\"\n")

    if problems_data:
        prompt_lines.append("Detected problems:")
        for idx, (pname, pctx) in enumerate(problems_data, start=1):
            line = f"{idx}. {pname}"
            if pctx:
                line += f" (Context: {pctx})"
            prompt_lines.append(line)
        prompt_lines.append("")  # blank line
    else:
        prompt_lines.append("No specific problems were detected.\n")

    if projects_data:
        prompt_lines.append("Recommended projects:")
        for idx, (proj_name, proj_desc, proj_site, proj_email) in enumerate(projects_data, start=1):
            line = f"{idx}. {proj_name}"
            if proj_desc:
                line += f": {proj_desc}"
            if proj_site:
                line += f" | Website: {proj_site}"
            if proj_email:
                line += f" | Contact: {proj_email}"
            prompt_lines.append(line)
        prompt_lines.append("")  # blank line
    else:
        prompt_lines.append("No candidate projects available to recommend.\n")

    prompt_lines.append("Please write a response that:")
    prompt_lines.append("- Acknowledges the user's message and the problems above.")
    prompt_lines.append("- Describes how the recommended projects can help solve those problems.")
    prompt_lines.append("- Provides any additional guidance or next steps.")
    prompt_lines.append("- Be concise and helpful.\n")

    full_prompt = "\n".join(prompt_lines)

    # ── 5) Call ChatOpenAI via LangChain ───────────────────────────────────────
    llm = ChatOpenAI(model_name=MODEL_NAME, temperature=0.7)
    messages = [
        SystemMessage(content="You are an assistant that recommends projects to address users' problems."),
        HumanMessage(content=full_prompt)
    ]
    response = llm(messages)
    reply_text = response.content.strip()

    # ── 6) Insert reply into `responses` ─────────────────────────────────────
    conn2 = sqlite3.connect(db_file)
    cur2 = conn2.cursor()
    cur2.execute(
        "INSERT INTO responses(message_id, text) VALUES (?, ?)",
        (message_id, reply_text)
    )
    conn2.commit()
    conn2.close()

    return reply_text


# ── CLI for Direct Invocation ────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate an LLM-based reply for a given message, using detected problems and matched projects."
    )
    parser.add_argument("--db-file", required=True, help="Path to SQLite DB file")
    parser.add_argument("--message-id", type=int, required=True, help="ID of the message to reply to")
    parser.add_argument(
        "--problems",
        type=int,
        nargs="*",
        default=[],
        help="List of problem_id values associated with this message"
    )
    parser.add_argument(
        "--projects",
        type=int,
        nargs="*",
        default=[],
        help="List of project_id values to recommend"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help="Number of projects (from the supplied list) to include in the prompt"
    )

    args = parser.parse_args()

    reply = generate_output(
        db_file=args.db_file,
        message_id=args.message_id,
        problem_ids=args.problems,
        project_ids=args.projects,
        top_n=args.top_n
    )
    print("\n===== Generated Reply =====\n")
    print(reply)
    print("\n===========================\n")
