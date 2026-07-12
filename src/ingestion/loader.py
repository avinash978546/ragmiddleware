import os
from typing import List

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class Document:
    """Represents a loaded document with text content and metadata."""
    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata or {}

    def __repr__(self):
        return f"Document(metadata={self.metadata}, content_len={len(self.page_content)})"


def load_txt(file_path: str) -> Document:
    """Loads text from a TXT file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Document(
        page_content=content,
        metadata={"source": file_path, "file_type": "txt"}
    )


def load_pdf(file_path: str) -> Document:
    """Loads text from a PDF file using PyMuPDF (fitz)."""
    if fitz is None:
        raise ImportError("PyMuPDF (fitz) is not installed. Please install it using 'pip install pymupdf'.")
    
    doc = fitz.open(file_path)
    text_content = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text_content.append(page.get_text())
    
    full_text = "\n\n".join(text_content)
    return Document(
        page_content=full_text,
        metadata={
            "source": file_path,
            "file_type": "pdf",
            "pages": len(doc)
        }
    )


def load_directory(directory_path: str) -> List[Document]:
    """Loads all supported documents (.txt, .pdf) in the given directory."""
    documents = []
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        return documents

    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        if not os.path.isfile(file_path):
            continue

        ext = os.path.splitext(filename)[1].lower()
        try:
            if ext == ".txt":
                documents.append(load_txt(file_path))
            elif ext == ".pdf":
                documents.append(load_pdf(file_path))
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    return documents


if __name__ == "__main__":
    # Quick self-test
    test_dir = "data/raw_docs"
    print(f"Loading documents from {test_dir}...")
    docs = load_directory(test_dir)
    print(f"Loaded {len(docs)} documents:")
    for d in docs:
        print(d)
