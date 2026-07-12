from typing import List
from src.ingestion.loader import Document
from src.retrieval.embedder import BGEEmbedder
from src.retrieval.vector_store import QdrantStore, DEFAULT_COLLECTION


class Retriever:
    """Ties the embedder and vector store together to retrieve documents matching a query."""
    def __init__(self, embedder: BGEEmbedder, vector_store: QdrantStore, collection_name: str = DEFAULT_COLLECTION):
        self.embedder = embedder
        self.vector_store = vector_store
        self.collection_name = collection_name

    def retrieve(self, query: str, limit: int = 5) -> List[Document]:
        """Embeds the query and retrieves the top-k similar documents from the vector store."""
        query_vector = self.embedder.embed_query(query)
        return self.vector_store.search(
            query_vector=query_vector,
            collection_name=self.collection_name,
            limit=limit
        )


if __name__ == "__main__":
    # Self-test: requires pre-existing setup or will be empty
    print("Testing Retriever module instantiation...")
    embedder = BGEEmbedder()
    store = QdrantStore()
    retriever = Retriever(embedder, store)
    print("Retriever successfully initialized.")
