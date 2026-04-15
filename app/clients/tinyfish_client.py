from typing import Any

import httpx

from app.config import settings


class TinyFishClient:
    def __init__(self) -> None:
        self.base_url = settings.tinyfish_base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {settings.tinyfish_api_key}"}

    async def scrape_jobs(self, source: str, location: str = "Singapore") -> list[dict[str, Any]]:
        payload = {"source": source, "location": location}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/v1/scrape/jobs",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data.get("jobs", [])

    async def web_search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        payload = {"query": query, "limit": limit}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/v1/search",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data.get("results", [])
