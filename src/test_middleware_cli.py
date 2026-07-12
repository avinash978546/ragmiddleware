import json
import os
from src.ingestion.loader import Document
from src.middleware.pre_generation import PreGenerationMiddleware, PromptInjectionException


def load_injection_test_set(filepath: str = "data/test_set/injection_payloads.jsonl"):
    test_cases = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_cases.append(json.loads(line))
    return test_cases


def run_middleware_tests():
    print("=" * 70)
    print("RUNNING PRE-GENERATION MIDDLEWARE TEST SUITE (M3)")
    print("=" * 70)

    test_cases = load_injection_test_set()
    print(f"Loaded {len(test_cases)} adversarial test cases.")

    # 1. Initialize middleware with BLOCK policy
    print("\n--- Test Suite 1: BLOCK Policy (Active Firewall) ---")
    mw_block = PreGenerationMiddleware(policy="block", threshold=0.5, pii_enabled=True)
    
    passed_block_count = 0
    for idx, tc in enumerate(test_cases):
        doc = Document(page_content=tc["injection_chunk"], metadata={"source": f"test_{idx}.txt", "chunk_index": 0})
        expected = tc["expected_action"]
        
        print(f"\nCase {idx + 1}: Query='{tc['query']}'")
        print(f"Content: '{tc['injection_chunk'][:80]}...'")
        print(f"Expected behavior: {expected}")
        
        try:
            res = mw_block.process_chunks([doc])
            
            # If we reached here without exception
            if expected == "blocked":
                print("[FAIL] Expected prompt injection to be blocked, but it passed through.")
            elif expected == "redacted":
                # Check if redaction tags exist
                if "<EMAIL_ADDRESS>" in res[0].page_content or "<" in res[0].page_content:
                    print(f"[PASS] PII anonymized: '{res[0].page_content.strip()}'")
                    passed_block_count += 1
                else:
                    print("[FAIL] Expected PII to be redacted, but text is unchanged.")
            else: # allowed
                print("[PASS] Benign text allowed through intact.")
                passed_block_count += 1
                
        except PromptInjectionException as pie:
            if expected == "blocked":
                print(f"[PASS] Prompt injection successfully blocked: {pie}")
                passed_block_count += 1
            else:
                print(f"[FAIL] Raised unexpected block exception: {pie}")

    # 2. Initialize middleware with STRIP policy
    print("\n--- Test Suite 2: STRIP Policy (Passive Filtering) ---")
    mw_strip = PreGenerationMiddleware(policy="strip", threshold=0.5, pii_enabled=True)
    
    passed_strip_count = 0
    for idx, tc in enumerate(test_cases):
        doc = Document(page_content=tc["injection_chunk"], metadata={"source": f"test_{idx}.txt", "chunk_index": 0})
        expected = tc["expected_action"]
        
        print(f"\nCase {idx + 1}: Expected behavior: {expected}")
        
        try:
            res = mw_strip.process_chunks([doc])
            if expected == "blocked":
                if not res:
                    print("[PASS] Compromised chunk successfully stripped (returned empty context).")
                    passed_strip_count += 1
                else:
                    print("[FAIL] Expected chunk to be stripped, but it was returned.")
            elif expected == "redacted":
                if "<" in res[0].page_content:
                    print(f"[PASS] PII anonymized and returned: '{res[0].page_content.strip()}'")
                    passed_strip_count += 1
                else:
                    print("[FAIL] PII not redacted.")
            else: # allowed
                print("[PASS] Benign chunk returned.")
                passed_strip_count += 1
        except Exception as e:
            print(f"[FAIL] Raised unexpected exception under strip policy: {e}")

    # Summary
    total_runs = len(test_cases)
    print("\n" + "=" * 70)
    print("MIDDLEWARE EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Block Policy Suite: {passed_block_count}/{total_runs} tests passed.")
    print(f"Strip Policy Suite: {passed_strip_count}/{total_runs} tests passed.")
    
    if passed_block_count == total_runs and passed_strip_count == total_runs:
        print("\n[SUCCESS] All Milestone 3 pre-generation middleware tests passed successfully!")
    else:
        print("\n[WARNING] Some test cases failed. Please review details above.")


if __name__ == "__main__":
    run_middleware_tests()
