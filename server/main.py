from fastapi import FastAPI, HTTPException, Depends
from server.schemas import (
    ProcessMessageRequest,
    Project, ProjectCreate, ProjectUpdate,
    Problem, ProblemCreate, ProblemUpdate,
    Solution, SolutionCreate, SolutionUpdate,
    Organization, OrganizationCreate, OrganizationUpdate
)
from server.pipeline import run as process_message_run
from server.database import Database
import logging
from typing import List
from server.security import get_api_key

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/")
async def root(api_key: str = Depends(get_api_key)):
    return {"message": "API is running"}


@app.post("/process-message")
async def process_message(request: ProcessMessageRequest, api_key: str = Depends(get_api_key)):
    try:
        logger.info(f"Processing message: {request.message}")
        result = process_message_run(request.message)
        logger.info("Message processed successfully.")
        return {"result": result}
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Projects
@app.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate, api_key: str = Depends(get_api_key)):
    with Database() as db:
        project_id = db.create_project(project.name, project.description, project.website, project.contact_email)
        if project_id is None:
            raise HTTPException(status_code=500, detail="Failed to create project")
        return Project(project_id=project_id, name=project.name, description=project.description,
                       website=project.website, contact_email=project.contact_email)


@app.get("/projects", response_model=List[Project])
async def get_projects(api_key: str = Depends(get_api_key)):
    with Database() as db:
        projects = db.get_projects()
        return [Project(project_id=p[0], name=p[1], description=p[2], created_at=p[3], website=p[4],
                        contact_email=p[5]) for p in projects]


@app.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        project = db.get_project_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return Project(project_id=project[0], name=project[1], description=project[2], created_at=project[3],
                       website=project[4], contact_email=project[5])


@app.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: int, project: ProjectUpdate, api_key: str = Depends(get_api_key)):
    with Database() as db:
        success = db.update_project(project_id, project.name, project.description, project.website,
                                    project.contact_email)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")

        updated_project = db.get_project_by_id(project_id)
        if updated_project is None:
            raise HTTPException(status_code=404, detail="Project not found after update")

        return Project(project_id=updated_project[0], name=updated_project[1], description=updated_project[2],
                       created_at=updated_project[3], website=updated_project[4],
                       contact_email=updated_project[5])


@app.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        success = db.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")


# Problems
@app.post("/problems", response_model=Problem)
async def create_problem(problem: ProblemCreate, api_key: str = Depends(get_api_key)):
    with Database() as db:
        problem_id = db.create_problem(problem.name, problem.context)
        if problem_id is None:
            raise HTTPException(status_code=500, detail="Failed to create problem")
        return Problem(problem_id=problem_id, name=problem.name, context=problem.context)


@app.get("/problems", response_model=List[Problem])
async def get_problems(api_key: str = Depends(get_api_key)):
    with Database() as db:
        problems = db.get_problems()
        return [Problem(problem_id=p[0], name=p[1], context=p[2], created_at=p[3], is_processed=p[4]) for p in
                problems]


@app.get("/problems/{problem_id}", response_model=Problem)
async def get_problem(problem_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        problem = db.get_problem_by_id(problem_id)
        if problem is None:
            raise HTTPException(status_code=404, detail="Problem not found")
        return Problem(problem_id=problem[0], name=problem[1], context=problem[2], created_at=problem[3],
                       is_processed=problem[4])


@app.put("/problems/{problem_id}", response_model=Problem)
async def update_problem(problem_id: int, problem: ProblemUpdate, api_key: str = Depends(get_api_key)):
    with Database() as db:
        success = db.update_problem(problem_id, problem.name, problem.context, problem.is_processed)
        if not success:
            raise HTTPException(status_code=404, detail="Problem not found")
        updated_problem = db.get_problem_by_id(problem_id)
        if updated_problem is None:
            raise HTTPException(status_code=404, detail="Problem not found after update")
        return Problem(problem_id=updated_problem[0], name=updated_problem[1], context=updated_problem[2],
                       created_at=updated_problem[3], is_processed=updated_problem[4])


@app.delete("/problems/{problem_id}", status_code=204)
async def delete_problem(problem_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        success = db.delete_problem(problem_id)
        if not success:
            raise HTTPException(status_code=404, detail="Problem not found")


# Solutions
@app.post("/solutions", response_model=Solution)
async def create_solution(solution: SolutionCreate, api_key: str = Depends(get_api_key)):
    with Database() as db:
        solution_id = db.create_solution(solution.name, solution.context)
        if solution_id is None:
            raise HTTPException(status_code=500, detail="Failed to create solution")
        return Solution(solution_id=solution_id, name=solution.name, context=solution.context)


@app.get("/solutions", response_model=List[Solution])
async def get_solutions(api_key: str = Depends(get_api_key)):
    with Database() as db:
        solutions = db.get_solutions()
        return [Solution(solution_id=s[0], name=s[1], context=s[2], created_at=s[3]) for s in solutions]


@app.get("/solutions/{solution_id}", response_model=Solution)
async def get_solution(solution_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        solution = db.get_solution_by_id(solution_id)
        if solution is None:
            raise HTTPException(status_code=404, detail="Solution not found")
        return Solution(solution_id=solution[0], name=solution[1], context=solution[2], created_at=solution[3])


@app.put("/solutions/{solution_id}", response_model=Solution)
async def update_solution(solution_id: int, solution: SolutionUpdate, api_key: str = Depends(get_api_key)):
    with Database() as db:
        success = db.update_solution(solution_id, solution.name, solution.context)
        if not success:
            raise HTTPException(status_code=404, detail="Solution not found")
        updated_solution = db.get_solution_by_id(solution_id)
        if updated_solution is None:
            raise HTTPException(status_code=404, detail="Solution not found after update")
        return Solution(solution_id=updated_solution[0], name=updated_solution[1], context=updated_solution[2],
                        created_at=updated_solution[3])


@app.delete("/solutions/{solution_id}", status_code=204)
async def delete_solution(solution_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        success = db.delete_solution(solution_id)
        if not success:
            raise HTTPException(status_code=404, detail="Solution not found")


# Organizations
@app.post("/organizations", response_model=Organization)
async def create_organization(organization: OrganizationCreate, api_key: str = Depends(get_api_key)):
    with Database() as db:
        organization_id = db.create_organization(organization.name)
        if organization_id is None:
            raise HTTPException(status_code=500, detail="Failed to create organization")
        return Organization(id=organization_id, name=organization.name)


@app.get("/organizations", response_model=List[Organization])
async def get_organizations(api_key: str = Depends(get_api_key)):
    with Database() as db:
        organizations = db.get_organizations()
        return [Organization(id=o[0], name=o[1]) for o in organizations]


@app.get("/organizations/{organization_id}", response_model=Organization)
async def get_organization(organization_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        organization = db.get_organization_by_id(organization_id)
        if organization is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        return Organization(id=organization[0], name=organization[1])


@app.put("/organizations/{organization_id}", response_model=Organization)
async def update_organization(organization_id: int, organization: OrganizationUpdate,
                              api_key: str = Depends(get_api_key)):
    with Database() as db:
        if organization.name is None:
            raise HTTPException(status_code=400, detail="Name is required for update")
        success = db.update_organization(organization_id, organization.name)
        if not success:
            raise HTTPException(status_code=404, detail="Organization not found")
        return Organization(id=organization_id, name=organization.name)


@app.delete("/organizations/{organization_id}", status_code=204)
async def delete_organization(organization_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        success = db.delete_organization(organization_id)
        if not success:
            raise HTTPException(status_code=404, detail="Organization not found")