"""Search the web when a question is outside the knowledge base.

Results are summarised for the student and returned raw so the caller can
stage them for teacher approval before they enter the knowledge base.
"""

import logging

from rag_core.agents.prompts import TUTOR_ROLE
from rag_core.llm import complete_text
from rag_core.timing import log_latency

logger = logging.getLogger("codelens.agents")


def web_agent(query: str) -> dict:
    with log_latency("web"):
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
        except Exception as exc:
            logger.warning("web search failed: %s", exc)
            return {
                "answer": f"Web search failed: {exc}",
                "source": None,
                "raw_content": None,
            }

        if not results:
            return {
                "answer": "I could not find relevant information online.",
                "source": None,
                "raw_content": None,
            }

        source_url = results[0].get("href")
        context = "\n".join(
            f"{item.get('title', '')}: {item.get('body', '')}" for item in results
        )
        prompt = f"""{TUTOR_ROLE}
Using only the search results below, answer the student clearly and briefly.

Search results:
{context}

Student: {query}

Answer:"""
        answer = complete_text("large", prompt)
        return {"answer": answer, "source": source_url, "raw_content": context}
