"""Explain a concept the student needs for the role they are preparing for."""

from rag_core.agents.prompts import DIRECTIVE_INSTRUCTIONS, TUTOR_ROLE
from rag_core.agents.retrieval import get_context
from rag_core.llm import complete_text
from rag_core.timing import log_latency


def concept_agent(query: str, directive: str = "full") -> str:
    with log_latency("concept"):
        context = get_context(query)
        instruction = DIRECTIVE_INSTRUCTIONS.get(directive, DIRECTIVE_INSTRUCTIONS["full"])
        prompt = f"""{TUTOR_ROLE}
Explain the concept clearly, with one short example the student could mention in an interview.
Response style: {instruction}

Knowledge base:
{context}

Student: {query}

Explanation:"""
        return complete_text("large", prompt)
