from pydantic import BaseModel

from app.clients.openai_client import OpenAIClient


class ContactEnrichment(BaseModel):
    function: str
    specialization: str = ""
    seniority: str = ""
    focus_area: str = ""


class ContactEnrichmentService:
    """Extracts concise outreach-relevant signals from contact metadata."""

    def __init__(self, openai_client: OpenAIClient | None = None) -> None:
        self.openai = openai_client or OpenAIClient()

    async def enrich(self, *, name: str, role: str, snippet: str) -> ContactEnrichment:
        system_prompt = (
            "You classify professional contact metadata for internship outreach personalization. "
            "Return strict JSON with keys: function, specialization, seniority, focus_area. "
            "Keep outputs concise and evidence-based. "
            "Infer likely hiring involvement from role wording, but do not hallucinate. "
            "If unknown, return empty string for that field. "
            "For function, prefer one of: recruiter, hiring_manager, engineering_manager, "
            "team_lead, senior_ic, hr, other."
        )
        user_prompt = (
            "Extract contact enrichment fields from the provided metadata.\n"
            "Rules:\n"
            "- function: role type label (concise)\n"
            "- specialization: hiring or domain specialty if explicitly implied\n"
            "- seniority: concise seniority tag if indicated\n"
            "- focus_area: team/domain focus if indicated\n"
            "- do not invent company/team details not present or implied\n\n"
            f"NAME: {name}\n"
            f"ROLE: {role}\n"
            f"SNIPPET: {snippet}"
        )

        payload = await self.openai.json_completion(system_prompt, user_prompt)
        return ContactEnrichment.model_validate(payload)
