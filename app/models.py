from typing import Literal

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience: str = ""
    education: str = ""
    projects: list[str] = Field(default_factory=list)


class Job(BaseModel):
    title: str
    company: str
    description: str
    location: str | None = None
    job_url: str
    job_id: str
    source: Literal["manual"] = "manual"


class Contact(BaseModel):
    name: str
    role: str
    linkedin_url: str | None = None
    email: str | None = None
    relevance_score: float = Field(ge=0.0, le=1.0)


class RankJobsRequest(BaseModel):
    job_urls: list[str] = Field(default_factory=list)
    user_profile: UserProfile
    top_k: int = Field(default=5, ge=3, le=5)


class RankedJobResult(BaseModel):
    title: str
    company: str
    job_url: str
    job_fit: float = Field(ge=0.0, le=1.0)
    contact_score: float = Field(ge=0.0, le=1.0)
    top_contacts: list[Contact] = Field(default_factory=list)
    reason: str
