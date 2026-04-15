from pydantic import BaseModel, Field

from app.clients.openai_client import OpenAIClient


class OutreachResult(BaseModel):
    message: str
    personalization_points: list[str] = Field(default_factory=list)


class MessageGenerator:
    """Generates high-signal, personalized outreach messages for internship contacts."""

    def __init__(self, openai_client: OpenAIClient | None = None) -> None:
        self.openai = openai_client or OpenAIClient()

    async def generate(
        self,
        *,
        cv_data: dict,
        job_description: str,
        company_insights: str,
        contact_role: str,
        user_preferences: dict | None = None,
    ) -> OutreachResult:
        preferences = user_preferences or {}

        system_prompt = (
            "You write highly personalized internship outreach messages. "
            "Return strict JSON with keys: message, personalization_points. "
            "Hard constraints: max 120 words, no generic phrases, tone must be confident, concise, and curious. "
            "Message must include all of the following: "
            "(1) one specific project or technical skill from CV, "
            "(2) one specific reference to company or team context, "
            "(3) one clear and polite ask for advice or opportunity relevance. "
            "Do not invent fake facts, achievements, or contacts."
        )
        user_prompt = (
            "Generate a personalized outreach message.\n"
            "Quality bar: this should feel tailored and actionable, not templated.\n\n"
            "INPUTS:\n"
            f"CV DATA: {cv_data}\n"
            f"JOB DESCRIPTION: {job_description}\n"
            f"COMPANY INSIGHTS: {company_insights}\n"
            f"CONTACT ROLE: {contact_role}\n"
            f"USER PREFERENCES: {preferences}\n\n"
            "Output requirements:\n"
            "- message: <=120 words, one compact paragraph\n"
            "- personalization_points: short bullet-like list of concrete anchors used, such as:\n"
            "  - matched project\n"
            "  - company reference\n"
            "  - team relevance"
        )

        payload = await self.openai.json_completion(system_prompt, user_prompt)
        return OutreachResult.model_validate(payload)
