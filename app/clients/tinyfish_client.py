import re
from typing import Any

import httpx

from app.config import settings


class TinyFishClient:
    def __init__(self) -> None:
        self.search_url = settings.tinyfish_search_url.rstrip("/")
        self.fetch_api_url = settings.tinyfish_fetch_url.rstrip("/")
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

    def web_search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        with httpx.Client(timeout=30) as client:
            response = client.get(
                self.search_url,
                headers=self.headers,
                params={"query": query},
            )
            response.raise_for_status()
            data = response.json()
        return (data.get("results", []) or [])[:limit]

    def fetch_url(self, url: str) -> dict[str, Any]:
        with httpx.Client(timeout=45) as client:
            response = client.post(
                self.fetch_api_url,
                headers=self.headers,
                json={"url": url, "format": "markdown"},
            )
            response.raise_for_status()
            data = response.json()
        return data
