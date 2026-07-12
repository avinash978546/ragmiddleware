import os
import uuid
import hashlib
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

from src.ingestion.loader import Document

# Load env variables
load_dotenv()

QDRANT_PATH = os.getenv("QDRANT_PATH", "data/qdrant_db")
DEFAULT_COLLECTION = "rag_guard_collection"
EMBEDDING_DIM = 384  # bge-small-en-v1.5 embedding dimension


def generate_id_from_text(text: str) -> str:
    """Generates a consistent UUID based on the text content to prevent duplicate chunks."""
    hash_object = hashlib.md5(text.encode("utf-8"))
    hex_dig = hash_object.hexdigest()
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, hex_dig))


class QdrantStore:
    """Wrapper around Qdrant client running in local embedded mode."""
    def __init__(self, path: str = QDRANT_PATH):
        self.path = path
        # Ensure parent directory for Qdrant storage exists
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        # Local embedded mode
        self.client = QdrantClient(path=self.path)

    def init_collection(self, collection_name: str = DEFAULT_COLLECTION, vector_size: int = EMBEDDING_DIM):
        """Creates collection if it doesn't already exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        
        if not exists:
            print(f"Creating collection '{collection_name}' with size {vector_size}...")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        else:
            print(f"Collection '{collection_name}' already exists.")

    def delete_collection(self, collection_name: str = DEFAULT_COLLECTION):
        """Deletes a collection."""
        collections = self.client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if exists:
            self.client.delete_collection(collection_name=collection_name)
            print(f"Deleted collection '{collection_name}'.")

    def get_collection_count(self, collection_name: str = DEFAULT_COLLECTION) -> int:
        """Returns the number of points in the collection."""
        try:
            res = self.client.get_collection(collection_name=collection_name)
            return res.points_count
        except Exception:
            return 0

    def upsert_chunks(self, chunks: List[Document], embeddings: List[List[float]], collection_name: str = DEFAULT_COLLECTION):
        """Upserts embedded chunks into Qdrant."""
        if not chunks or not embeddings:
            return

        points = []
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            point_id = generate_id_from_text(chunk.page_content)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb,
                    payload={
                        "page_content": chunk.page_content,
                        "metadata": chunk.metadata
                    }
                )
            )

        print(f"Upserting {len(points)} chunks into collection '{collection_name}'...")
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )

    def search(self, query_vector: List[float], collection_name: str = DEFAULT_COLLECTION, limit: int = 5) -> List[Document]:
        """Searches the vector store for top-k similar chunks."""
        search_result = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )

        retrieved_docs = []
        for hit in search_result:
            payload = hit.payload
            retrieved_docs.append(Document(
                page_content=payload["page_content"],
                metadata=payload.get("metadata", {})
            ))
            
        return retrieved_docs


if __name__ == "__main__":
    # Quick self-test
    print("Testing Qdrant embedded client...")
    store = QdrantStore(path="data/test_qdrant_db")
    store.init_collection("test_col", vector_size=4)
    
    test_chunks = [
        Document("Apple pie recipe", {"category": "cooking"}),
        Document("Deep learning algorithms", {"category": "tech"})
    ]
    test_embs = [
        [0.1, 0.2, 0.3, 0.4],
        [0.9, 0.8, 0.7, 0.6]
    ]
    
    store.upsert_chunks(test_chunks, test_embs, "test_col")
    print(f"Collection count: {store.get_collection_count('test_col')}")
    
    results = store.search([0.15, 0.22, 0.31, 0.42], "test_col", limit=1)
    print(f"Search hit: {results[0].page_content} (metadata: {results[0].metadata})")
    
    # Cleanup
    store.delete_collection("test_col")
