"""A short hint, so the student can keep working the problem themselves."""

from rag_core.agents.prompts import DIRECTIVE_INSTRUCTIONS, TUTOR_ROLE
from rag_core.agents.retrieval import get_context
from rag_core.llm import complete_text
from rag_core.timing import log_latency


def hint_agent(query: str, directive: str = "full") -> str:
    with log_latency("hint"):
        context = get_context(query)
        instruction = DIRECTIVE_INSTRUCTIONS.get(directive, DIRECTIVE_INSTRUCTIONS["hint"])
        prompt = f"""{TUTOR_ROLE}
Give ONLY a small hint. Do not give the full answer or a working solution.
Response style: {instruction}

Knowledge base:
{context}

Student: {query}

Hint (one or two sentences):"""
        return complete_text("large", prompt)
