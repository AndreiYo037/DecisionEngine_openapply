# DecisionEngine OpenApply Backend

FastAPI backend for internship matching that only returns jobs when both conditions are true:

1. Candidate-job match score is high (`>= 70`)
2. High-confidence, relevant contacts exist (`>= 75`)

This enforces the product principle:
"Only show me jobs where I both qualify and have a way in."

## Stack

- FastAPI (Python)
- TinyFish API (job ingestion + indexed web search parsing)
- OpenAI API (CV parsing, job matching, intent extraction, outreach generation)

## API

### `POST /match_jobs`

Input JSON:

```json
{
  "cv_text": "Full text from the candidate CV",
  "jobs": [
    {
      "title": "Data Analyst Intern",
      "company": "Example Corp",
      "description": "Looking for SQL and Python...",
      "location": "Singapore"
    }
  ],
  "include_ingestion": false,
  "ingestion_sources": ["greenhouse", "lever", "workday", "mycareersfuture", "company_career_pages"]
}
```

Output JSON:

```json
{
  "profile": {
    "skills": ["Python", "SQL"],
    "domains": ["data"],
    "experience_level": "intern",
    "interests": ["analytics"],
    "projects": ["forecasting project"]
  },
  "matched_jobs": [
    {
      "job": {
        "title": "Data Analyst Intern",
        "company": "Example Corp",
        "match_score": 82
      },
      "contacts": [
        {
          "name": "Jane Lim",
          "role": "Technical Recruiter - Example Corp",
          "company": "Example Corp",
          "score": 91.5,
          "reason": "technical recruiter with strong relevance to data.",
          "source_url": "https://linkedin.com/in/..."
        }
      ],
      "outreach_message": "Hi Jane, I am a ... "
    }
  ]
}
```

## Contact Scoring Formula

`TOTAL_SCORE = 0.40 * HiringAuthority + 0.20 * RoleRelevance + 0.15 * TeamMatch + 0.15 * ResponseLikelihood + 0.10 * Accessibility`

Hard filters applied:

- Company mismatch -> reject
- Role irrelevant -> reject
- Contact score `< 75` -> reject
- If no remaining contact for a job -> drop job

## Setup

1. Create virtual environment and install dependencies:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
2. Copy env file:
   - `copy .env.example .env`
3. Configure:
   - `OPENAI_API_KEY`
   - `TINYFISH_API_KEY`
   - optional model/threshold values
4. Run server:
   - `uvicorn app.main:app --reload --port 8000`

## Constraints Implemented

- No direct LinkedIn scraping logic
- No fake emails generation
- Precision-first filtering with strict score thresholds
- Uncertain/low-confidence contacts are discarded
