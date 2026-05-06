from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM ONCE at module level, not inside function
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API"))

def route_query(query: str) -> str:
    """
    Routes student query to the correct agent.
    Returns: "debug", "concept", "hint", or "web"
    """
    
    prompt = f"""You are a query router for CodeLens AI, a Python learning assistant.
Classify the student query into exactly one of these categories:

- debug: student has an error, exception, or bug in their code
- concept: student wants to understand a programming concept or topic
- hint: student explicitly asks for a hint or clue, not full answer
- web: query is outside Python/programming scope entirely

Respond with ONLY one word: debug, concept, hint, or web
No explanation. No punctuation. Just one word.

Student query: {query}

Category:"""

    response = llm.invoke(prompt).content.strip().lower()
    
    # Validate response
    valid_routes = ["debug", "concept", "hint", "web"]
    if response not in valid_routes:
        return "debug"  # default fallback
    
    return response


# Test it
if __name__ == "__main__":
    import time
    
    test_queries = [
        "I'm getting NameError: name 'x' is not defined",
        "What is recursion in Python?",
        "Give me a hint for fixing my IndexError",
        "What is the capital of France?"
    ]
    
    for query in test_queries:
        start = time.time()
        route = route_query(query)
        routing_time = round(time.time() - start, 2)
        print(f"Query: {query}")
        print(f"Route: {route} ({routing_time}s)\n")