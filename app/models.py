from typing import Any, Literal

from pydantic import BaseModel, Field


class NormalizedJob(BaseModel):
    title: str
    company: str
    description: str
    location: str = "Singapore"
    source: str | None = None


class CVProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    experience_level: str = "intern"
    interests: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    score: int = Field(ge=0, le=100)
    reasoning: str


class JobIntent(BaseModel):
    domain: str = "general"
    team: str | None = None
    seniority: str = "intern"


class ContactCandidate(BaseModel):
    name: str
    role: str
    company: str
    source_url: str | None = None
    snippet: str | None = None


class ScoredContact(BaseModel):
    name: str
    role: str
    company: str
    score: float = Field(ge=0, le=100)
    reason: str
    source_url: str | None = None


class OutreachMessage(BaseModel):
    message: str
    tone: Literal["professional, concise"] = "professional, concise"
    length: str = "<120 words"


class JobOutput(BaseModel):
    job: dict[str, Any]
    contacts: list[ScoredContact]
    outreach_message: str


class MatchJobsRequest(BaseModel):
    cv_text: str | None = None
    jobs: list[NormalizedJob] = Field(default_factory=list)
    include_ingestion: bool = False
    include_debug: bool = False
    ingestion_sources: list[str] = Field(
        default_factory=lambda: [
            "greenhouse",
            "lever",
            "workday",
            "mycareersfuture",
            "company_career_pages",
        ]
    )


class MatchJobsResponse(BaseModel):
    profile: CVProfile
    matched_jobs: list[JobOutput]


class ActionableJob(BaseModel):
    title: str
    company: str
    match_score: int = Field(ge=0, le=100)


class ActionableOpportunity(BaseModel):
    job: ActionableJob
    best_contact: ScoredContact
    alternate_contacts: list[ScoredContact] = Field(default_factory=list)
    message: str


class ActionableMatchJobsResponse(BaseModel):
    profile: CVProfile
    opportunities: list[ActionableOpportunity]
    debug: dict[str, Any] | None = None
