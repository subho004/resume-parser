"""Groq-backed agents that analyze the resume and job description."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Iterable, List, TypedDict

from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class AgentExecutionError(RuntimeError):
    """Raised when a Groq powered agent cannot complete."""


_llm = ChatGroq(
    model_name=settings.groq_model,
    temperature=settings.groq_temperature,
    max_tokens=settings.groq_max_tokens,
)
_parser = StrOutputParser()

SUMMARY_SCHEMA_HINT = (
    "Respond strictly in JSON with keys 'summary' (string) and 'highlights' (array of short strings)."
)

SIMILARITY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a resume analysing agent. Compare the resume text versus the job description and call out the most impressive overlaps. "
            f"{SUMMARY_SCHEMA_HINT}",
        ),
        (
            "human",
            "Resume content:\n```\n{resume_excerpt}\n```\n"
            "Job description:\n```\n{job_description}\n```",
        ),
    ]
)

GAP_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a resume analyser. Point out the missing skills, experiences or signals that would make the resume a closer match for the job and what can be done better "
            f"{SUMMARY_SCHEMA_HINT}",
        ),
        (
            "human",
            "Resume content:\n```\n{resume_excerpt}\n```\n"
            "Job description:\n```\n{job_description}\n```",
        ),
    ]
)

COMPILATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are decision making agent based on resume details. The first agent provides strengths and similarities with the job description. The second agent provides gaps and missing elements. Highlight what is working and what should improve. "
            f"{SUMMARY_SCHEMA_HINT}",
        ),
        (
            "human",
            "Agent 1 says:\n```\n{agent_one_feedback}\n```\n"
            "Agent 2 says:\n```\n{agent_two_feedback}\n```",
        ),
    ]
)


@dataclass
class AgentOutput:
    """Internal representation of each agent's result."""

    name: str
    summary: str
    highlights: List[str]


def _truncate(text: str, limit: int = 4000) -> str:
    """Prevent prompts from exploding in size."""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...\n[truncated]"


def _extract_json_blob(text: str) -> str:
    """Best-effort to locate a JSON dictionary within the model output."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def _invoke(prompt: ChatPromptTemplate, agent_label: str, **kwargs) -> str:
    chain = prompt | _llm | _parser

    try:
        return chain.invoke(kwargs)
    except Exception as exc:  # pragma: no cover - network issues cannot be tested
        logger.exception("Groq agent call failed for %s", agent_label)
        raise AgentExecutionError(f"{agent_label} could not complete due to an upstream Groq error.") from exc


def _parse_agent_payload(raw: str, agent_name: str) -> AgentOutput:
    try:
        payload = json.loads(_extract_json_blob(raw))
    except json.JSONDecodeError:
        payload = {"summary": raw.strip(), "highlights": []}

    summary = str(payload.get("summary") or "").strip()
    highlights = payload.get("highlights") or []
    if not isinstance(highlights, list):
        highlights = [str(highlights)]

    highlights = [str(item).strip() for item in highlights if str(item).strip()]

    if not summary:
        summary = "No summary returned by the LLM."

    return AgentOutput(name=agent_name, summary=summary, highlights=highlights[:8])


def agent_one(resume_text: str, job_text: str) -> AgentOutput:
    """Groq-backed similarity agent."""
    raw = _invoke(
        SIMILARITY_PROMPT,
        agent_label="Agent 1 (similarity & strengths)",
        resume_excerpt=_truncate(resume_text),
        job_description=_truncate(job_text),
    )
    return _parse_agent_payload(raw, "Similarity & strengths agent")

def agent_two(resume_text: str, job_text: str) -> AgentOutput:
    """Groq-backed gaps agent."""
    raw = _invoke(
        GAP_PROMPT,
        agent_label="Agent 2 (gap analysis)",
        resume_excerpt=_truncate(resume_text),
        job_description=_truncate(job_text),
    )
    return _parse_agent_payload(raw, "Gap analysis agent")


def agent_three(outputs: Iterable[AgentOutput]) -> AgentOutput:
    """Aggregate upstream agent feedback using Groq."""
    output_list = list(outputs)
    strengths_block = ""
    if output_list:
        strengths_block = "\n".join(
            [output_list[0].summary, *output_list[0].highlights]
        )

    gaps_block = ""
    if len(output_list) > 1:
        gaps_block = "\n".join(
            [output_list[1].summary, *output_list[1].highlights]
        )

    raw = _invoke(
        COMPILATION_PROMPT,
        agent_label="Agent 3 (compilation)",
        agent_one_feedback=strengths_block or "Agent 1 did not produce feedback.",
        agent_two_feedback=gaps_block or "Agent 2 did not produce feedback.",
    )
    return _parse_agent_payload(raw, "Compilation agent")


class AgentGraphState(TypedDict, total=False):
    """LangGraph state shared by nodes."""

    resume_text: str
    job_description: str
    agent_one_result: AgentOutput
    agent_two_result: AgentOutput
    agent_three_result: AgentOutput


def similarity_node(state: AgentGraphState) -> AgentGraphState:
    result = agent_one(state["resume_text"], state["job_description"])
    return {"agent_one_result": result}


def gap_node(state: AgentGraphState) -> AgentGraphState:
    result = agent_two(state["resume_text"], state["job_description"])
    return {"agent_two_result": result}


def compilation_node(state: AgentGraphState) -> AgentGraphState:
    outputs = [
        state["agent_one_result"],
        state["agent_two_result"],
    ]
    compiled = agent_three(outputs)
    return {"agent_three_result": compiled}


def _build_workflow() -> StateGraph:
    graph = StateGraph(AgentGraphState)
    graph.add_node("similarity", similarity_node)
    graph.add_node("gaps", gap_node)
    graph.add_node("compile", compilation_node)

    graph.add_edge(START, "similarity")
    graph.add_edge("similarity", "gaps")
    graph.add_edge("gaps", "compile")
    graph.add_edge("compile", END)
    return graph.compile()


_agent_graph = _build_workflow()


def run_agent_workflow(resume_text: str, job_text: str) -> List[AgentOutput]:
    """Execute the LangGraph-defined agent workflow."""
    final_state: AgentGraphState = _agent_graph.invoke(
        {"resume_text": resume_text, "job_description": job_text}
    )
    return [
        final_state["agent_one_result"],
        final_state["agent_two_result"],
        final_state["agent_three_result"],
    ]
