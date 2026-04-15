import re
from collections.abc import Iterable

from app.clients.openai_client import OpenAIClient
from app.clients.tinyfish_client import TinyFishClient
from app.config import settings
from app.models import (
    CVProfile,
    ContactCandidate,
    JobIntent,
    JobOutput,
    MatchJobsResponse,
    MatchResult,
    NormalizedJob,
    OutreachMessage,
    ScoredContact,
)


def _normalize_jobs(raw_jobs: Iterable[dict]) -> list[NormalizedJob]:
    normalized: list[NormalizedJob] = []
    for item in raw_jobs:
        if not all(k in item for k in ("title", "company", "description")):
            continue
        location = item.get("location") or "Singapore"
        if "singapore" not in location.lower():
            continue
        normalized.append(
            NormalizedJob(
                title=item["title"].strip(),
                company=item["company"].strip(),
                description=item["description"].strip(),
                location="Singapore",
                source=item.get("source"),
            )
        )
    return normalized


def _clean_name_from_snippet(snippet: str) -> str:
    candidate = snippet.split("-")[0].strip()
    if len(candidate) < 3:
        return "Unknown Candidate"
    return candidate


def _role_bucket(role: str) -> str:
    value = role.lower()
    if "university recruiter" in value:
        return "university_recruiter"
    if "recruiter" in value:
        return "technical_recruiter"
    if "hiring manager" in value or "manager" in value:
        return "hiring_manager"
    if any(k in value for k in ("engineer", "scientist", "analyst", "specialist", "developer")):
        return "senior_ic"
    return "other"


class DecisionEngineService:
    def __init__(self) -> None:
        self.openai = OpenAIClient()
        self.tinyfish = TinyFishClient()

    async def ingest_jobs(self, sources: list[str]) -> list[NormalizedJob]:
        collected: list[dict] = []
        for source in sources:
            scraped = await self.tinyfish.scrape_jobs(source=source, location="Singapore")
            for job in scraped:
                job["source"] = source
            collected.extend(scraped)
        return _normalize_jobs(collected)

    async def parse_cv(self, cv_text: str) -> CVProfile:
        system = (
            "Extract internship candidate profile from CV text. "
            "Return strict JSON with keys: skills, domains, experience_level, interests, projects."
        )
        user = f"CV:\n{cv_text}"
        payload = await self.openai.json_completion(system, user)
        return CVProfile.model_validate(payload)

    async def score_job_match(self, profile: CVProfile, job: NormalizedJob) -> MatchResult:
        system = (
            "Score internship candidate fit for job from 0-100. "
            "Criteria: skill overlap, domain relevance, experience alignment, keyword similarity. "
            "Return JSON with score (int), reasoning."
        )
        user = (
            f"Candidate profile: {profile.model_dump_json()}\n"
            f"Job: {job.model_dump_json()}\n"
            "Weight quality over quantity and avoid inflated scores."
        )
        payload = await self.openai.json_completion(system, user)
        return MatchResult.model_validate(payload)

    async def analyze_intent(self, job: NormalizedJob) -> JobIntent:
        system = (
            "Extract job intent from description. Return JSON keys: domain, team, seniority. "
            "Domain should be one of: data, swe, marketing, product, business, general."
        )
        user = f"Job title: {job.title}\nJob description:\n{job.description}"
        payload = await self.openai.json_completion(system, user)
        return JobIntent.model_validate(payload)

    async def find_contacts(self, job: NormalizedJob, intent: JobIntent) -> list[ContactCandidate]:
        domain = intent.domain or "general"
        queries = [
            f'site:linkedin.com "{job.company}" "technical recruiter" Singapore',
            f'site:linkedin.com "{job.company}" "{domain} manager" Singapore',
            f'site:linkedin.com "{job.company}" "{domain} lead" Singapore',
        ]

        candidates: list[ContactCandidate] = []
        for query in queries:
            results = await self.tinyfish.web_search(query=query, limit=5)
            for result in results:
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                url = result.get("url")
                if "linkedin.com" not in (url or "") and "linkedin.com" not in (title + snippet).lower():
                    continue
                role_text = title or snippet
                name = _clean_name_from_snippet(title or snippet)
                candidate = ContactCandidate(
                    name=name,
                    role=role_text[:140],
                    company=job.company,
                    source_url=url,
                    snippet=snippet[:300] if snippet else None,
                )
                candidates.append(candidate)
        return candidates

    def score_contact(self, contact: ContactCandidate, intent: JobIntent, job: NormalizedJob) -> ScoredContact | None:
        role = contact.role.lower()
        role_type = _role_bucket(role)

        hiring_authority_map = {
            "university_recruiter": 100,
            "technical_recruiter": 90,
            "hiring_manager": 85,
            "senior_ic": 60,
            "other": 0,
        }
        response_likelihood_map = {
            "university_recruiter": 95,
            "technical_recruiter": 95,
            "hiring_manager": 70,
            "senior_ic": 50,
            "other": 0,
        }

        if job.company.lower() not in (contact.company or "").lower():
            return None

        domain_tokens = set(re.findall(r"[a-zA-Z]+", (intent.domain or "").lower()))
        role_tokens = set(re.findall(r"[a-zA-Z]+", role))
        keyword_overlap = domain_tokens.intersection(role_tokens)
        role_relevance = min(100, 40 + 30 * len(keyword_overlap))
        team_match = 60
        if intent.team:
            team_tokens = set(re.findall(r"[a-zA-Z]+", intent.team.lower()))
            team_overlap = team_tokens.intersection(role_tokens)
            if team_overlap:
                team_match = min(100, 50 + 25 * len(team_overlap))

        if "head" in role or "director" in role or "vp" in role or "chief" in role:
            accessibility = 20
        elif "senior" in role or "lead" in role:
            accessibility = 70
        else:
            accessibility = 100

        hiring_authority = hiring_authority_map[role_type]
        response_likelihood = response_likelihood_map[role_type]

        total_score = (
            0.40 * hiring_authority
            + 0.20 * role_relevance
            + 0.15 * team_match
            + 0.15 * response_likelihood
            + 0.10 * accessibility
        )

        if hiring_authority == 0 or role_relevance < 50:
            return None
        if total_score < settings.contact_threshold:
            return None

        reason = f"{role_type.replace('_', ' ')} with strong relevance to {intent.domain or 'job domain'}."
        return ScoredContact(
            name=contact.name,
            role=contact.role,
            company=job.company,
            score=round(total_score, 2),
            reason=reason,
            source_url=contact.source_url,
        )

    async def generate_outreach(self, profile: CVProfile, job: NormalizedJob, contact: ScoredContact) -> OutreachMessage:
        system = (
            "Write a short personalized outreach message for internship networking. "
            "Return JSON with keys: message, tone, length. "
            "Tone must be 'professional, concise' and length '<120 words'."
        )
        user = (
            f"Candidate profile: {profile.model_dump_json()}\n"
            f"Job: {job.model_dump_json()}\n"
            f"Contact: {contact.model_dump_json()}\n"
            "Guidelines: mention relevant skills/projects, interest in team/domain, "
            "ask for advice or opportunity without begging, no generic fluff."
        )
        payload = await self.openai.json_completion(system, user)
        return OutreachMessage.model_validate(payload)

    async def run(self, cv_text: str, jobs: list[NormalizedJob], include_ingestion: bool, ingestion_sources: list[str]) -> MatchJobsResponse:
        job_pool = list(jobs)
        if include_ingestion:
            ingested = await self.ingest_jobs(ingestion_sources)
            job_pool.extend(ingested)

        profile = await self.parse_cv(cv_text)
        final_results: list[JobOutput] = []

        for job in job_pool:
            match = await self.score_job_match(profile, job)
            if match.score < settings.match_threshold:
                continue

            intent = await self.analyze_intent(job)
            contacts = await self.find_contacts(job, intent)

            scored_contacts: list[ScoredContact] = []
            for c in contacts:
                scored = self.score_contact(c, intent, job)
                if scored:
                    scored_contacts.append(scored)

            deduped: dict[tuple[str, str], ScoredContact] = {}
            for contact in sorted(scored_contacts, key=lambda s: s.score, reverse=True):
                key = (contact.name.lower(), contact.role.lower())
                if key not in deduped:
                    deduped[key] = contact

            top_contacts = list(deduped.values())[:3]
            if not top_contacts:
                continue

            outreach = await self.generate_outreach(profile, job, top_contacts[0])
            final_results.append(
                JobOutput(
                    job={
                        "title": job.title,
                        "company": job.company,
                        "match_score": match.score,
                    },
                    contacts=top_contacts,
                    outreach_message=outreach.message,
                )
            )

        return MatchJobsResponse(profile=profile, matched_jobs=final_results)
