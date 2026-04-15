import hashlib
import re
from typing import Optional

from app.clients.tinyfish_client import TinyFishClient
from app.models import Job

_PAGE_CACHE: dict[str, Job] = {}


def _job_id_from_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _extract_title(payload: dict, fallback_url: str) -> str:
    candidates = [
        payload.get("title"),
        payload.get("metadata", {}).get("title"),
        payload.get("data", {}).get("title"),
    ]
    for item in candidates:
        if isinstance(item, str) and item.strip():
            return item.strip()[:160]
    return fallback_url


def _extract_description(payload: dict) -> str:
    candidates = [
        payload.get("markdown"),
        payload.get("content"),
        payload.get("text"),
        payload.get("data", {}).get("markdown"),
    ]
    for item in candidates:
        if isinstance(item, str) and item.strip():
            return item.strip()[:12000]
    return ""


def _extract_company(title: str, description: str) -> str:
    for splitter in (" - ", " | ", " at "):
        parts = title.split(splitter)
        if len(parts) > 1 and parts[-1].strip():
            return parts[-1].strip()[:80]

    # Weak fallback from description (kept intentionally conservative).
    match = re.search(r"\b(?:at|with)\s+([A-Z][A-Za-z0-9&.\- ]{1,60})", description)
    if match:
        return match.group(1).strip()[:80]
    return "Unknown Company"


def _extract_location(title: str, description: str) -> Optional[str]:
    joined = f"{title}\n{description}"
    if "singapore" in joined.lower():
        return "Singapore"
    return None


def ingest_jobs_from_urls(job_urls: list[str]) -> list[Job]:
    """
    One URL -> One job.
    Loads each URL via TinyFish Fetch API and normalizes job fields.
    """
    tinyfish = TinyFishClient()
    jobs: list[Job] = []

    for raw_url in job_urls:
        url = raw_url.strip()
        if not url:
            continue
        if url in _PAGE_CACHE:
            jobs.append(_PAGE_CACHE[url])
            continue

        payload = tinyfish.fetch_url(url)
        title = _extract_title(payload, url)
        description = _extract_description(payload)
        company = _extract_company(title, description)
        location = _extract_location(title, description)

        job = Job(
            title=title,
            company=company,
            description=description,
            location=location,
            job_url=url,
            job_id=_job_id_from_url(url),
            source="manual",
        )
        _PAGE_CACHE[url] = job
        jobs.append(job)

    return jobs
