from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def get_answer(query: str) -> dict:
    # Load embeddings
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Load existing ChromaDB
    vectorstore = Chroma(
        persist_directory="./codelens_kb",
        embedding_function=embeddings
    )
    
    # Retrieve relevant chunks
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    docs = retriever.invoke(query)
    context = "\n".join([doc.page_content for doc in docs])
    
    # Build prompt
    prompt = f"""You are CodeLens AI, a helpful assistant for engineering students.
Use the following context to answer the student's question.
If the answer is not in the context, say "I don't know".

Context:
{context}

Student Question: {query}

Answer:"""
    
    # Get LLM response
    llm = OllamaLLM(model="llama3.2")
    answer = llm.invoke(prompt)
    
    return {
        "query": query,
        "answer": answer,
        "context_used": context
    }

# Test it
if __name__ == "__main__":
    result = get_answer("Why am I getting NameError in Python?")
    print("Question:", result["query"])
    print("\nAnswer:", result["answer"])
    print("\nContext used:", result["context_used"])