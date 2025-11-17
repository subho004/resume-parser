"""FastAPI application exposing the resume analysis workflow."""

from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .agents import AgentExecutionError, AgentOutput, run_agent_workflow
from .models import AgentResult, AnalysisResponse, HealthResponse
from .pdf_parser import ResumeParsingError, resume_parser

ALLOWED_RESUME_TYPES = {"application/pdf"}

app = FastAPI(
    title="Resume vs JD Analyzer",
    version="0.1.0",
    description="Uploads a resume PDF and compares it to a job description via a simple multi-agent pipeline.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    """Lightweight readiness probe."""
    return HealthResponse(status="ok", detail="Resume analyzer is running.")


def _as_agent_result(output: AgentOutput) -> AgentResult:
    return AgentResult(name=output.name, summary=output.summary, highlights=output.highlights)


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    job_description: str = Form(..., description="Plain text job requirements."),
    resume: UploadFile = File(..., description="PDF resume upload."),
) -> AnalysisResponse:
    if resume.content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported resume content type {resume.content_type}. Only PDF files are accepted.",
        )
    print(f"[analyze_resume] Received resume file: {resume.filename} of type {resume.content_type}.")
    resume_bytes = await resume.read()
    try:
        print("[analyze_resume] Starting PDF resume parsing.")
        resume_text = resume_parser.convert_pdf_bytes(resume_bytes, file_name=resume.filename)

    except ResumeParsingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        agent_outputs = run_agent_workflow(resume_text, job_description)
    except AgentExecutionError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return AnalysisResponse(
        resume_character_count=len(resume_text),
        job_description_character_count=len(job_description),
        agent_results=[_as_agent_result(output) for output in agent_outputs],
        combined_summary=agent_outputs[-1].summary,
        resume_excerpt=resume_text[:500],
    )
