import os
import fitz

def generate_pdf(output_path: str):
    """Generates a simple PDF with test content using PyMuPDF (fitz)."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    doc = fitz.open()
    page = doc.new_page()
    
    # Text container rect (X-start, Y-start, X-end, Y-end)
    rect = fitz.Rect(50, 50, 550, 750)
    
    text = (
        "RAG-Guard Security & Document Ingestion Test\n\n"
        "This PDF document is generated to test PyMuPDF (fitz) text parsing capabilities.\n\n"
        "Security Concepts:\n"
        "1. Prompt Injection: Traditional prompt injection occurs when a user directly crafts instructions "
        "to override the system prompt. In contrast, 'Indirect Prompt Injection' is a new vulnerability where "
        "the attack payload is stored inside an external data source (like a PDF or webpage). When the RAG pipeline "
        "retrieves this document, the payload enters the context window and tricks the LLM into executing malicious "
        "commands, ignoring its original system instructions.\n\n"
        "2. PII Detection: High-risk documents often contain Personally Identifiable Information (PII) like names, "
        "addresses, phone numbers, or social security numbers. Presidio scanner intercepts these chunks pre-generation.\n\n"
        "3. Local Model Verification: Milestone 1 is configured to use gemma3:1b via local Ollama."
    )
    
    page.insert_textbox(rect, text, fontsize=11, fontname="helv")
    doc.save(output_path)
    doc.close()
    print(f"Sample PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    generate_pdf("data/raw_docs/sample_doc2.pdf")
