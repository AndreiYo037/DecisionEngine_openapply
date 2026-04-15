from pydantic import BaseModel, Field

from app.clients.openai_client import OpenAIClient


class CVProject(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)


class ParsedCV(BaseModel):
    skills: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    projects: list[CVProject] = Field(default_factory=list)
    experience_level: str = "intern"
    interests: list[str] = Field(default_factory=list)
    notable_signals: list[str] = Field(default_factory=list)


class CVParser:
    """Parses raw student CV text into structured, high-signal fields."""

    def __init__(self, openai_client: OpenAIClient | None = None) -> None:
        self.openai = openai_client or OpenAIClient()

    async def parse(self, raw_cv_text: str) -> ParsedCV:
        system_prompt = (
            "You are an expert CV parser for internship candidates. "
            "Extract only strong, evidence-backed signals from the CV. "
            "Prioritize technical skills, project depth, and domain focus. "
            "Do not include weak or speculative items. "
            "Return strict JSON with keys: "
            "skills, domains, projects, experience_level, interests, notable_signals. "
            "projects must be an array of objects with keys: "
            "name, description, technologies."
        )
        user_prompt = (
            "Parse this CV text into structured JSON for downstream matching and personalization.\n"
            "Rules:\n"
            "- skills: concrete technical skills only\n"
            "- domains: focused domains (e.g., data, software engineering, product)\n"
            "- projects: include only meaningful projects with depth\n"
            "- notable_signals: concise items like hackathons, leadership, startup experience\n"
            "- if missing, return empty arrays\n\n"
            f"CV TEXT:\n{raw_cv_text}"
        )

        payload = await self.openai.json_completion(system_prompt, user_prompt)
        return ParsedCV.model_validate(payload)
