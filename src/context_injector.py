import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = "evaluation/student_chromadb"

def get_persona_context(student_id: str, question: str) -> str:
    """Fetch relevant persona context for a student from their ChromaDB."""
    if not student_id:
        return ""
    
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        ef = embedding_functions.DefaultEmbeddingFunction()
        
        collection = chroma_client.get_collection(
            name=f"student_{student_id}",
            embedding_function=ef
        )
        
        results = collection.query(query_texts=[question], n_results=3)
        docs = results["documents"][0]
        
        context = "\n".join(docs)
        return f"[Student History]\n{context}"
    
    except Exception as e:
        return ""


if __name__ == "__main__":
    # Test
    result = get_persona_context("S001", "Why am I getting a NameError?")
    print(result)