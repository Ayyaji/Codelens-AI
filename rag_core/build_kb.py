from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Step 1: Load knowledge base file

print("Loading knowledge base...")
loader = TextLoader("knowledge_base/python_error.txt", encoding="utf-8")
documents = loader.load()
print(f"Loaded {len(documents)} document(s)")

# Step 2: Split into chunks
print("Splitting into chunks...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20
)
chunks = splitter.split_documents(documents)
print(f"Created {len(chunks)} chunks")

# Step 3: Create embeddings
print("Loading embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Step 4: Store in ChromaDB
print("Storing in ChromaDB...")
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./codelens_kb"
)

print(f"✅ Knowledge base built successfully!")
print(f"Total chunks stored: {len(chunks)}")





# Step 5: Test retrieval
print("\nTesting retrieval...")
query = "why am I getting NameError?"
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
results = retriever.invoke(query)

for i, doc in enumerate(results):
    print(f"\nResult {i+1}:")
    print(doc.page_content)