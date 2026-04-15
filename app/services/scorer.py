import re
from pydantic import BaseModel, Field

from app.services.contact_engine import ContactCandidate
from app.services.job_intent import JobIntentProfile


class ScoredContact(BaseModel):
    name: str
    role: str
    company: str
    total_score: float = Field(ge=0, le=100)
    reason: str
    source_url: str | None = None


def _role_bucket(role: str) -> str:
    value = role.lower()
    if "university recruiter" in value:
        return "university_recruiter"
    if "recruiter" in value:
        return "technical_recruiter"
    if "hiring manager" in value or "manager" in value:
        return "hiring_manager"
    if any(k in value for k in ("engineer", "scientist", "analyst", "developer", "specialist")):
        return "senior_ic"
    return "other"


class ContactScorer:
    """Scores contacts for outreach quality and hiring relevance."""

    threshold: float = 75.0

    def _hiring_authority(self, role_bucket: str) -> int:
        # Prioritize recruiters and hiring managers by design.
        return {
            "university_recruiter": 100,
            "technical_recruiter": 92,
            "hiring_manager": 88,
            "senior_ic": 60,
            "other": 0,
        }[role_bucket]

    def _response_likelihood(self, role_bucket: str) -> int:
        return {
            "university_recruiter": 95,
            "technical_recruiter": 92,
            "hiring_manager": 72,
            "senior_ic": 50,
            "other": 0,
        }[role_bucket]

    def _accessibility(self, role_lower: str) -> int:
        if any(k in role_lower for k in ("chief", "vp", "director", "head")):
            return 20
        if "senior" in role_lower or "lead" in role_lower:
            return 70
        return 100

    def _role_relevance(self, role_lower: str, intent: JobIntentProfile) -> float:
        domain_tokens = set(re.findall(r"[a-zA-Z]+", (intent.domain or "").lower()))
        role_tokens = set(re.findall(r"[a-zA-Z]+", role_lower))
        overlap = domain_tokens.intersection(role_tokens)
        return min(100, 40 + 30 * len(overlap))

    def _team_match(self, role_lower: str, intent: JobIntentProfile) -> float:
        if not intent.team:
            return 60
        team_tokens = set(re.findall(r"[a-zA-Z]+", intent.team.lower()))
        role_tokens = set(re.findall(r"[a-zA-Z]+", role_lower))
        overlap = team_tokens.intersection(role_tokens)
        if not overlap:
            return 55
        return min(100, 50 + 25 * len(overlap))

    def score_one(
        self,
        contact: ContactCandidate,
        *,
        job_company: str,
        intent: JobIntentProfile,
    ) -> ScoredContact | None:
        # Hard reject on company mismatch.
        if contact.company.lower().strip() != job_company.lower().strip():
            return None

        role_lower = contact.role.lower()
        bucket = _role_bucket(role_lower)

        hiring_authority = self._hiring_authority(bucket)
        role_relevance = self._role_relevance(role_lower, intent)
        team_match = self._team_match(role_lower, intent)
        response_likelihood = self._response_likelihood(bucket)
        accessibility = self._accessibility(role_lower)

        total_score = (
            0.40 * hiring_authority
            + 0.20 * role_relevance
            + 0.15 * team_match
            + 0.15 * response_likelihood
            + 0.10 * accessibility
        )

        # Hard reject threshold.
        if total_score < self.threshold:
            return None

        reason = (
            f"{bucket.replace('_', ' ')}; authority={hiring_authority}, "
            f"domain/team relevance={round((role_relevance + team_match) / 2, 1)}."
        )
        return ScoredContact(
            name=contact.name,
            role=contact.role,
            company=contact.company,
            total_score=round(total_score, 2),
            reason=reason,
            source_url=contact.source_url,
        )

    def rank_contacts(
        self,
        contacts: list[ContactCandidate],
        *,
        job_company: str,
        intent: JobIntentProfile,
    ) -> list[ScoredContact]:
        scored: list[ScoredContact] = []
        seen: set[tuple[str, str]] = set()

        for candidate in contacts:
            item = self.score_one(candidate, job_company=job_company, intent=intent)
            if not item:
                continue
            key = (item.name.lower(), item.role.lower())
            if key in seen:
                continue
            seen.add(key)
            scored.append(item)

        scored.sort(key=lambda x: x.total_score, reverse=True)
        return scored[:3]
