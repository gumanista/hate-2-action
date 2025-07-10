from pydantic import BaseModel
from typing import Optional


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
    is_processed: Optional[bool] = False

    class Config:
        orm_mode = True
        from_attributes = True


class ProblemCreate(BaseModel):
    name: str
    context: Optional[str] = None


class ProblemUpdate(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None
    is_processed: Optional[bool] = None


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