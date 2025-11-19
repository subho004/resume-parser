# Resume vs JD Analyzer

FastAPI service that compares a PDF resume against a job description using MarkItDown for parsing and a Groq-powered LangGraph workflow. It also exposes a helper endpoint to summarize any public web page.

## Features

- Resume parsing with [MarkItDown](https://github.com/microsoft/markitdown) to convert PDFs into markdown/text without shelling out to external binaries.
- Three Groq-backed agents (similarity, gap, compilation) orchestrated by LangGraph (`app/agents.py`) to surface overlaps, gaps, and an overall takeaway.
- `/analyze` endpoint validates uploads (PDF-only, 10 MB max), emits per-agent highlights, and includes a resume excerpt for debugging.
- `/website-summary` endpoint fetches arbitrary URLs, extracts the readable text with MarkItDown, and summarizes them with Groq (`app/webagent.py`).
- Simple `/health` probe for readiness and full CORS support so frontends can call it directly.

## Prerequisites

- Python 3.10+ (tested with 3.11) and `pip`
- Groq API key with access to the referenced model

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.sample .env
```

Edit `.env` with your Groq token and (optionally) override model parameters.

## Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `GROQ_API_KEY` | Required Groq token used by both the resume agents and the website summarizer | — |
| `GROQ_MODEL` | Model slug sent to `langchain_groq.ChatGroq` | `llama-3.1-8b-instant` |
| `GROQ_TEMPERATURE` | Sampling temp for all agents | `0.2` |
| `GROQ_MAX_TOKENS` | Hard cap per agent response | `800` |

`app/config.py` loads the variables via `pydantic-settings` and keeps them cached for subsequent requests.

## Run the API

```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

The app starts on `http://localhost:8000` by default. Interactive docs will be available at `/docs`.

## API Endpoints

### `GET /health`

Returns a simple `{ "status": "ok" }` payload so Cloud Run/containers can perform liveness checks.

### `POST /analyze`

Multipart form fields:

- `job_description` – plain text
- `resume` – PDF file (`application/pdf`, ≤ 10 MB)

Example:

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F 'job_description=Senior Python engineer with FastAPI and Groq experience.' \
  -F 'resume=@resume.pdf;type=application/pdf'
```

Response:

- Character counts for resume + JD
- Three `agent_results` entries (similarities, gaps, compiled takeaways) with summaries and highlight bullets
- `combined_summary` (Agent 3)
- `resume_excerpt` (first 500 chars) to inspect parsing quality

### `POST /website-summary`

Form field:

- `website_url` – Fully qualified URL to summarize

```bash
curl -X POST "http://localhost:8000/website-summary" \
  -F "website_url=https://groq.com/blog"
```

Response contains the canonicalized URL, extracted text, and a Groq-generated summary.

## Implementation Notes

- PDF parsing lives in `app/pdf_parser.py`; noisy logs prefixed with `[ResumeParser]` make it easier to trace parsing issues.
- LangGraph workflow definitions and Groq prompts are in `app/agents.py`; adjust prompts or agent order there.
- The MarkItDown-backed website scraper is in `app/website_parser.py`, while the summarization prompt sits in `app/webagent.py`.
- FastAPI routes are defined in `app/main.py`; tweak middleware, validation rules, or response models there.
