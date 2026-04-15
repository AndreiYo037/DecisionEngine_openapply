from fastapi import FastAPI, HTTPException

from app.models import MatchJobsRequest, MatchJobsResponse
from app.services.pipeline import DecisionEngineService

app = FastAPI(
    title="DecisionEngine OpenApply",
    description="Internship decision engine that returns only jobs with high fit and high-confidence contacts.",
    version="1.0.0",
)

service = DecisionEngineService()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/match_jobs", response_model=MatchJobsResponse)
async def match_jobs(payload: MatchJobsRequest) -> MatchJobsResponse:
    if not payload.cv_text:
        raise HTTPException(status_code=400, detail="cv_text is required.")

    return await service.run(
        cv_text=payload.cv_text,
        jobs=payload.jobs,
        include_ingestion=payload.include_ingestion,
        ingestion_sources=payload.ingestion_sources,
    )
