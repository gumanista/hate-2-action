import os
from typing import List, Dict

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from server.database import Database
from server.schemas import Problem, Solution, Project

DEFAULT_TOP_N = 5
MODEL_NAME = "gpt-4.1-mini"

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
- answer the user's message in a style of Oleksandr Les Podervianskyi, with a touch of irony and sarcasm.
- Sarcastically acknowledges the user's message and their problems.
- Mentions how the projects might help.
- Provide contact details of the projects, and guidance or next steps.
- Keep it short and snappy."""
    },
    "formal": {
        "system_prompt": "You are a professional assistant providing factual information about available projects.",
        "response_guidelines": """Please write a formal response in ukrainian language that:
- States the identified issues in a professional manner
- Presents recommended projects with clear, factual descriptions
- Lists contact information and next steps in a structured format
- Maintains a professional, business-like tone throughout"""
    }
}


def generate_output(
        db: Database,
        message_id: int,
        problem_ids: List[int],
        solution_ids: List[int],
        project_ids: List[int],
        top_n: int = DEFAULT_TOP_N,
        answer_style: str = "empathetic"
) -> dict: # This function will now return a dict that includes response_id and created_at
    """
    1) Fetch original message text from `messages`.
    2) Fetch detected problem names & contexts for each problem_id.
    3) Fetch solution details for each solution_id.
    4) Fetch project details for each project_id.
    5) Construct a single prompt that includes:
       - The user’s original message
       - A numbered list of detected problems
       - A numbered list of solutions
       - A numbered list of candidate projects (with metadata)
       - Clear instructions asking the LLM to write a concise, empathetic response.
    6) Use LangChain’s ChatOpenAI to generate the reply.
    7) Insert that reply into `responses(message_id, text)`.
    8) Return the reply text, problem_ids, solution_ids, and project_ids.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    style = ANSWER_STYLES.get(answer_style, ANSWER_STYLES["empathetic"])

    message_text = db.get_message_by_id(message_id)
    if not message_text:
        raise ValueError(f"No message found with message_id = {message_id}")

    problems_data = db.get_problems_by_ids(problem_ids)
    solutions_data = db.get_solutions_by_ids(solution_ids)
    projects_data = db.get_projects_by_ids(project_ids, top_n)

    # Build the LLM prompt
    prompt_lines: List[str] = []
    prompt_lines.append(style["system_prompt"] + "\n")
    prompt_lines.append("Original user message:")
    prompt_lines.append(f'"""{message_text}"""\n')

    if problems_data:
        prompt_lines.append("Detected problems:")
        for idx, (_, pname, pctx) in enumerate(problems_data, start=1):
            line = f"{idx}. {pname}"
            if pctx:
                line += f" (Context: {pctx})"
            prompt_lines.append(line)
        prompt_lines.append("")
    else:
        prompt_lines.append("No specific problems were detected.\n")

    if solutions_data:
        prompt_lines.append("Recommended solutions:")
        for idx, (_, sol_name, sol_ctx) in enumerate(solutions_data, start=1):
            line = f"{idx}. {sol_name}"
            if sol_ctx:
                line += f" (Context: {sol_ctx})"
            prompt_lines.append(line)
        prompt_lines.append("")
    else:
        prompt_lines.append("No specific solutions were detected.\n")

    if projects_data:
        prompt_lines.append("Recommended projects:")
        for idx, (_, proj_name, proj_desc, proj_site, proj_email) in enumerate(projects_data, start=1):
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
    response = llm.invoke(messages)
    reply_text = response.content.strip()

    # Insert reply into `responses` and get the response_id and created_at
    response_data = db.add_response(message_id, reply_text)
    if response_data is None:
        print(f"Warning: Failed to add response for message_id {message_id}. Database error occurred or add_response returned None.")
        response_id, created_at = None, None
    else:
        response_id = response_data[0]
        created_at = response_data[3]

    # Convert tuples to Pydantic models
    problems = [Problem(problem_id=p[0], name=p[1], context=p[2]) for p in problems_data]
    solutions = [Solution(solution_id=s[0], name=s[1], context=s[2]) for s in solutions_data]
    projects = [Project(project_id=p[0], name=p[1], description=p[2], website=p[3], contact_email=p[4]) for p in
                projects_data]

    output_data = {
        "reply_text": reply_text,
        "problems": problems,
        "solutions": solutions,
        "projects": projects,
    }

    output_data["response_id"] = response_id
    output_data["created_at"] = created_at

    return output_data
