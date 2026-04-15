import re
from pydantic import BaseModel

from app.clients.tinyfish_client import TinyFishClient


def _clean_person_name(text: str) -> str | None:
    # Common Google title format: "Name - Role - Company | LinkedIn"
    head = re.split(r"\s[-|]\s", text.strip())[0]
    head = re.sub(r"\s*\(.*?\)\s*", " ", head).strip()
    if not head:
        return None
    if len(head.split()) < 2:
        return None
    if any(ch.isdigit() for ch in head):
        return None
    if len(head) > 80:
        return None
    return head


def _extract_role(title: str, snippet: str) -> str:
    source = title.strip() or snippet.strip()
    source = re.sub(r"\s+", " ", source)
    if len(source) > 160:
        source = source[:160].rstrip()
    return source


class ContactCandidate(BaseModel):
    name: str
    role: str
    company: str
    source_url: str | None = None


class ContactEngine:
    """High-precision contact discovery via TinyFish-powered web search."""

    def __init__(self, tinyfish_client: TinyFishClient | None = None) -> None:
        self.tinyfish = tinyfish_client or TinyFishClient()

    def build_queries(self, company: str, domain: str) -> list[str]:
        return [
            f'site:linkedin.com "{company}" "technical recruiter" Singapore',
            f'site:linkedin.com "{company}" "{domain} manager" Singapore',
            f'site:linkedin.com "{company}" "{domain} lead" Singapore',
        ]

    async def find_candidates(self, company: str, domain: str, limit_per_query: int = 5) -> list[ContactCandidate]:
        queries = self.build_queries(company=company, domain=domain)
        candidates: list[ContactCandidate] = []
        seen: set[tuple[str, str]] = set()

        for query in queries:
            results = await self.tinyfish.web_search(query=query, limit=limit_per_query)
            for result in results:
                title = (result.get("title") or "").strip()
                snippet = (result.get("snippet") or "").strip()
                url = (result.get("url") or "").strip()

                # Precision guardrails: keep only likely LinkedIn profile-like results.
                combined = f"{title} {snippet} {url}".lower()
                if "linkedin.com" not in combined:
                    continue
                if company.lower() not in combined:
                    continue

                name = _clean_person_name(title or snippet)
                if not name:
                    continue

                role = _extract_role(title=title, snippet=snippet)
                if len(role) < 5:
                    continue

                key = (name.lower(), role.lower())
                if key in seen:
                    continue
                seen.add(key)

                candidates.append(
                    ContactCandidate(
                        name=name,
                        role=role,
                        company=company,
                        source_url=url or None,
                    )
                )

        return candidates
