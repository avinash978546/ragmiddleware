# RAG Evaluation & Guardrails Harness — Architecture

## 1. Overview

**Project name:** RAG-Guard (RAG Evaluation & Guardrails Harness)

**Problem statement:** Most RAG tutorials stop once retrieval + generation "works." Production RAG systems fail silently in two ways: (a) hallucinated/unfaithful answers, and (b) indirect prompt injection, where malicious instructions embedded inside *retrieved documents* hijack the LLM's behavior. RAG-Guard is a middleware + evaluation layer that sits inside any RAG pipeline, intercepts data at the retrieval and generation checkpoints, and produces a quantitative safety/quality scorecard.

**Core idea:** Not another "chat with your PDF" app. A pipeline-agnostic harness that any RAG system can be plugged into, scoring retrieval quality, generation faithfulness, and security posture — fully offline, zero API cost.

**Deployment model:** 100% local / on-prem / air-gapped. No paid APIs. Reuses components from the Guardrails Gateway project (DeBERTa injection classifier, Presidio, Detoxify).

---

## 2. High-Level Architecture

```
                         ┌───────────────────────────────────┐
                         │            USER QUERY              │
                         └──────────────────┬──────────────────┘
                                            │
                                            ▼
                         ┌───────────────────────────────────┐
                         │       RAG PIPELINE (under test)     │
                         │  ┌─────────────────────────────┐   │
                         │  │  Embedding Model (bge-small) │   │
                         │  └───────────────┬─────────────┘   │
                         │                  ▼                  │
                         │  ┌─────────────────────────────┐   │
                         │  │  Vector Store (Qdrant/Chroma)│   │
                         │  └───────────────┬─────────────┘   │
                         │                  ▼                  │
                         │        Top-k Retrieved Chunks       │
                         └──────────────────┬──────────────────┘
                                            │
                                            ▼
                 ┌────────────────────────────────────────────────┐
                 │      MIDDLEWARE CHECKPOINT 1: PRE-GENERATION     │
                 │  ─────────────────────────────────────────────  │
                 │  • Indirect Prompt Injection Scan (DeBERTa)      │
                 │  • PII Detection on retrieved chunks (Presidio)  │
                 │  • Retrieval Quality Metrics (Precision/Recall)  │
                 │  → chunk sanitization / block / flag             │
                 └──────────────────────┬───────────────────────────┘
                                        │  (sanitized context)
                                        ▼
                 ┌────────────────────────────────────────────────┐
                 │            LLM GENERATION (Ollama + Llama)       │
                 └──────────────────────┬───────────────────────────┘
                                        │
                                        ▼
                 ┌────────────────────────────────────────────────┐
                 │      MIDDLEWARE CHECKPOINT 2: POST-GENERATION    │
                 │  ─────────────────────────────────────────────  │
                 │  • Faithfulness Scoring (NLI cross-encoder)      │
                 │  • Answer Relevancy Scoring                      │
                 │  • Toxicity Check (Detoxify)                     │
                 │  • Output PII Leak Check (Presidio)              │
                 └──────────────────────┬───────────────────────────┘
                                        │
                                        ▼
                 ┌────────────────────────────────────────────────┐
                 │        FINAL ANSWER + SCORECARD REPORT           │
                 │   (Streamlit dashboard / JSON / Markdown report) │
                 └────────────────────────────────────────────────┘
```

---

## 3. Component Breakdown

### 3.1 RAG Pipeline Under Test (the "app" layer)

| Component | Tech | Notes |
|---|---|---|
| Document loader | `PyMuPDF` / `unstructured` | Parses PDFs, txt, markdown |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | 512-token chunks, 50-token overlap |
| Embedding model | `bge-small-en-v1.5` via `sentence-transformers` | Runs on CPU, ~130MB |
| Vector store | Qdrant (local, Docker or embedded mode) | Chroma as lightweight alternative |
| Retriever | Top-k similarity search (k=5), optional hybrid BM25 + dense | `rank_bm25` for sparse leg |
| LLM (generation) | Ollama running Llama 3.1 8B (or 3.2 3B / Phi-3-mini if hardware-limited) | Local inference, zero cost |

### 3.2 Middleware Checkpoint 1 — Pre-Generation (Retrieval-side)

| Check | Tech | Reused from Guardrails Gateway? |
|---|---|---|
| Indirect prompt injection detection | Fine-tuned DeBERTa classifier | Yes — direct reuse |
| PII detection in retrieved chunks | Microsoft Presidio | Yes — direct reuse |
| Retrieval quality metrics | Custom Python (Hit Rate@k, MRR, Context Precision/Recall) | New |

**Action on flag:** injected/malicious chunks are either stripped from context, redacted, or the whole request is blocked with a logged reason — configurable policy.

### 3.3 Middleware Checkpoint 2 — Post-Generation (Answer-side)

| Check | Tech | Reused? |
|---|---|---|
| Faithfulness (groundedness) | `cross-encoder/nli-deberta-v3-base` — sentence-level entailment between answer and retrieved context | New |
| Answer relevancy | Cosine similarity between question embedding and generated-answer embedding | New |
| Toxicity | Detoxify | Yes — direct reuse |
| Output PII leakage | Presidio on generated text | Yes — direct reuse |

### 3.4 Evaluation & Reporting Layer

| Component | Tech |
|---|---|
| Metrics aggregation | RAGAS (pointed at local Ollama as judge, not OpenAI) + custom scorer |
| Test set | Hand-labeled QA pairs (30–50) + adversarial injection payloads (JailbreakBench-style, 20–30) |
| Dashboard | Streamlit (matches your Flight Delay Prediction project stack) |
| Report export | Markdown/JSON scorecard, e.g. `report_YYYYMMDD.md` |

---

## 4. Data Flow (Step-by-Step)

1. **Ingestion:** Documents loaded → chunked → embedded → stored in Qdrant.
2. **Query:** User (or test harness) submits a question.
3. **Retrieval:** Top-k chunks pulled via similarity search.
4. **Checkpoint 1:** Each chunk scanned for injection payloads and PII before touching the LLM prompt. Retrieval metrics logged against the labeled test set (if running in eval mode).
5. **Generation:** Sanitized context + query sent to local Llama model via Ollama.
6. **Checkpoint 2:** Generated answer scored for faithfulness (does it match retrieved context?), relevancy, toxicity, and PII leakage.
7. **Output:** Final answer returned to user; all checkpoint results logged.
8. **Reporting:** After a full test-set run, aggregate scores compiled into a scorecard (e.g., "Faithfulness: 94%, Injection block rate: 18/20, PII leak rate: 0%").

---

## 5. Tech Stack Summary

| Layer | Tool | Cost |
|---|---|---|
| Language | Python 3.11 | Free |
| Orchestration | LangChain (or raw Python — recommend raw for more resume credit) | Free |
| Embeddings | `bge-small-en-v1.5` (sentence-transformers) | Free, local |
| Vector DB | Qdrant (local/embedded) | Free |
| LLM runtime | Ollama + Llama 3.1 8B / 3.2 3B | Free, local |
| Injection detection | Fine-tuned DeBERTa (from Guardrails Gateway) | Free, local |
| PII detection | Microsoft Presidio | Free |
| Toxicity | Detoxify | Free |
| Faithfulness scorer | `cross-encoder/nli-deberta-v3-base` | Free, local |
| Eval framework | RAGAS (local LLM judge mode) | Free |
| Dashboard | Streamlit | Free |
| Dev environment | Antigravity IDE | — |

**Total cost: ₹0.** No API keys, no cloud billing.

---

## 6. Folder Structure

```
rag-guard/
├── architecture.md
├── README.md
├── requirements.txt
├── data/
│   ├── raw_docs/                 # source PDFs/txt for the RAG corpus
│   ├── test_set/
│   │   ├── qa_pairs.jsonl        # labeled query→expected-chunk/answer set
│   │   └── injection_payloads.jsonl
├── src/
│   ├── ingestion/
│   │   ├── loader.py
│   │   └── chunker.py
│   ├── retrieval/
│   │   ├── embedder.py
│   │   ├── vector_store.py
│   │   └── retriever.py
│   ├── middleware/
│   │   ├── pre_generation.py     # injection + PII scan on chunks
│   │   └── post_generation.py    # faithfulness, toxicity, PII leak
│   ├── generation/
│   │   └── llm_client.py         # Ollama wrapper
│   ├── evaluation/
│   │   ├── retrieval_metrics.py  # Hit Rate, MRR, Context Precision/Recall
│   │   ├── faithfulness.py       # NLI scoring
│   │   └── run_eval.py           # orchestrates full test-set run
│   └── pipeline.py               # wires everything together end-to-end
├── dashboard/
│   └── app.py                    # Streamlit scorecard UI
├── reports/
│   └── report_YYYYMMDD.md
└── notebooks/
    └── exploration.ipynb
```

---

## 7. Evaluation Metrics Reference

| Metric | Measures | Formula/Method |
|---|---|---|
| Hit Rate@k | Did the correct chunk appear in top-k? | Binary hit / total queries |
| MRR | How high was the correct chunk ranked? | Mean of 1/rank across queries |
| Context Precision | % of retrieved chunks that are relevant | relevant retrieved / total retrieved |
| Context Recall | % of relevant chunks that were retrieved | relevant retrieved / total relevant |
| Faithfulness | Is every claim in the answer supported by context? | NLI entailment score per sentence, averaged |
| Answer Relevancy | Does the answer address the question? | Cosine sim(question embedding, answer embedding) |
| Injection Block Rate | % of adversarial payloads caught pre-generation | blocked / total attempts |
| PII Leak Rate | % of outputs containing unredacted PII | flagged outputs / total outputs |
| Toxicity Rate | % of outputs flagged toxic | flagged / total outputs |

---

## 8. Build Order (Milestones)

1. **M1 — Base RAG pipeline:** ingestion → chunking → embedding → Qdrant → retrieval → Ollama generation, working end-to-end with no middleware.
2. **M2 — Retrieval evaluation:** labeled test set + Hit Rate/MRR/Context Precision-Recall scoring.
3. **M3 — Pre-generation middleware:** wire in DeBERTa injection detector + Presidio on retrieved chunks; build adversarial injection test set.
4. **M4 — Post-generation middleware:** faithfulness scorer (NLI) + Detoxify + output PII check.
5. **M5 — Reporting:** aggregate all metrics into a scorecard; Streamlit dashboard.
6. **M6 — Polish:** README, architecture diagram, sample report, demo video/gif for resume/portfolio.

---

## 9. Resume/Interview Framing

> "Built a middleware and evaluation harness for RAG pipelines that intercepts both the retrieval and generation stages — detecting indirect prompt injection from poisoned documents, PII leakage, hallucination (via NLI-based faithfulness scoring), and toxicity — fully offline using Ollama, DeBERTa, and Presidio, with zero API cost. Extends the guardrails architecture from [Guardrails Gateway project] to a new attack surface: retrieval-side prompt injection."

---

## 10. Future Extensions (optional, if time permits)

- Hybrid retrieval (BM25 + dense) with re-ranker (cross-encoder) to boost Context Precision.
- Graph-based retrieval for multi-hop questions.
- Support plugging in *external* RAG pipelines (not just the reference one) via a standard adapter interface, making the harness genuinely pipeline-agnostic.
- CI-style regression testing: run the eval suite automatically whenever the corpus or prompt template changes.
