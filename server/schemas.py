from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class OrganizationIn(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    organization_id: int
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    created_at: Optional[datetime] = None


class ProjectIn(BaseModel):
    name: str
    description: Optional[str] = None
    organization_id: Optional[int] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_id: int
    name: str
    description: Optional[str] = None
    organization_id: Optional[int] = None
    created_at: Optional[datetime] = None


class ProblemIn(BaseModel):
    name: str
    context: Optional[str] = None
    content: Optional[str] = None
    is_processed: Optional[bool] = None


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    problem_id: int
    name: str
    context: Optional[str] = None
    content: Optional[str] = None
    is_processed: bool = False
    created_at: Optional[datetime] = None


class SolutionIn(BaseModel):
    name: str
    context: Optional[str] = None
    content: Optional[str] = None


class SolutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    solution_id: int
    name: str
    context: Optional[str] = None
    content: Optional[str] = None
    created_at: Optional[datetime] = None


class ProcessMessageIn(BaseModel):
    message: str
    response_style: str = "normal"
