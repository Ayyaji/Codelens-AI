from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings

# Test LLM
llm = OllamaLLM(model="llama3.2")
response = llm.invoke("What is a NameError in Python? Answer in one sentence.")
print("LLM:", response)

# Test Embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector = embeddings.embed_query("NameError in Python")
print("Embedding length:", len(vector))
print("First 5 values:", vector[:5])
print("Embedding length:", len(vector))