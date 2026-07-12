from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

from src.ingestion.loader import Document

# Global tokenizer instance loaded from local cache or downloaded once
TOKENIZER_MODEL = "BAAI/bge-small-en-v1.5"
_tokenizer = None

def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        try:
            # Reuses huggingface cache if model was already pulled by sentence-transformers
            _tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_MODEL)
        except Exception as e:
            print(f"Warning: Could not load tokenizer {TOKENIZER_MODEL} offline: {e}. Falling back to default length function (characters).")
            _tokenizer = None
    return _tokenizer

def token_length(text: str) -> int:
    """Calculates the number of tokens in the text using the BGE tokenizer."""
    tokenizer = get_tokenizer()
    if tokenizer is not None:
        try:
            return len(tokenizer.encode(text, add_special_tokens=False))
        except Exception:
            pass
    # Fallback to rough token estimation (word count) if tokenizer fails
    return len(text.split())


def chunk_documents(documents: List[Document], chunk_size: int = 512, chunk_overlap: int = 50) -> List[Document]:
    """
    Splits documents into smaller chunks using RecursiveCharacterTextSplitter.
    Determines length in tokens using the BGE tokenizer.
    """
    # Initialize the splitter with our token length function
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=token_length
    )

    chunks = []
    for doc in documents:
        # Split text using langchain's built-in RecursiveCharacterTextSplitter method
        split_texts = splitter.split_text(doc.page_content)
        
        for idx, text in enumerate(split_texts):
            # Propagate and enrich metadata
            metadata = doc.metadata.copy()
            metadata["chunk_index"] = idx
            
            chunks.append(Document(
                page_content=text,
                metadata=metadata
            ))

    return chunks


if __name__ == "__main__":
    # Quick self-test
    test_docs = [
        Document("Hello, this is a very simple test document to verify chunking behavior.", {"source": "test.txt"})
    ]
    print("Chunking test documents...")
    chunks = chunk_documents(test_docs, chunk_size=5, chunk_overlap=1)
    print(f"Created {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"Chunk {chunk.metadata['chunk_index']}: {chunk.page_content} (tokens: {token_length(chunk.page_content)})")
