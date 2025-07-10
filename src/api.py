from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, EmailStr
import logging

from src.database import Database
from src.pipeline import process_message
from src.embed_and_match import match_embeddings




DB_PATH = "donation.db"

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True, check_dir=False), name="static")
templates = Jinja2Templates(directory="templates")


# —————————————————————————————————————————————————————————————————————
# Pydantic schemas
# —————————————————————————————————————————————————————————————————————

class ProjectIn(BaseModel):
    name: str
    description: Optional[str]
    website: Optional[HttpUrl]
    contact_email: Optional[EmailStr]
    organization_id: Optional[int]
    solution_ids: List[int] = []


class ProjectOut(ProjectIn):
    project_id: int


# —————————————————————————————————————————————————————————————————————
# Dependency
# —————————————————————————————————————————————————————————————————————

def get_db():
    logging.warning("Attempting to get new DB connection")
    with Database(DB_PATH) as db:
        yield db


# —————————————————————————————————————————————————————————————————————
# 1) RAG-Agent Homepage
# —————————————————————————————————————————————————————————————————————

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ping", response_class=HTMLResponse)
def ping(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



@app.post("/recommend/", response_class=HTMLResponse)
def recommend(
    request: Request,
    text: str = Form(...),
    db: Database = Depends(get_db)
):
    # 1) Insert into messages & detect problems
    msg_id = db.add_message(
        user_id=0, 
        user_username="web", 
        chat_title=None, 
        text=text
    )
    if msg_id is None:
        raise HTTPException(500, "Failed to save message")

    from src.problem_detector import detect_problems
    problem_ids = detect_problems(db_file=DB_PATH, message_id=msg_id)

    # 2) Match to solutions & projects
    sol_ids, proj_ids = match_embeddings(DB_PATH, problem_ids)
    projects = db.get_projects_by_ids(proj_ids, top_n=5)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user_text": text,
            "projects": [
                {
                    "id": p[0],
                    "name": p[1],
                    "description": p[2],
                    "website": p[3],
                    "contact_email": p[4],
                }
                for p in projects
            ]
        }
    )


# —————————————————————————————————————————————————————————————————————
# 2) Admin: CRUD Projects + Select Solutions
# —————————————————————————————————————————————————————————————————————

@app.get("/admin/projects/", response_class=HTMLResponse)
def list_projects(request: Request, db: Database = Depends(get_db)):
    raw = db.conn.execute("SELECT project_id,name,description,website,contact_email FROM projects").fetchall()
    sols = db.conn.execute("SELECT solution_id,name FROM solutions").fetchall()
    return templates.TemplateResponse(
        "admin_projects.html",
        {
            "request": request,
            "projects": raw,
            "solutions": sols,
        }
    )


@app.post("/admin/projects/", response_class=HTMLResponse)
def create_project(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    website: str = Form(None),
    contact_email: str = Form(None),
    organization_id: int = Form(None),
    solution_ids: List[int] = Form([]),
    db: Database = Depends(get_db)
):
    # Insert project
    cur = db.conn.cursor()
    cur.execute(
        """
        INSERT INTO projects(name,description,website,contact_email,organization_id)
        VALUES (?,?,?,?,?)
        """,
        (name, description, website, contact_email, organization_id)
    )
    proj_id = cur.lastrowid

    # Link solutions
    for sid in solution_ids:
        cur.execute(
            "INSERT INTO projects_solutions(project_id,solution_id,matched_at) VALUES (?,?,CURRENT_TIMESTAMP)",
            (proj_id, sid)
        )
    db.conn.commit()

    return RedirectResponse(url="/admin/projects/", status_code=303)
