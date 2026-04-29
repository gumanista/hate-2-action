"""FastAPI server exposing CRUD + process-message endpoints for the hate2action frontend."""
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from db import queries
from pipelines.problem_solution import (
    PROBLEM_SOLUTION_LINK_THRESHOLD,
    _embedding_text,
    _link_problems_to_solutions,
    _link_solution_to_orgs_and_projects,
    _normalize_entities,
)
from server.schemas import (
    OrganizationIn,
    OrganizationOut,
    ProblemIn,
    ProblemOut,
    ProcessMessageIn,
    ProjectIn,
    ProjectOut,
    SolutionIn,
    SolutionOut,
)
from utils import llm

logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY", "")
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="hate2action API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _check_api_key(x_api_key: str | None) -> None:
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Organizations ────────────────────────────────────────────────────────
@app.get("/organizations", response_model=list[OrganizationOut])
def get_organizations(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    return queries.list_organizations()


@app.get("/organizations/{organization_id}")
def get_organization(organization_id: int, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    org = queries.get_organization(organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@app.post("/organizations", response_model=OrganizationOut, status_code=201)
def post_organization(payload: OrganizationIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    return queries.create_organization(payload.name, payload.description, payload.website, payload.contact_email)


@app.put("/organizations/{organization_id}", response_model=OrganizationOut)
def put_organization(organization_id: int, payload: OrganizationIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    updated = queries.update_organization(organization_id, payload.name, payload.description, payload.website, payload.contact_email)
    if not updated:
        raise HTTPException(status_code=404, detail="Organization not found")
    return updated


@app.delete("/organizations/{organization_id}", status_code=204)
def remove_organization(organization_id: int, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    if not queries.delete_organization(organization_id):
        raise HTTPException(status_code=404, detail="Organization not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Projects ─────────────────────────────────────────────────────────────
@app.get("/projects", response_model=list[ProjectOut])
def get_projects(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    return queries.list_projects()


@app.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    project = queries.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/projects", response_model=ProjectOut, status_code=201)
def post_project(payload: ProjectIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    return queries.create_project(payload.name, payload.description, payload.organization_id)


@app.put("/projects/{project_id}", response_model=ProjectOut)
def put_project(project_id: int, payload: ProjectIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    updated = queries.update_project(project_id, payload.name, payload.description, payload.organization_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated


@app.delete("/projects/{project_id}", status_code=204)
def remove_project(project_id: int, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    if not queries.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Problems ─────────────────────────────────────────────────────────────
@app.get("/problems", response_model=list[ProblemOut])
def get_problems(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    return queries.list_problems()


@app.get("/problems/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    problem = queries.get_problem(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


@app.post("/problems", response_model=ProblemOut, status_code=201)
def post_problem(payload: ProblemIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    return queries.create_problem(payload.name, payload.context, payload.content, bool(payload.is_processed))


@app.put("/problems/{problem_id}", response_model=ProblemOut)
def put_problem(problem_id: int, payload: ProblemIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    updated = queries.update_problem(problem_id, payload.name, payload.context, payload.content, payload.is_processed)
    if not updated:
        raise HTTPException(status_code=404, detail="Problem not found")
    return updated


@app.delete("/problems/{problem_id}", status_code=204)
def remove_problem(problem_id: int, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    if not queries.delete_problem(problem_id):
        raise HTTPException(status_code=404, detail="Problem not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Solutions ────────────────────────────────────────────────────────────
@app.get("/solutions", response_model=list[SolutionOut])
def get_solutions(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    return queries.list_solutions()


@app.get("/solutions/{solution_id}", response_model=SolutionOut)
def get_solution(solution_id: int, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    sol = queries.get_solution(solution_id)
    if not sol:
        raise HTTPException(status_code=404, detail="Solution not found")
    return sol


@app.post("/solutions", response_model=SolutionOut, status_code=201)
def post_solution(payload: SolutionIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    return queries.create_solution(payload.name, payload.context, payload.content)


@app.put("/solutions/{solution_id}", response_model=SolutionOut)
def put_solution(solution_id: int, payload: SolutionIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    updated = queries.update_solution(solution_id, payload.name, payload.context, payload.content)
    if not updated:
        raise HTTPException(status_code=404, detail="Solution not found")
    return updated


@app.delete("/solutions/{solution_id}", status_code=204)
def remove_solution(solution_id: int, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    if not queries.delete_solution(solution_id):
        raise HTTPException(status_code=404, detail="Solution not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Messages ─────────────────────────────────────────────────────────────
def _shape_message(row: dict) -> dict:
    return {
        "message_id": row["message_id"],
        "chat_id": row.get("chat_id"),
        "user_id": row.get("user_id"),
        "user_username": row.get("user_username") or row.get("user_first_name") or f"user_{row.get('user_id') or ''}",
        "chat_title": row.get("chat_type"),
        "text": row.get("message_text"),
        "date": row.get("date"),
        "pipeline_used": row.get("pipeline_used"),
        "response": {
            "text": row.get("reply_text") or "",
            "problems": [],
            "solutions": [],
            "projects": [],
        } if row.get("reply_text") else None,
    }


@app.get("/messages")
def get_messages(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    return [_shape_message(r) for r in queries.list_messages()]


@app.get("/messages/{message_id}")
def get_message(message_id: int, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    row = queries.get_message(message_id)
    if not row:
        raise HTTPException(status_code=404, detail="Message not found")
    return _shape_message(row)


# ── Process message ──────────────────────────────────────────────────────
@app.post("/process-message")
def process_message(payload: ProcessMessageIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _check_api_key(x_api_key)
    text = (payload.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message is empty")

    style = payload.response_style or "normal"
    lang = llm.detect_language(text)

    try:
        extracted = llm.extract_problems_and_solutions(text)
        problems_data = _normalize_entities(extracted.get("problems"))
        solutions_data = _normalize_entities(extracted.get("solutions"))

        problem_rows: list[dict] = []
        for problem in problems_data:
            embedding = llm.get_embedding(_embedding_text(problem))
            problem_id = queries.upsert_problem(problem["name"], problem["context"], problem["content"], embedding)
            problem_rows.append({
                "problem_id": problem_id, "embedding": embedding, "name": problem["name"],
            })

        solution_rows: list[dict] = []
        for solution in solutions_data:
            embedding = llm.get_embedding(_embedding_text(solution))
            solution_id = queries.upsert_solution(solution["name"], solution["context"], solution["content"], embedding)
            solution_rows.append({
                "solution_id": solution_id, "embedding": embedding, "name": solution["name"],
            })
            try:
                _link_solution_to_orgs_and_projects(solution_id, embedding)
            except Exception as e:
                logger.warning("link solution failed: %s", e)

        _link_problems_to_solutions(problem_rows, solution_rows)

        problem_ids = [r["problem_id"] for r in problem_rows]
        orgs = queries.find_orgs_via_solutions(problem_ids)
        projects = queries.find_projects_via_solutions(problem_ids)
        if not orgs and not projects:
            fallback_text = " ".join(_embedding_text(p) for p in problems_data) or text
            fallback_embedding = llm.get_embedding(fallback_text)
            orgs = queries.find_orgs_by_embedding(fallback_embedding, top_n=3)
            projects = queries.find_projects_by_embedding(fallback_embedding, top_n=3)

        reply = llm.generate_reply(text, style, orgs, projects, [], lang=lang)

        return {
            "text": reply,
            "problems": [{"problem_id": r["problem_id"], "name": r["name"]} for r in problem_rows],
            "solutions": [{"solution_id": r["solution_id"], "name": r["name"]} for r in solution_rows],
            "projects": [{"project_id": p["project_id"], "name": p["name"]} for p in projects],
            "organizations": [{"organization_id": o["organization_id"], "name": o["name"]} for o in orgs],
        }
    except Exception as e:
        logger.error("process-message failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Static frontend ──────────────────────────────────────────────────────
if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{filename:path}")
    def frontend_asset(filename: str):
        target = FRONTEND_DIR / filename
        if target.is_file():
            return FileResponse(str(target))
        raise HTTPException(status_code=404, detail="Not found")
