# RAG-Guard (M1–M3)

RAG-Guard is a local, offline evaluation and guardrails harness for Retrieval-Augmented Generation (RAG) pipelines. This repository implements milestones through **M3 (Pre-Generation Middleware)**.

All components run locally — zero API costs, zero data leakage, full air-gapped support.

---

## Milestone Status

| Milestone | Status | Description |
|---|---|---|
| **M1** | ✅ Complete | Base RAG pipeline: ingestion → retrieval → Ollama generation |
| **M2** | ✅ Complete | Retrieval evaluation: Hit Rate, MRR, Context Precision/Recall |
| **M3** | ✅ Complete | Pre-generation middleware: DeBERTa injection scan + Presidio PII redaction |
| M4 | Pending | Post-generation middleware: faithfulness, toxicity, output PII |
| M5 | Pending | Streamlit dashboard + aggregate scorecard |
| M6 | Pending | Polish: demo, portfolio assets |

---

## Technical Stack

*   **Language:** Python 3.11
*   **Embeddings:** `BAAI/bge-small-en-v1.5` via `sentence-transformers`
*   **Vector DB:** Qdrant embedded mode (`data/qdrant_db/`)
*   **LLM:** Ollama + `gemma3:1b` at `http://localhost:11434`
*   **Injection Detector (M3):** `protectai/deberta-v3-base-prompt-injection-v2`
*   **PII Scanner (M3):** Microsoft Presidio + spaCy `en_core_web_sm`
*   **Document Parsers:** PyMuPDF (PDF) + raw TXT handlers

---

## Directory Structure

```text
ragmiddleware/
├── architecture.md
├── README.md
├── requirements.txt
├── .env.example
├── data/
│   ├── raw_docs/                     # Source PDFs/txt for the RAG corpus
│   └── test_set/
│       ├── qa_pairs.jsonl            # M2 labeled retrieval test set
│       └── injection_payloads.jsonl  # M3 adversarial injection test set
├── src/
│   ├── ingestion/
│   │   ├── loader.py
│   │   └── chunker.py
│   ├── retrieval/
│   │   ├── embedder.py
│   │   ├── vector_store.py
│   │   └── retriever.py
│   ├── middleware/
│   │   └── pre_generation.py         # M3: DeBERTa + Presidio checkpoint
│   ├── generation/
│   │   └── llm_client.py
│   ├── evaluation/
│   │   ├── retrieval_metrics.py      # M2 metrics
│   │   ├── run_eval.py               # M2 eval runner + report
│   │   └── run_middleware_eval.py    # M3 eval runner + report
│   ├── test_middleware_cli.py        # M3 quick test suite
│   └── pipeline.py                   # End-to-end pipeline (M1–M3)
└── reports/                          # Auto-generated scorecard reports
```

---

## Setup Instructions

### 1. Prerequisite: Local LLM (Ollama)
```bash
ollama pull gemma3:1b
ollama run gemma3:1b "Say Hello!"
```

### 2. Environment Setup
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Configure Environment
Copy `.env.example` to `.env` and adjust if needed:
```env
INJECTION_POLICY=block      # block | strip | flag
INJECTION_THRESHOLD=0.5
PII_ENABLED=True
```

### 4. Generate Sample Data
```bash
python src/create_sample_pdf.py
```

---

## Running the Pipeline (M1–M3)

The pipeline now runs retrieval **and** pre-generation security checkpoints before calling the LLM:

```bash
python src/pipeline.py --query "What is indirect prompt injection?"
```

Options:
*   `--query` — question to answer
*   `--force-reingest` — re-index documents from `data/raw_docs/`
*   `--limit` — top-k chunks to retrieve (default: 5)

If an injected chunk is retrieved, the request is blocked (default policy) with a clear security exception.

---

## M2: Retrieval Evaluation

Run the labeled QA test set and generate a markdown scorecard:

```bash
python -m src.evaluation.run_eval
```

Report saved to `reports/report_YYYYMMDD_HHMMSS.md`.

---

## M3: Pre-Generation Middleware Evaluation

Run the adversarial injection test suite (24 cases):

```bash
python -m src.evaluation.run_middleware_eval
```

Quick interactive test suite:

```bash
python -m src.test_middleware_cli
```

Report saved to `reports/middleware_report_YYYYMMDD_HHMMSS.md`.

### M3 Middleware Behavior

| Policy | On Injection Detected |
|---|---|
| `block` (default) | Raises `PromptInjectionException`, halts pipeline |
| `strip` | Removes compromised chunks, continues with clean context |
| `flag` | Logs warning, passes all chunks (including injected) to LLM |

PII (emails, phone numbers, SSNs, etc.) is always redacted via Presidio tags like `<EMAIL_ADDRESS>` before generation.

---

## Next: M4

Post-generation middleware — faithfulness scoring (NLI cross-encoder), answer relevancy, Detoxify toxicity check, and output PII leak detection.
