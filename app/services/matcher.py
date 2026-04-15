from pydantic import BaseModel, Field

from app.clients.openai_client import OpenAIClient


class MatchEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    reasoning: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class JobMatcher:
    """Computes employability-focused CV-job match scores."""

    def __init__(self, openai_client: OpenAIClient | None = None) -> None:
        self.openai = openai_client or OpenAIClient()

    async def evaluate(self, cv_profile: dict, job_description: str) -> MatchEvaluation:
        system_prompt = (
            "You are an internship fit evaluator. "
            "Score candidate-job fit from 0-100 for real employability, not keyword stuffing. "
            "Penalize role/domain mismatch and shallow overlap. "
            "Reward strong alignment between project depth and core job responsibilities. "
            "Return strict JSON with keys: score, reasoning, matched_skills, missing_skills."
        )
        user_prompt = (
            "Evaluate this candidate against the job.\n"
            "Scoring rules:\n"
            "- Score >= 70 means strong fit.\n"
            "- Penalize irrelevant roles or domain mismatch.\n"
            "- Reward meaningful project alignment and hands-on evidence.\n"
            "- matched_skills: skills clearly present in CV and relevant to role.\n"
            "- missing_skills: critical missing skills for this role.\n\n"
            f"CV STRUCTURED DATA:\n{cv_profile}\n\n"
            f"JOB DESCRIPTION:\n{job_description}"
        )

        payload = await self.openai.json_completion(system_prompt, user_prompt)
        return MatchEvaluation.model_validate(payload)
