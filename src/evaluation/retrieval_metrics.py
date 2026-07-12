import os
from typing import List, Dict, Any
from src.ingestion.loader import Document

def is_relevant(retrieved_chunk: Document, ground_truth_chunks: List[Dict[str, Any]]) -> bool:
    """
    Checks if a retrieved chunk matches any of the ground truth document chunks.
    Matches are based on the base filename of the source document and the chunk index.
    """
    source_path = retrieved_chunk.metadata.get("source", "")
    retrieved_doc = os.path.basename(source_path)
    retrieved_idx = retrieved_chunk.metadata.get("chunk_index")

    for gt in ground_truth_chunks:
        gt_doc = gt.get("document", "")
        gt_idx = gt.get("chunk_index")
        
        # Check matching document base name and chunk index
        if gt_doc == retrieved_doc and gt_idx == retrieved_idx:
            return True
            
    return False


def calculate_hit_rate(retrieved: List[Document], ground_truth_chunks: List[Dict[str, Any]]) -> float:
    """
    Hit Rate@k: Returns 1.0 if at least one ground-truth chunk appears 
    in the retrieved chunks, otherwise 0.0.
    """
    if not retrieved or not ground_truth_chunks:
        return 0.0
        
    for chunk in retrieved:
        if is_relevant(chunk, ground_truth_chunks):
            return 1.0
    return 0.0


def calculate_mrr(retrieved: List[Document], ground_truth_chunks: List[Dict[str, Any]]) -> float:
    """
    MRR (Mean Reciprocal Rank): Finds the highest rank (1-indexed) among 
    retrieved chunks that matches a ground-truth chunk, returning 1/rank.
    Returns 0.0 if no match is found.
    """
    if not retrieved or not ground_truth_chunks:
        return 0.0

    for idx, chunk in enumerate(retrieved):
        if is_relevant(chunk, ground_truth_chunks):
            return 1.0 / (idx + 1)
    return 0.0


def calculate_context_precision(retrieved: List[Document], ground_truth_chunks: List[Dict[str, Any]]) -> float:
    """
    Context Precision: % of retrieved chunks that are relevant to the query.
    Formula: relevant retrieved / total retrieved
    """
    if not retrieved or not ground_truth_chunks:
        return 0.0
        
    relevant_retrieved = sum(1 for chunk in retrieved if is_relevant(chunk, ground_truth_chunks))
    return relevant_retrieved / len(retrieved)


def calculate_context_recall(retrieved: List[Document], ground_truth_chunks: List[Dict[str, Any]]) -> float:
    """
    Context Recall: % of relevant chunks that were retrieved.
    Formula: relevant retrieved / total relevant (ground truth chunks)
    """
    if not retrieved or not ground_truth_chunks:
        return 0.0
        
    relevant_retrieved = sum(1 for chunk in retrieved if is_relevant(chunk, ground_truth_chunks))
    return relevant_retrieved / len(ground_truth_chunks)
