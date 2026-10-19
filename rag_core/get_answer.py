"""Single-shot retrieval helper for a guidance question.

The live path is the multi-agent pipeline. This function is the earlier
retrieve-then-answer shape, now on the shared Groq client.
"""

from rag_core.agents.retrieval import get_context
from rag_core.llm import complete_text


def get_answer(query: str) -> dict:
    context = get_context(query)
    prompt = f"""You are CodeLens AI, an interview-readiness tutor.
Use the context below to answer. If the context does not contain the answer, say you do not know.
Debugging questions are part of interview practice.

Context:
{context}

Student: {query}

Answer:"""
    answer = complete_text("large", prompt)
    return {"query": query, "answer": answer, "context_used": context}


if __name__ == "__main__":
    result = get_answer("Why am I getting NameError in Python?")
    print(result["answer"])
