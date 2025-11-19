from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

groq_client = ChatGroq(model="llama-3.1-8b-instant", api_key=api_key)

agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant that extracts key information from web page content."),
        ("user", "Extract key information from the following web page content:\n\n{text}"),
    ]
)


async def web_agent(text: str) -> str:
    """Summarize or extract key details from raw page text."""
    chain = agent_prompt | groq_client
    result = await chain.ainvoke({"text": text})
    return result.content
