import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

from src.retrieval.embedder import BGEEmbedder
from src.retrieval.vector_store import QdrantStore, DEFAULT_COLLECTION
from src.retrieval.retriever import Retriever
from src.evaluation.retrieval_metrics import (
    calculate_hit_rate,
    calculate_mrr,
    calculate_context_precision,
    calculate_context_recall
)


def load_test_set(filepath: str) -> List[Dict[str, Any]]:
    """Loads labeled QA pairs from a JSONL file."""
    test_set = []
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Test set file not found: {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_set.append(json.loads(line))
    return test_set


def run_evaluation(test_set_path: str = "data/test_set/qa_pairs.jsonl", k: int = 5):
    """Orchestrates query retrieval and evaluates metrics across the test set."""
    print("=" * 70)
    print(f"RAG-GUARD RETRIEVAL EVALUATION (Milestone 2 - k={k})")
    print("=" * 70)

    # 1. Init clients
    print("\n[1/3] Initializing local models and database...")
    embedder = BGEEmbedder()
    vector_store = QdrantStore()
    
    collection_count = vector_store.get_collection_count(DEFAULT_COLLECTION)
    if collection_count == 0:
        print("ERROR: Vector store collection is empty! Please run 'python -m src.pipeline' first to ingest documents.")
        return

    retriever = Retriever(embedder, vector_store)

    # 2. Load test cases
    print(f"\n[2/3] Loading test cases from '{test_set_path}'...")
    try:
        test_cases = load_test_set(test_set_path)
        print(f"Loaded {len(test_cases)} test cases.")
    except Exception as e:
        print(f"ERROR: Failed to load test cases: {e}")
        return

    # 3. Evaluate each test case
    print(f"\n[3/3] Running retrieval and computing metrics...")
    results = []
    
    total_hit_rate = 0.0
    total_mrr = 0.0
    total_precision = 0.0
    total_recall = 0.0

    print("\n" + "-" * 110)
    print(f"{'Query':<50} | {'HitRate':<8} | {'MRR':<8} | {'Precision':<10} | {'Recall':<8}")
    print("-" * 110)

    for case in test_cases:
        query = case["query"]
        ground_truth = case["ground_truth_chunks"]
        
        # Retrieve top-k chunks
        retrieved_chunks = retriever.retrieve(query, limit=k)
        
        # Compute metrics
        hit_rate = calculate_hit_rate(retrieved_chunks, ground_truth)
        mrr = calculate_mrr(retrieved_chunks, ground_truth)
        precision = calculate_context_precision(retrieved_chunks, ground_truth)
        recall = calculate_context_recall(retrieved_chunks, ground_truth)
        
        # Accumulate
        total_hit_rate += hit_rate
        total_mrr += mrr
        total_precision += precision
        total_recall += recall
        
        # Store for report
        results.append({
            "query": query,
            "ground_truth": ground_truth,
            "retrieved": [
                {
                    "document": os.path.basename(c.metadata.get("source", "")),
                    "chunk_index": c.metadata.get("chunk_index", 0),
                    "content_snippet": c.page_content[:100].replace("\n", " ") + "..."
                } for c in retrieved_chunks
            ],
            "metrics": {
                "hit_rate": hit_rate,
                "mrr": mrr,
                "precision": precision,
                "recall": recall
            }
        })
        
        # Print row
        short_query = query[:47] + "..." if len(query) > 50 else query
        print(f"{short_query:<50} | {hit_rate:<8.2f} | {mrr:<8.2f} | {precision:<10.2f} | {recall:<8.2f}")

    print("-" * 110)
    
    # Compute Averages
    num_cases = len(test_cases)
    avg_hit_rate = total_hit_rate / num_cases
    avg_mrr = total_mrr / num_cases
    avg_precision = total_precision / num_cases
    avg_recall = total_recall / num_cases

    print(f"{'OVERALL AVERAGE':<50} | {avg_hit_rate:<8.2f} | {avg_mrr:<8.2f} | {avg_precision:<10.2f} | {avg_recall:<8.2f}")
    print("=" * 110)

    # 4. Generate Markdown Scorecard Report
    generate_markdown_report(k, collection_count, results, avg_hit_rate, avg_mrr, avg_precision, avg_recall)


def generate_markdown_report(k: int, doc_count: int, results: List[Dict[str, Any]], 
                             avg_hit: float, avg_mrr: float, avg_prec: float, avg_rec: float):
    """Generates and writes a timestamped evaluation report in the reports directory."""
    os.makedirs("reports", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"reports/report_{timestamp}.md"
    
    md_content = []
    md_content.append(f"# RAG-Guard Retrieval Evaluation Report — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_content.append("## Executive Summary\n")
    md_content.append(f"This scorecard evaluates the quality and safety profile of the RAG retriever module. Testing was conducted on a local database containing **{doc_count} chunks** in local embedded Qdrant mode.\n")
    
    md_content.append("### Pipeline Configuration")
    md_content.append(f"- **Embedding Model**: `BAAI/bge-small-en-v1.5` (local sentence-transformers)")
    md_content.append(f"- **Retrieval Configuration**: Top-k similarity search (k={k})")
    md_content.append(f"- **Vector Index Database**: Qdrant Local/Embedded Mode\n")
    
    md_content.append("### Aggregate Scorecard")
    md_content.append("| Metric | Score | Description |")
    md_content.append("|---|---|---|")
    md_content.append(f"| **Hit Rate@{k}** | {avg_hit:.2%} | Was at least one expected chunk retrieved? |")
    md_content.append(f"| **Mean Reciprocal Rank (MRR)** | {avg_mrr:.2f} | How highly ranked was the correct answer? |")
    md_content.append(f"| **Context Precision** | {avg_prec:.2%} | What percentage of retrieved chunks were relevant? |")
    md_content.append(f"| **Context Recall** | {avg_rec:.2%} | What percentage of total relevant chunks were retrieved? |\n")
    
    md_content.append("---")
    md_content.append("## Detailed Query Breakdown\n")
    
    md_content.append("| Query | Hit Rate | MRR | Context Precision | Context Recall |")
    md_content.append("|---|---|---|---|---|")
    for r in results:
        md_content.append(f"| {r['query']} | {r['metrics']['hit_rate']:.2f} | {r['metrics']['mrr']:.2f} | {r['metrics']['precision']:.2f} | {r['metrics']['recall']:.2f} |")
    
    md_content.append("\n---")
    md_content.append("## Retrieval Details per Query\n")
    
    for idx, r in enumerate(results):
        md_content.append(f"### {idx+1}. Query: \"{r['query']}\"")
        md_content.append(f"**Expected Ground-Truth Chunks**:")
        for gt in r["ground_truth"]:
            md_content.append(f"- Document: `{gt['document']}`, Chunk Index: `{gt['chunk_index']}`")
        
        md_content.append(f"\n**Retrieved Chunks**:")
        for rank, ret in enumerate(r["retrieved"]):
            match_status = "✅ Match" if any(
                ret["document"] == gt["document"] and ret["chunk_index"] == gt["chunk_index"] 
                for gt in r["ground_truth"]
            ) else "❌ No Match"
            
            md_content.append(f"- Rank {rank+1}: `{ret['document']}`, Chunk: `{ret['chunk_index']}` ({match_status})")
            md_content.append(f"  > *Snippet*: {ret['content_snippet']}")
        md_content.append("")

    with open(report_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    print(f"\nMarkdown scorecard report written to: {report_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG retriever using a labeled test set.")
    parser.add_argument(
        "--test-set", 
        type=str, 
        default="data/test_set/qa_pairs.jsonl",
        help="Path to labeled test set (default: data/test_set/qa_pairs.jsonl)"
    )
    parser.add_argument(
        "--k", 
        type=int, 
        default=5,
        help="Top-k retrieval limit (default: 5)"
    )
    args = parser.parse_args()

    run_evaluation(test_set_path=args.test_set, k=args.k)
