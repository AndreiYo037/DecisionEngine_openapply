from typing import Any
import re

import httpx

from app.config import settings


class TinyFishClient:
    def __init__(self) -> None:
        configured_search_url = settings.tinyfish_search_url.rstrip("/")
        # Backward-compatible fallback if old hostname is still configured.
        if "api.tinyfish.ai" in configured_search_url:
            configured_search_url = "https://api.search.tinyfish.ai"
        self.search_url = configured_search_url
        self.headers = {"X-API-Key": settings.tinyfish_api_key}

    @staticmethod
    def _extract_company(title: str) -> str:
        # Common SERP title patterns:
        # "Data Intern - Company", "Company Careers | ...", "Role at Company"
        cleaned = title.strip()
        for splitter in (" - ", " | ", " at "):
            parts = cleaned.split(splitter)
            if len(parts) > 1:
                candidate = parts[-1].strip()
                if candidate:
                    return candidate[:80]
        words = re.findall(r"[A-Za-z0-9&.]+", cleaned)
        if not words:
            return "Unknown Company"
        return " ".join(words[-2:])[:80]

    async def scrape_jobs(self, source: str, location: str = "Singapore") -> list[dict[str, Any]]:
        source_queries = {
            "greenhouse": f"site:boards.greenhouse.io intern {location}",
            "lever": f"site:jobs.lever.co intern {location}",
            "workday": f"site:myworkdayjobs.com intern {location}",
            "mycareersfuture": f"site:mycareersfuture.gov.sg internship {location}",
            "company_career_pages": f"internship careers {location}",
        }
        query = source_queries.get(source, f"internship jobs {location}")
        results = await self.web_search(query=query, limit=10)
        jobs: list[dict[str, Any]] = []
        for item in results:
            title = (item.get("title") or "").strip()
            snippet = (item.get("snippet") or "").strip()
            if not title:
                continue
            jobs.append(
                {
                    "title": title[:140],
                    "company": self._extract_company(title),
                    "description": snippet or title,
                    "location": location,
                    "url": item.get("url"),
                }
            )
        return jobs

    async def web_search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                self.search_url,
                headers=self.headers,
                params={"query": query},
            )
            response.raise_for_status()
            data = response.json()
        return (data.get("results", []) or [])[:limit]
