"""Build the local knowledge base used when a student asks for debugging help."""

from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_core.agents.retrieval import get_embeddings
from rag_core.config import KNOWLEDGE_FILE, get_kb_dir


def build() -> None:
    print(f"Loading {KNOWLEDGE_FILE}...")
    documents = TextLoader(str(KNOWLEDGE_FILE), encoding="utf-8").load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(documents)
    print(f"Storing {len(chunks)} chunks...")
    embeddings = get_embeddings()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=get_kb_dir(),
    )
    print(f"Knowledge base ready at {get_kb_dir()}")
    sample = vectorstore.as_retriever(search_kwargs={"k": 1}).invoke("why am I getting NameError?")
    if sample:
        print(sample[0].page_content[:200])


if __name__ == "__main__":
    build()
