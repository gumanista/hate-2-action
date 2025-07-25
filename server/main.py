from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from server.schemas import (
    ProcessMessageRequest,
    Message,
    Project, ProjectCreate, ProjectUpdate,
    Problem, ProblemCreate, ProblemUpdate,
    Solution, SolutionCreate, SolutionUpdate,
    Organization, OrganizationCreate, OrganizationUpdate, OrganizationFull,
    Response # Import the unified Response schema
)
from server.pipeline import run as process_message_run
from server.database import Database
import logging
from typing import List, Optional
from server.security import get_api_key


app = FastAPI()
origins = [
    "http://localhost:3000",
    "http://localhost:3009",
    "https://hate2action.devalma.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/")
async def root(api_key: str = Depends(get_api_key)):
    return {"message": "API is running"}
@app.post("/process-message", response_model=Response) # Use the unified Response schema
async def process_message(request: ProcessMessageRequest, api_key: str = Depends(get_api_key)):
    try:
        logger.info(f"Processing message: {request.message}")
        result = process_message_run(request.message) # This now returns the unified Response
        logger.info("Message processed successfully.")
        return result
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Messages
@app.get("/messages", response_model=List[Message])
async def get_messages(api_key: str = Depends(get_api_key)):
    with Database() as db:
        messages_data = db.get_messages()
        messages_with_responses = []
        for m in messages_data:
            message_id = m[0]
            response_data = db.get_response_by_message_id(message_id)
            response_obj = None
            if response_data:
                response_obj = Response(
                    response_id=response_data[0],
                    message_id=response_data[1],
                    text=response_data[2],
                    created_at=response_data[3],
                    problems=[], # These fields are not available when fetching from responses table directly
                    solutions=[],
                    projects=[]
                )
            messages_with_responses.append(Message(
                message_id=m[0],
                user_id=m[1],
                user_username=m[2],
                chat_title=m[3],
                text=m[4],
                response=response_obj
            ))
        return messages_with_responses


@app.get("/messages/{message_id}", response_model=Message)
async def get_message(message_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        message = db.get_message_by_id(message_id)
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Fetch response if it exists
        response_data = db.get_response_by_message_id(message_id)
        response_obj = None
        if response_data:
            # For a single message, we can try to fetch associated problems, solutions, projects
            # This would require new database methods or a more complex query
            # For now, we'll just populate the text and basic response info
            response_obj = Response(
                response_id=response_data[0],
                message_id=response_data[1],
                text=response_data[2],
                created_at=response_data[3],
                problems=[], # Placeholder
                solutions=[], # Placeholder
                projects=[] # Placeholder
            )

        return Message(
            message_id=message[0],
            user_id=message[1],
            user_username=message[2],
            chat_title=message[3],
            text=message[4],
            response=response_obj # Attach the response object
        )

# Projects
@app.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate, api_key: str = Depends(get_api_key)):
    with Database() as db:
        project_id = db.create_project(
            project.name,
            project.description,
            project.website,
            project.contact_email,
            project.organization_id
        )
        if project_id is None:
            raise HTTPException(status_code=500, detail="Failed to create project")
        return Project(
            project_id=project_id,
            name=project.name,
            description=project.description,
            website=project.website,
            contact_email=project.contact_email,
            organization_id=project.organization_id
        )


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
    logger.info(f"Received organization data: {organization.dict()}")
    with Database() as db:
        organization_id = db.create_organization(
            organization.name,
            organization.description,
            organization.website,
            organization.contact_email
        )
        if organization_id is None:
            raise HTTPException(status_code=500, detail="Failed to create organization")
        return Organization(organization_id=organization_id, name=organization.name, description=organization.description, website=organization.website, contact_email=organization.contact_email)


@app.get("/organizations", response_model=List[Organization])
async def get_organizations(api_key: str = Depends(get_api_key)):
    with Database() as db:
        organizations = db.get_organizations()
        return [Organization(organization_id=o[0], name=o[1], description=o[2], website=o[3], contact_email=o[4]) for o in organizations]


@app.get("/organizations/{organization_id}", response_model=OrganizationFull)
async def get_organization(organization_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        organization_data = db.get_organization_by_id(organization_id)
        if organization_data is None:
            raise HTTPException(status_code=404, detail="Organization not found")

        projects_data = db.get_projects_by_organization(organization_id)
        
        # Create a dictionary from the organization data tuple
        organization_dict = {
            "organization_id": organization_data[0],
            "name": organization_data[1],
            "description": organization_data[2],
            "website": organization_data[3],
            "contact_email": organization_data[4]
        }

        # Create Project objects from the projects data
        projects = [
            Project(
                project_id=p[0],
                name=p[1],
                description=p[2],
                created_at=p[3],
                website=p[4],
                contact_email=p[5],
                organization_id=p[6]
            ) for p in projects_data
        ]

        # Combine them into the OrganizationFull model
        organization_full = OrganizationFull(**organization_dict, projects=projects)
        return organization_full

@app.get("/organizations/{organization_id}/projects", response_model=List[Project])
async def get_projects_by_organization(organization_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        projects = db.get_projects_by_organization(organization_id)
        if projects is None:
            raise HTTPException(status_code=404, detail="No projects found for this organization")
        return [Project(project_id=p[0], name=p[1], description=p[2], created_at=p[3], website=p[4],
                        contact_email=p[5]) for p in projects]

@app.put("/organizations/{organization_id}", response_model=Organization)
async def update_organization(organization_id: int, organization: OrganizationUpdate,
                              api_key: str = Depends(get_api_key)):
    with Database() as db:
        success = db.update_organization(
            organization_id,
            organization.name,
            organization.description,
            organization.website,
            organization.contact_email
        )
        if not success:
            raise HTTPException(status_code=404, detail="Organization not found")

        updated_organization = db.get_organization_by_id(organization_id)
        if updated_organization is None:
            raise HTTPException(status_code=404, detail="Organization not found after update")

        return Organization(
            organization_id=updated_organization[0],
            name=updated_organization[1],
            description=updated_organization[2],
            website=updated_organization[3],
            contact_email=updated_organization[4]
        )


@app.delete("/organizations/{organization_id}", status_code=204)
async def delete_organization(organization_id: int, api_key: str = Depends(get_api_key)):
    with Database() as db:
        success = db.delete_organization(organization_id)
        if not success:
            raise HTTPException(status_code=404, detail="Organization not found")

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return JSONResponse(get_openapi(title="Hate2Action API", version="1.0.0", routes=app.routes))


@app.get("/docs", include_in_schema=False)
async def get_documentation():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")