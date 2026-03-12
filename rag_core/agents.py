from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma # type: ignore

# Load shared resources
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
llm = OllamaLLM(model="llama3.2")

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
    
    return llm.invoke(prompt)

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
    
    return llm.invoke(prompt)

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
    
    return llm.invoke(prompt)

def web_agent(query: str) -> str:
    prompt = f"""You are CodeLens AI assistant.
The student asked something outside the Python knowledge base.
Answer helpfully but briefly. If it's completely off-topic, 
politely redirect them back to programming topics.

Student Query: {query}

Response:"""
    
    return llm.invoke(prompt)


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