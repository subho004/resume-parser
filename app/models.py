"""Pydantic models shared across the FastAPI app."""

from typing import List, Optional, TypedDict

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Represents the output of a single agent in the workflow."""

    name: str
    summary: str
    highlights: List[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    """Response payload for the resume analysis endpoint."""

    resume_character_count: int
    job_description_character_count: int
    agent_results: List[AgentResult]
    combined_summary: str
    resume_excerpt: Optional[str] = Field(
        default=None,
        description="First slice of the parsed resume text to help with debugging.",
    )


class HealthResponse(BaseModel):
    """Response payload for the health endpoint."""

    status: str
    detail: str

class GraphState(TypedDict):
    resume:str
    jd:str
    agent1_output: dict | None
    agent2_output: dict | None
    agent3_output: dict | None