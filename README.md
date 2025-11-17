# Resume vs JD Analyzer

FastAPI service that ingests a resume PDF, parses it with [MarkItDown](https://github.com/microsoft/markitdown), and runs a three-step Groq-powered LangGraph workflow:

1. **Similarity agent** – highlights skills/phrases shared between the resume and JD.
2. **Gap agent** – describes what’s missing from the resume.
3. **Compilation agent** – summarizes the first two agents for quick sharing.

The API returns each agent’s highlights plus the compiled summary.

## Getting started

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Provide Groq credentials via `.env` (copy `.env.sample`):

```bash
cp .env.sample .env
```

Edit `.env` with your `GROQ_API_KEY` and optional tuning (`GROQ_MODEL`, `GROQ_TEMPERATURE`, `GROQ_MAX_TOKENS`).

## Running the API

```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/health`

### Analyze endpoint

`POST /analyze` accepts a multipart form with:

- `job_description` (string)
- `resume` (PDF file upload)

Example (assuming a file named `resume.pdf` in the repo root):

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "job_description=Looking for a senior Python engineer experienced with FastAPI and Groq." \
  -F "resume=@resume.pdf;type=application/pdf"
```

The JSON response includes character counts, every agent’s summary/highlights, and Agent 3’s combined summary.

## Development notes

- Resume parsing happens in `app/pdf_parser.py`; logs prefixed with `[ResumeParser]` help debug parsing issues.
- LLM/agent configuration lives in `app/agents.py`, with prompts and the LangGraph pipeline.
- Adjust dependencies in `requirements.txt` as needed; FastAPI + Uvicorn run the API server.
