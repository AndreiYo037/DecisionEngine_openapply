import socket
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.ingestion.manual_input import ingest_jobs_from_urls
from app.models import RankJobsRequest, RankedJobResult
from app.ranking.decision_engine import rank_jobs

app = FastAPI(
    title="DecisionEngine OpenApply",
    description="Decision engine that ranks manually provided job URLs by CV fit and reachable contacts.",
    version="2.0.0",
    docs_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


def _resolve_host(target_url: str) -> tuple[bool, str]:
    hostname = urlparse(target_url).hostname
    if not hostname:
        return False, "invalid_url"
    try:
        socket.gethostbyname(hostname)
        return True, "ok"
    except Exception as exc:
        return False, f"dns_error: {exc}"


async def _probe_http(target_url: str, *, headers: dict | None = None) -> tuple[bool, int | None, str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(target_url, headers=headers)
        return True, response.status_code, "ok"
    except Exception as exc:
        return False, None, str(exc)


@app.get("/diag/upstream")
async def diag_upstream() -> dict:
    tinyfish_url = settings.tinyfish_search_url
    if "api.tinyfish.ai" in tinyfish_url:
        tinyfish_url = "https://api.search.tinyfish.ai"
    tinyfish_dns_ok, tinyfish_dns_detail = _resolve_host(tinyfish_url)
    tinyfish_http_ok, tinyfish_http_status, tinyfish_http_detail = await _probe_http(
        tinyfish_url,
        headers={"X-API-Key": settings.tinyfish_api_key},
    )

    openai_base = "https://api.openai.com"
    openai_dns_ok, openai_dns_detail = _resolve_host(openai_base)
    openai_http_ok, openai_http_status, openai_http_detail = await _probe_http(
        f"{openai_base}/v1/models",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
    )

    return {
        "tinyfish": {
            "base_url": tinyfish_url,
            "dns_ok": tinyfish_dns_ok,
            "dns_detail": tinyfish_dns_detail,
            "http_ok": tinyfish_http_ok,
            "http_status": tinyfish_http_status,
            "http_detail": tinyfish_http_detail,
        },
        "openai": {
            "base_url": openai_base,
            "dns_ok": openai_dns_ok,
            "dns_detail": openai_dns_detail,
            "http_ok": openai_http_ok,
            "http_status": openai_http_status,
            "http_detail": openai_http_detail,
        },
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def home() -> HTMLResponse:
    return HTMLResponse(
        """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>DecisionEngine OpenApply</title>
          <style>
            body {
              font-family: Inter, Segoe UI, Arial, sans-serif;
              margin: 0;
              padding: 32px;
              background: #0b1020;
              color: #e6edf7;
            }
            .card {
              max-width: 780px;
              margin: 48px auto;
              padding: 28px;
              border-radius: 14px;
              background: linear-gradient(145deg, #121a33, #0d152b);
              border: 1px solid #2a3761;
              box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
            }
            h1 { margin-top: 0; font-size: 28px; }
            p { line-height: 1.6; color: #b8c4e1; }
            a.button {
              display: inline-block;
              margin-top: 12px;
              padding: 10px 16px;
              border-radius: 10px;
              text-decoration: none;
              font-weight: 600;
              color: #fff;
              background: #3b82f6;
            }
            a.button:hover { background: #2563eb; }
          </style>
        </head>
        <body>
          <main class="card">
            <h1>DecisionEngine OpenApply API</h1>
            <p>
              Internship decision engine that only returns jobs where the candidate
              has both strong fit and high-confidence contacts.
            </p>
            <a class="button" href="/docs">Open API Docs</a>
          </main>
        </body>
        </html>
        """
    )


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} Docs",
        swagger_css_url="/static/swagger-custom.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 1,
            "docExpansion": "list",
            "deepLinking": True,
            "displayRequestDuration": True,
            "filter": True,
            "tryItOutEnabled": True,
        },
    )


@app.post("/match_jobs", response_model=list[RankedJobResult])
async def match_jobs(payload: RankJobsRequest) -> list[RankedJobResult]:
    if not payload.job_urls:
        raise HTTPException(status_code=400, detail="job_urls is required.")

    try:
        jobs = ingest_jobs_from_urls(payload.job_urls)
        ranked = rank_jobs(job_list=jobs, user_profile=payload.user_profile, top_k=payload.top_k)
        return ranked
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach TinyFish API for manual URL ingestion/enrichment.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unexpected server error.") from exc
