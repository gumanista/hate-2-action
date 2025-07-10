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
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    projects: Optional[List[Project]] = None


class OrganizationCreate(BaseModel):
    name: str


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None


class ProcessMessageRequest(BaseModel):
    message: str


class ProcessMessageResponse(BaseModel):
    reply_text: str
    problems: list[Problem]
    solutions: list[Solution]
    projects: list[Project]


class Message(BaseModel):
    message_id: int
    user_id: int
    user_username: str
    chat_title: Optional[str] = None
    text: str

    class Config:
        orm_mode = True
        from_attributes = True