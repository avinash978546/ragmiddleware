import os
import argparse
from dotenv import load_dotenv

from src.ingestion.loader import load_directory
from src.ingestion.chunker import chunk_documents
from src.retrieval.embedder import BGEEmbedder
from src.retrieval.vector_store import QdrantStore, DEFAULT_COLLECTION
from src.retrieval.retriever import Retriever
from src.generation.llm_client import OllamaClient
from src.middleware.pre_generation import PreGenerationMiddleware, PromptInjectionException

# Load configurations
load_dotenv()


def run_pipeline(query: str, force_reingest: bool = False, raw_docs_dir: str = "data/raw_docs", limit: int = 5):
    """Orchestrates ingestion, retrieval, and generation steps."""
    print("=" * 60)
    print("RAG-GUARD PIPELINE (Milestone 3 - Pre-Gen Guardrails)")
    print("=" * 60)

    # 1. Initialize core clients and models
    print("\n[1/4] Initializing local models, storage, and safety guardrails...")
    embedder = BGEEmbedder()
    vector_store = QdrantStore()
    llm_client = OllamaClient()
    pre_gen_middleware = PreGenerationMiddleware()

    # 2. Check if ingestion is needed
    vector_store.init_collection(DEFAULT_COLLECTION)
    existing_count = vector_store.get_collection_count(DEFAULT_COLLECTION)
    
    if existing_count == 0 or force_reingest:
        if force_reingest:
            print("\n[2/4] Force-reingest enabled. Re-creating collection...")
            vector_store.delete_collection(DEFAULT_COLLECTION)
            vector_store.init_collection(DEFAULT_COLLECTION)

        print(f"\n[2/4] Ingesting documents from '{raw_docs_dir}'...")
        documents = load_directory(raw_docs_dir)
        if not documents:
            print(f"Warning: No documents found in '{raw_docs_dir}'. Please add some .txt or .pdf files.")
            print("Creating a default welcome document to proceed...")
            os.makedirs(raw_docs_dir, exist_ok=True)
            default_path = os.path.join(raw_docs_dir, "welcome.txt")
            with open(default_path, "w", encoding="utf-8") as f:
                f.write("Welcome to RAG-Guard! This is a default fallback document for Milestone 1 evaluation.")
            documents = load_directory(raw_docs_dir)

        print(f"Loaded {len(documents)} raw document(s).")
        chunks = chunk_documents(documents)
        print(f"Split documents into {len(chunks)} chunks.")

        print("Generating embeddings for chunks...")
        chunk_texts = [c.page_content for c in chunks]
        embeddings = embedder.embed_documents(chunk_texts)

        vector_store.upsert_chunks(chunks, embeddings)
        print("Ingestion complete.")
    else:
        print(f"\n[2/4] Skipping ingestion. Vector store contains {existing_count} existing chunks.")

    # 3. Retrieval & Middleware Sanitization
    print(f"\n[3/4] Retrieving context for query: '{query}'...")
    retriever = Retriever(embedder, vector_store)
    retrieved_chunks = retriever.retrieve(query, limit=limit)
    
    print(f"Retrieved {len(retrieved_chunks)} raw chunks. Running safety checkpoints...")
    try:
        retrieved_chunks = pre_gen_middleware.process_chunks(retrieved_chunks)
    except PromptInjectionException as pie:
        print("\n" + "=" * 60)
        print("SECURITY EXCEPTION DETECTED:")
        print("=" * 60)
        print(str(pie))
        print("=" * 60)
        return

    print(f"\nPassed security check. {len(retrieved_chunks)} chunks in final context:")
    for idx, chunk in enumerate(retrieved_chunks):
        source = os.path.basename(chunk.metadata.get("source", "unknown"))
        print(f"\n--- Chunk {idx + 1} (Source: {source}, Index: {chunk.metadata.get('chunk_index', 0)}) ---")
        print(chunk.page_content.strip())
    print("-" * 60)

    # 4. Generation
    if not retrieved_chunks:
        print("\n[4/4] Sending query and context to Ollama LLM...")
        print("Warning: All chunks were stripped by security policy. Sending empty context.")
    else:
        print("\n[4/4] Sending query and context to Ollama LLM...")
        
    context_texts = [c.page_content for c in retrieved_chunks]
    
    try:
        answer = llm_client.generate_rag_answer(query, context_texts)
        print("\n" + "=" * 60)
        print("GENERATED ANSWER:")
        print("=" * 60)
        print(answer)
        print("=" * 60)
    except ConnectionError as ce:
        print(f"\nConnection Error: {ce}")
    except Exception as e:
        print(f"\nGeneration Error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG-Guard Milestone 1 base pipeline.")
    parser.add_argument(
        "--query", 
        type=str, 
        default="What are the key components of RAG-Guard?",
        help="Query to run through the RAG pipeline."
    )
    parser.add_argument(
        "--force-reingest", 
        action="store_true",
        help="Force re-ingest documents from data/raw_docs/ even if database already has chunks."
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=5,
        help="Top-k documents to retrieve (default: 5)."
    )
    args = parser.parse_args()

    run_pipeline(
        query=args.query,
        force_reingest=args.force_reingest,
        limit=args.limit
    )
