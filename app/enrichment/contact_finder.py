import re

from app.clients.tinyfish_client import TinyFishClient
from app.models import Contact


def _extract_name(text: str) -> str:
    first_segment = re.split(r"\s[-|]\s", text.strip())[0]
    first_segment = re.sub(r"\s*\(.*?\)\s*", " ", first_segment).strip()
    if not first_segment:
        return "Unknown Contact"
    if len(first_segment.split()) < 2:
        return "Unknown Contact"
    return first_segment[:80]


def _extract_email(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else None


def _role_priority(role: str) -> float:
    value = role.lower()
    if "recruiter" in value:
        return 1.0
    if "hiring manager" in value:
        return 0.95
    if "manager" in value:
        return 0.85
    if "lead" in value:
        return 0.75
    if any(k in value for k in ("engineer", "scientist", "analyst", "developer")):
        return 0.6
    return 0.35


def find_contacts(company: str, role: str) -> list[Contact]:
    tinyfish = TinyFishClient()
    base_queries = [
        f'site:linkedin.com "{company}" recruiter "{role}"',
        f'site:linkedin.com "{company}" "hiring manager" "{role}"',
        f'site:linkedin.com "{company}" "{role}"',
        f'"{company}" "{role}" email',
    ]

    candidates: list[Contact] = []
    seen: set[tuple[str, str]] = set()

    for query in base_queries:
        results = tinyfish.web_search(query=query, limit=8)
        for item in results:
            title = (item.get("title") or "").strip()
            snippet = (item.get("snippet") or "").strip()
            url = (item.get("url") or "").strip()
            if not (title or snippet):
                continue

            name = _extract_name(title or snippet)
            role_text = (title or snippet)[:160]
            linkedin_url = url if "linkedin.com" in url.lower() else None
            email = _extract_email(f"{title}\n{snippet}")

            relevance = _role_priority(role_text)
            if linkedin_url:
                relevance += 0.1
            if email:
                relevance += 0.2
            relevance = min(1.0, relevance)

            key = (name.lower(), role_text.lower())
            if key in seen:
                continue
            seen.add(key)

            candidates.append(
                Contact(
                    name=name,
                    role=role_text,
                    linkedin_url=linkedin_url,
                    email=email,
                    relevance_score=round(relevance, 4),
                )
            )

    candidates.sort(key=lambda c: c.relevance_score, reverse=True)
    return candidates[:8]


def compute_contact_score(contacts: list[Contact]) -> float:
    if not contacts:
        return 0.0

    best = contacts[0]
    score = 0.0
    score += 0.35 * best.relevance_score
    score += 0.25 if any(c.linkedin_url for c in contacts) else 0.0
    score += 0.25 if any(c.email for c in contacts) else 0.0
    score += min(0.15, 0.05 * len(contacts))
    return round(min(1.0, score), 4)
