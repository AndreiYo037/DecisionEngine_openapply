import json
import socket
from io import BytesIO
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import AuthenticationError as OpenAIAuthenticationError
from pypdf import PdfReader

from app.config import settings
from app.models import (
    ActionableJob,
    ActionableMatchJobsResponse,
    ActionableOpportunity,
    MatchJobsRequest,
    MatchJobsResponse,
)
from app.services.pipeline import DecisionEngineService

app = FastAPI(
    title="DecisionEngine OpenApply",
    description="Internship decision engine that returns only jobs with high fit and high-confidence contacts.",
    version="1.0.0",
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

service = DecisionEngineService()


def _to_actionable_response(result: MatchJobsResponse) -> ActionableMatchJobsResponse:
    opportunities: list[ActionableOpportunity] = []
    for item in result.matched_jobs:
        if not item.contacts:
            continue
        opportunities.append(
            ActionableOpportunity(
                job=ActionableJob(
                    title=str(item.job.get("title", "")),
                    company=str(item.job.get("company", "")),
                    match_score=int(item.job.get("match_score", 0)),
                ),
                best_contact=item.contacts[0],
                alternate_contacts=item.contacts[1:3],
                message=item.outreach_message,
            )
        )
    return ActionableMatchJobsResponse(profile=result.profile, opportunities=opportunities)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text.strip())
    return "\n\n".join(pages).strip()


async def _run_service_or_raise(payload: MatchJobsRequest) -> MatchJobsResponse:
    try:
        return await service.run(
            cv_text=payload.cv_text or "",
            jobs=payload.jobs,
            include_ingestion=payload.include_ingestion,
            ingestion_sources=payload.ingestion_sources,
        )
    except OpenAIAuthenticationError as exc:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key is invalid. Update OPENAI_API_KEY in .env and retry.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="A required upstream API is unreachable right now. Please retry shortly.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unexpected server error while processing the request.",
        ) from exc


async def _run_service_with_debug_or_raise(payload: MatchJobsRequest) -> tuple[MatchJobsResponse, dict]:
    try:
        return await service.run_with_debug(
            cv_text=payload.cv_text or "",
            jobs=payload.jobs,
            include_ingestion=payload.include_ingestion,
            ingestion_sources=payload.ingestion_sources,
        )
    except OpenAIAuthenticationError as exc:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key is invalid. Update OPENAI_API_KEY in .env and retry.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="A required upstream API is unreachable right now. Please retry shortly.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unexpected server error while processing the request.",
        ) from exc


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
    tinyfish_dns_ok, tinyfish_dns_detail = _resolve_host(settings.tinyfish_base_url)
    tinyfish_url = f"{settings.tinyfish_base_url.rstrip('/')}/v1/search"
    tinyfish_http_ok, tinyfish_http_status, tinyfish_http_detail = await _probe_http(
        tinyfish_url,
        headers={"Authorization": f"Bearer {settings.tinyfish_api_key}"},
    )

    openai_base = "https://api.openai.com"
    openai_dns_ok, openai_dns_detail = _resolve_host(openai_base)
    openai_http_ok, openai_http_status, openai_http_detail = await _probe_http(
        f"{openai_base}/v1/models",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
    )

    return {
        "tinyfish": {
            "base_url": settings.tinyfish_base_url,
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


@app.post("/match_jobs", response_model=MatchJobsResponse)
async def match_jobs(payload: MatchJobsRequest) -> MatchJobsResponse:
    if not payload.cv_text:
        raise HTTPException(status_code=400, detail="cv_text is required.")
    return await _run_service_or_raise(payload)


@app.post("/match_jobs_actionable", response_model=ActionableMatchJobsResponse)
async def match_jobs_actionable(payload: MatchJobsRequest) -> ActionableMatchJobsResponse:
    if not payload.cv_text:
        raise HTTPException(status_code=400, detail="cv_text is required.")

    if payload.include_debug:
        result, debug = await _run_service_with_debug_or_raise(payload)
        response = _to_actionable_response(result)
        response.debug = debug
        return response

    result = await _run_service_or_raise(payload)

    return _to_actionable_response(result)


@app.post("/match_jobs_from_cv", response_model=ActionableMatchJobsResponse)
async def match_jobs_from_cv(
    cv_file: UploadFile = File(...),
    jobs_json: str = Form("[]"),
    include_ingestion: bool = Form(False),
    ingestion_sources_json: str = Form(
        '["greenhouse","lever","workday","mycareersfuture","company_career_pages"]'
    ),
) -> ActionableMatchJobsResponse:
    filename = (cv_file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="cv_file must be a PDF.")

    raw_bytes = await cv_file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="cv_file is empty.")

    try:
        cv_text = _extract_pdf_text(raw_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse PDF: {exc}") from exc

    if not cv_text:
        raise HTTPException(status_code=400, detail="No readable text found in PDF.")

    try:
        jobs = json.loads(jobs_json)
        ingestion_sources = json.loads(ingestion_sources_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON form field: {exc}") from exc

    payload = MatchJobsRequest(
        cv_text=cv_text,
        jobs=jobs,
        include_ingestion=include_ingestion,
        ingestion_sources=ingestion_sources,
    )

    if payload.include_debug:
        result, debug = await _run_service_with_debug_or_raise(payload)
        response = _to_actionable_response(result)
        response.debug = debug
        return response

    result = await _run_service_or_raise(payload)
    return _to_actionable_response(result)
