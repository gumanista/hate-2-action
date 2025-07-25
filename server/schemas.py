from pydantic import BaseModel
from typing import List, Optional


class Project(BaseModel):
    project_id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    organization_id: Optional[int] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    organization_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None


class Problem(BaseModel):
    problem_id: int
    name: str
    context: Optional[str] = None
    created_at: Optional[str] = None
    is_processed: Optional[int] = 0

    class Config:
        orm_mode = True
        from_attributes = True


class ProblemCreate(BaseModel):
    name: str
    context: Optional[str] = None


class ProblemUpdate(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None
    is_processed: Optional[int] = None


class Solution(BaseModel):
    solution_id: int
    name: str
    context: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True


class SolutionCreate(BaseModel):
    name: str
    context: Optional[str] = None


class SolutionUpdate(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None


class Organization(BaseModel):
    organization_id: int
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    projects: Optional[List[Project]] = None


class OrganizationFull(Organization):
    projects: List[Project] = []
 
class OrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None


class ProcessMessageRequest(BaseModel):
    message: str
    response_style: str


class Response(BaseModel):
    response_id: Optional[int] = None # Make optional for initial creation
    message_id: Optional[int] = None # Make optional for initial creation
    text: str
    created_at: Optional[str] = None
    problems: List[Problem] = []
    solutions: List[Solution] = []
    projects: List[Project] = []

    class Config:
        orm_mode = True
        from_attributes = True


class Message(BaseModel):
    message_id: int
    user_id: int
    user_username: str
    chat_title: Optional[str] = None
    text: str
    response: Optional[Response] = None # Add optional response field

    class Config:
        orm_mode = True
        from_attributes = True