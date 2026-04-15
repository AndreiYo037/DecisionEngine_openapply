from app.config import settings
from app.enrichment.contact_finder import compute_contact_score, find_contacts
from app.models import Job, RankedJobResult, UserProfile
from app.ranking.job_matcher import compute_job_fit


def score_job(job: Job, user_profile: UserProfile) -> dict:
    job_fit = compute_job_fit(job, user_profile)
    contacts = find_contacts(job.company, job.title)
    contact_score = compute_contact_score(contacts)

    final_score = 0.6 * job_fit + 0.4 * contact_score
    return {
        "job": job,
        "job_fit": job_fit,
        "contacts": contacts,
        "contact_score": contact_score,
        "final_score": round(final_score, 4),
    }


def apply_thresholds(scored_jobs: list[dict]) -> list[dict]:
    return [
        item
        for item in scored_jobs
        if item["job_fit"] >= settings.job_fit_threshold
        and item["contact_score"] >= settings.contact_score_threshold
    ]


def _build_reason(job_fit: float, contact_score: float, top_contacts_count: int) -> str:
    return (
        f"Recommended for strong profile alignment (fit={job_fit:.2f}) and reachable contacts "
        f"(contact_score={contact_score:.2f}, contacts={top_contacts_count}). "
        "Start with recruiter or hiring-manager contacts first."
    )


def rank_jobs(job_list: list[Job], user_profile: UserProfile, top_k: int = 5) -> list[RankedJobResult]:
    scored = [score_job(job, user_profile) for job in job_list]
    filtered = apply_thresholds(scored)
    sorted_jobs = sorted(filtered, key=lambda x: x["final_score"], reverse=True)

    return [
        RankedJobResult(
            title=item["job"].title,
            company=item["job"].company,
            job_url=item["job"].job_url,
            job_fit=item["job_fit"],
            contact_score=item["contact_score"],
            top_contacts=item["contacts"][:5],
            reason=_build_reason(
                job_fit=item["job_fit"],
                contact_score=item["contact_score"],
                top_contacts_count=min(5, len(item["contacts"])),
            ),
        )
        for item in sorted_jobs[:top_k]
    ]
