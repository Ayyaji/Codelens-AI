"""Explain a bug the student hit while practising for an interview."""

from rag_core.agents.prompts import DIRECTIVE_INSTRUCTIONS, TUTOR_ROLE
from rag_core.agents.retrieval import get_context
from rag_core.llm import complete_text
from rag_core.timing import log_latency


def debug_agent(query: str, directive: str = "full") -> str:
    with log_latency("debug"):
        context = get_context(query)
        instruction = DIRECTIVE_INSTRUCTIONS.get(directive, DIRECTIVE_INSTRUCTIONS["full"])
        prompt = f"""{TUTOR_ROLE}
The student is debugging code. Explain the error and how to fix it.
Response style: {instruction}

Knowledge base:
{context}

Student: {query}

Explanation and fix:"""
        return complete_text("large", prompt)
