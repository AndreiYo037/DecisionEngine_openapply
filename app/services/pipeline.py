from collections.abc import Iterable

from app.clients.tinyfish_client import TinyFishClient
from app.config import settings
from app.models import (
    CVProfile,
    ContactCandidate,
    JobOutput,
    MatchJobsResponse,
    NormalizedJob,
    ScoredContact,
)
from app.services.contact_engine import ContactEngine
from app.services.cv_parser import CVParser
from app.services.job_intent import JobIntentExtractor, JobIntentProfile
from app.services.matcher import JobMatcher
from app.services.message_generator import MessageGenerator
from app.services.scorer import ContactScorer


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


class DecisionEngineService:
    def __init__(self) -> None:
        self.tinyfish = TinyFishClient()
        self.cv_parser = CVParser()
        self.matcher = JobMatcher()
        self.intent_extractor = JobIntentExtractor()
        self.contact_engine = ContactEngine(self.tinyfish)
        self.contact_scorer = ContactScorer()
        self.message_generator = MessageGenerator()

    async def ingest_jobs(self, sources: list[str]) -> list[NormalizedJob]:
        collected: list[dict] = []
        for source in sources:
            try:
                scraped = await self.tinyfish.scrape_jobs(source=source, location="Singapore")
            except Exception:
                # Keep the strict pipeline running even when one ingestion source is unavailable.
                continue
            for job in scraped:
                job["source"] = source
            collected.extend(scraped)
        return _normalize_jobs(collected)

    async def parse_cv(self, cv_text: str) -> CVProfile:
        parsed = await self.cv_parser.parse(cv_text)
        project_names = [p.name for p in parsed.projects if p.name]
        notable_project_points = [f"{p.name}: {p.description}" for p in parsed.projects if p.name and p.description]
        merged_projects = (project_names + notable_project_points)[:8]
        interests = list(dict.fromkeys(parsed.interests + parsed.notable_signals))
        return CVProfile(
            skills=parsed.skills,
            domains=parsed.domains,
            experience_level=parsed.experience_level or "intern",
            interests=interests[:8],
            projects=merged_projects,
        )

    async def run(self, cv_text: str, jobs: list[NormalizedJob], include_ingestion: bool, ingestion_sources: list[str]) -> MatchJobsResponse:
        job_pool = list(jobs)
        if include_ingestion:
            ingested = await self.ingest_jobs(ingestion_sources)
            job_pool.extend(ingested)

        profile = await self.parse_cv(cv_text)
        final_results: list[JobOutput] = []
        matcher_input = profile.model_dump()

        for job in job_pool:
            match = await self.matcher.evaluate(
                cv_profile=matcher_input,
                job_description=f"{job.title}\n{job.description}",
            )
            if match.score < settings.match_threshold:
                continue

            intent = await self.intent_extractor.extract(
                job_title=job.title,
                job_description=job.description,
            )
            contacts = await self.contact_engine.find_candidates(
                company=job.company,
                domain=intent.domain or "general",
            )

            top_contacts = self.contact_scorer.rank_contacts(
                contacts=contacts,
                job_company=job.company,
                intent=JobIntentProfile(
                    domain=intent.domain,
                    team=intent.team,
                    seniority=intent.seniority,
                    keywords=intent.keywords,
                    problem_area=intent.problem_area,
                    tools=intent.tools,
                ),
            )
            if not top_contacts:
                continue

            best_contact = top_contacts[0]
            tools_text = ", ".join(intent.tools[:6]) if intent.tools else "not explicitly listed"
            company_insights = (
                f"Company: {job.company}. Domain: {intent.domain}. "
                f"Likely team: {intent.team or 'not explicitly stated'}. "
                f"Problem area: {intent.problem_area or 'not explicitly stated'}. "
                f"Tools: {tools_text}. Role focus: {job.title}."
            )
            outreach = await self.message_generator.generate(
                cv_data=matcher_input,
                job_description=job.description,
                company_insights=company_insights,
                contact_role=best_contact.role,
                user_preferences={
                    "tone": "confident, concise, curious",
                    "max_words": 120,
                },
            )

            api_contacts: list[ScoredContact] = [
                ScoredContact(
                    name=item.name,
                    role=item.role,
                    company=item.company,
                    score=item.total_score,
                    reason=item.reason,
                    source_url=item.source_url,
                )
                for item in top_contacts
            ]
            final_results.append(
                JobOutput(
                    job={
                        "title": job.title,
                        "company": job.company,
                        "match_score": match.score,
                    },
                    contacts=api_contacts,
                    outreach_message=outreach.message,
                )
            )

        return MatchJobsResponse(profile=profile, matched_jobs=final_results)
