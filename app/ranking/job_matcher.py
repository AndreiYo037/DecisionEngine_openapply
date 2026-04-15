import re

from app.models import Job, UserProfile


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9+#\.]{2,}", text)}


def compute_job_fit(job: Job, user_profile: UserProfile) -> float:
    """
    Compute job-to-profile fit score (0-1) using weighted overlap:
    - skills overlap
    - project relevance overlap
    - experience/education overlap
    """
    job_tokens = _tokenize(f"{job.title}\n{job.description}")

    skill_tokens = _tokenize(" ".join(user_profile.skills))
    project_tokens = _tokenize(" ".join(user_profile.projects))
    background_tokens = _tokenize(f"{user_profile.experience}\n{user_profile.education}")

    skill_score = 0.0
    if skill_tokens:
        skill_score = len(skill_tokens.intersection(job_tokens)) / len(skill_tokens)

    project_score = 0.0
    if project_tokens:
        project_score = len(project_tokens.intersection(job_tokens)) / len(project_tokens)

    background_score = 0.0
    if background_tokens:
        background_score = len(background_tokens.intersection(job_tokens)) / len(background_tokens)

    weighted = 0.55 * skill_score + 0.30 * project_score + 0.15 * background_score
    return round(min(1.0, max(0.0, weighted)), 4)
