from pydantic import BaseModel, Field

from app.clients.openai_client import OpenAIClient


class JobIntentProfile(BaseModel):
    domain: str = "general"
    team: str | None = None
    seniority: str = "intern"
    keywords: list[str] = Field(default_factory=list)
    problem_area: str = ""
    tools: list[str] = Field(default_factory=list)


class JobIntentExtractor:
    """Extracts hiring intent signals from job descriptions for contact targeting."""

    def __init__(self, openai_client: OpenAIClient | None = None) -> None:
        self.openai = openai_client or OpenAIClient()

    async def extract(self, job_title: str, job_description: str) -> JobIntentProfile:
        system_prompt = (
            "You extract structured hiring intent from internship job descriptions. "
            "Return strict JSON with keys: domain, team, seniority, keywords, problem_area, tools. "
            "domain should preferably be one of: data, swe, marketing, product, business, general. "
            "Infer team whenever possible from context such as responsibilities, stack, or org naming. "
            "Infer the real problem_area the intern will likely work on (e.g., recommendation systems, growth analytics). "
            "Extract concrete tools mentioned (e.g., Python, SQL, Tableau, React). "
            "If uncertain, set team to null and use empty values rather than guessing."
        )
        user_prompt = (
            "Extract intent for downstream contact selection.\n"
            "Rules:\n"
            "- domain: pick the best-fit domain\n"
            "- team: infer likely team if evidence exists (e.g., data platform, growth, infra, analytics)\n"
            "- seniority: usually intern unless stated otherwise\n"
            "- keywords: high-signal terms for contact search and scoring\n"
            "- problem_area: what the intern is actually expected to solve/build\n"
            "- tools: explicit tools/technologies used in the role\n\n"
            f"JOB TITLE:\n{job_title}\n\n"
            f"JOB DESCRIPTION:\n{job_description}"
        )

        payload = await self.openai.json_completion(system_prompt, user_prompt)
        return JobIntentProfile.model_validate(payload)
