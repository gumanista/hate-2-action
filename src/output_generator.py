import os
from typing import List, Tuple, Dict

from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from src.database import Database

DEFAULT_TOP_N = 5
MODEL_NAME = "gpt-4o-mini"


ANSWER_STYLES: Dict[str, Dict[str, str]] = {
    "empathetic": {
        "system_prompt": "You are an assistant that helps users by recommending relevant projects that can help solve user's problems.",
        "response_guidelines": """Please write a response in ukrainian language that:
- Acknowledges the user's message and the problems above.
- Describes how the recommended projects can help solve those problems.
- Provide contact details of the projects, and guidance or next steps.
- Be concise, empathetic, and helpful."""
    },
    "rude": {
        "system_prompt": "You are an assistant that helps users by recommending relevant projects that can help solve user's problems.",
        "response_guidelines": """Be sarcastic, use snappy sentences and tongue-in-cheek jabs.
Please write a response in ukrainian language that:
- Sarcastically acknowledges the user's message and their problems.
- Mentions how the projects might help.
- Provide contact details of the projects, and guidance or next steps.
- Keep it short and snappy."""
    }
}


def generate_output(
    db_file: str,
    message_id: int,
    problem_ids: List[int],
    top_n: int = DEFAULT_TOP_N,
    answer_style: str = "empathetic",
    project_ids: List[int] = None
) -> str:
    """
    1) Fetch original message text from `messages`.
    2) Fetch detected problem names & contexts for each problem_id.
    3) Fetch project details for each project_id.
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

    style = ANSWER_STYLES.get(answer_style, ANSWER_STYLES["empathetic"])

    with Database(db_file) as db:
        message_text = db.get_message_by_id(message_id)
        if not message_text:
            raise ValueError(f"No message found with message_id = {message_id}")

        problems_data = db.get_problems_by_ids(problem_ids)
        projects_data = db.get_projects_by_ids(project_ids, top_n)

        # Build the LLM prompt
        prompt_lines: List[str] = []
        prompt_lines.append(style["system_prompt"] + "\n")
        prompt_lines.append("Original user message:")
        prompt_lines.append(f'"""{message_text}"""\n')

        if problems_data:
            prompt_lines.append("Detected problems:")
            for idx, (pname, pctx) in enumerate(problems_data, start=1):
                line = f"{idx}. {pname}"
                if pctx:
                    line += f" (Context: {pctx})"
                prompt_lines.append(line)
            prompt_lines.append("")
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
            prompt_lines.append("")
        else:
            prompt_lines.append("No candidate projects available to recommend.\n")

        prompt_lines.append(style["response_guidelines"] + "\n")
        full_prompt = "\n".join(prompt_lines)

        # Call ChatOpenAI
        llm = ChatOpenAI(model_name=MODEL_NAME, temperature=0.7)
        messages = [
            SystemMessage(content=style["system_prompt"]),
            HumanMessage(content=full_prompt)
        ]
        response = llm(messages)
        reply_text = response.content.strip()

        # Insert reply into `responses`
        db.add_response(message_id, reply_text)

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
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help="Number of projects (from the supplied list) to include in the prompt"
    )
    parser.add_argument(
        "--answer-style",
        type=str,
        default="empathetic",
        choices=list(ANSWER_STYLES.keys()),
        help="The style of the answer to generate."
    )
 
    args = parser.parse_args()
 
    reply = generate_output(
        db_file=args.db_file,
        message_id=args.message_id,
        problem_ids=args.problems,
        top_n=args.top_n,
        answer_style=args.answer_style
    )
    print("\n===== Generated Reply =====\n")
    print(reply)
    print("\n===========================\n")
