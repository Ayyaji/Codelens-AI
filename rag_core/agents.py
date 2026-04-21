import os
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from ddgs import DDGS
from dotenv import load_dotenv

load_dotenv()

# Load shared resources
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API"))

def load_vectorstore():
    return Chroma(
        persist_directory="./codelens_kb",
        embedding_function=embeddings
    )

def debug_agent(query: str) -> str:
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    docs = retriever.invoke(query)
    context = "\n".join([doc.page_content for doc in docs])
    
    prompt = f"""You are CodeLens AI debug assistant for engineering students.
Use the context below to explain the error and how to fix it.
Be clear and beginner-friendly.

Context: {context}

Student Error: {query}

Explanation and Fix:"""
    
    return llm.invoke(prompt).content

def concept_agent(query: str) -> str:
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    docs = retriever.invoke(query)
    context = "\n".join([doc.page_content for doc in docs])
    
    prompt = f"""You are CodeLens AI concept teacher for engineering students.
Explain the concept clearly with a simple example.

Context: {context}

Student Question: {query}

Explanation:"""
    
    return llm.invoke(prompt).content

def hint_agent(query: str) -> str:
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    docs = retriever.invoke(query)
    context = "\n".join([doc.page_content for doc in docs])
    
    prompt = f"""You are CodeLens AI hint provider for engineering students.
Give ONLY a small hint — do not give the full answer or solution.
Make the student think and figure it out themselves.

Context: {context}

Student Request: {query}

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
                "raw_content": None
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
        
        llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API"))
        answer = llm.invoke(prompt).content
        
        return {
            "answer": answer,
            "source": source_url,
            "raw_content": context
        }
    
    except Exception as e:
        return {
            "answer": f"Web search failed: {str(e)}",
            "source": None,
            "raw_content": None
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