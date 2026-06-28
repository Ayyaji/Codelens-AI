import os

from ddgs import DDGS
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# Load shared resources ONCE at module level
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API"))
DIRECTIVE_INSTRUCTIONS = {
    "full": "the instruction is just the normal complete-explanation behavior. ",
    "hint": "the instruction says to give only a small hint, not a full answer, because the student has hit this error before",
    "gentle": " the instruction says to briefly reference that the student covered this topic recently before explaining.",
    "break": "he instruction says to give the full answer but explicitly suggest a short break, since this is the 4th+ time on the same error",
}


def load_vectorstore():
    return Chroma(persist_directory="./codelens_kb", embedding_function=embeddings)


def get_context(query, directive):
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    docs = retriever.invoke(query)
    return "\n".join([doc.page_content for doc in docs])


def debug_agent(query: str, directive: str = "full") -> str:
    context = get_context(query, directive)
    instruction = DIRECTIVE_INSTRUCTIONS.get(directive, DIRECTIVE_INSTRUCTIONS["full"])

    prompt = f"""You are CodeLens AI debug assistant for engineering students.
        Use the context below to explain the error and how to fix it.
        Be clear and beginner-friendly.
        Response style for this student right now: {instruction}
        Context: {context}
        Student Error: {query}
        Explanation and Fix:"""
    return llm.invoke(prompt).content


def concept_agent(query: str, directive: str = "full") -> str:
    context = get_context(query, directive)
    instruction = DIRECTIVE_INSTRUCTIONS.get(directive, DIRECTIVE_INSTRUCTIONS["full"])

    prompt = f"""You are CodeLens AI concept teacher for engineering students.
    Explain the concept clearly with a simple example.

    Response style for this student right now: {instruction}

    Context: {context}

    Student Question: {query}

    Explanation:"""

    return llm.invoke(prompt).content


def hint_agent(query: str, directive: str = "full") -> str:
    context = get_context(query, directive)
    instruction = DIRECTIVE_INSTRUCTIONS.get(directive, DIRECTIVE_INSTRUCTIONS["full"])
    prompt = f"""You are CodeLens AI hint provider for engineering students.
Give ONLY a small hint — do not give the full answer or solution.
Make the student think and figure it out themselves.

Context: {context}

Student Request: {query}
Response style for this student right now: {instruction}
Hint (one or two sentences only):"""

    return llm.invoke(prompt).content


def web_agent(query: str) -> dict:
    """
    Searches the web for answers outside KB.
    Returns answer + source URL + raw content for KB staging.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))

        if not results:
            return {
                "answer": "I could not find relevant information online.",
                "source": None,
                "raw_content": None,
            }

        # Build context from search results
        context = ""
        source_url = results[0]["href"]
        for r in results:
            context += f"{r['title']}: {r['body']}\n"

        # LLM summarises search results
        prompt = f"""You are CodeLens AI assistant for engineering students.
Based on the following web search results, answer the student's question clearly.

Search Results:
{context}

Student Question: {query}

Answer:"""

        answer = llm.invoke(prompt).content

        return {"answer": answer, "source": source_url, "raw_content": context}

    except Exception as e:
        return {
            "answer": f"Web search failed: {str(e)}",
            "source": None,
            "raw_content": None,
        }


# Test all agents
if __name__ == "__main__":
    print("=== DEBUG AGENT ===")
    print(debug_agent("I'm getting NameError: name 'x' is not defined"))

    print("\n=== CONCEPT AGENT ===")
    print(concept_agent("What is recursion in Python?"))

    print("\n=== HINT AGENT ===")
    print(hint_agent("Give me a hint for fixing IndexError"))

    print("\n=== WEB AGENT ===")
    print(web_agent("What is the capital of France?"))
