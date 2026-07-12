import os
from typing import List
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load env variables
load_dotenv()

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")


class BGEEmbedder:
    """Manages the local sentence-transformers model for generating document and query embeddings."""
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        # Loads local model (downloads if not present in cache)
        # Note: BGE models are compatible with sentence-transformers natively
        self.model = SentenceTransformer(self.model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a list of document chunks."""
        # For BGE, no query instruction prefix is needed for documents.
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding for a single user query."""
        # BAAI/bge-small-en-v1.5 does not strictly require instructions for queries,
        # but the standard BGE guideline suggests query syntax matches.
        # However, for bge-small-en-v1.5, simple encode is sufficient.
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.tolist()


if __name__ == "__main__":
    # Quick self-test
    print(f"Loading embedder with model: {EMBEDDING_MODEL_NAME}...")
    embedder = BGEEmbedder()
    test_texts = ["Hello world", "RAG evaluation harness"]
    embs = embedder.embed_documents(test_texts)
    print(f"Generated {len(embs)} document embeddings of dimension {len(embs[0])}")
    
    q_emb = embedder.embed_query("What is RAG-Guard?")
    print(f"Generated query embedding of dimension {len(q_emb)}")
