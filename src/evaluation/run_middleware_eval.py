import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

from src.ingestion.loader import Document
from src.middleware.pre_generation import PreGenerationMiddleware, PromptInjectionException


def load_injection_test_set(filepath: str) -> List[Dict[str, Any]]:
    """Loads adversarial injection test cases from a JSONL file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Injection test set not found: {filepath}")

    test_cases = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_cases.append(json.loads(line))
    return test_cases


def evaluate_case(middleware: PreGenerationMiddleware, case: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """Runs a single injection test case and returns pass/fail details."""
    doc = Document(
        page_content=case["injection_chunk"],
        metadata={"source": f"test_{idx}.txt", "chunk_index": 0},
    )
    expected = case["expected_action"]
    result = {
        "query": case["query"],
        "expected_action": expected,
        "passed": False,
        "actual_action": "unknown",
        "output_snippet": "",
        "error": None,
    }

    try:
        processed = middleware.process_chunks([doc])
        output_text = processed[0].page_content if processed else ""

        if expected == "blocked":
            result["actual_action"] = "allowed"
        elif expected == "redacted":
            if processed and ("<" in output_text):
                result["actual_action"] = "redacted"
                result["passed"] = True
                result["output_snippet"] = output_text[:120]
            else:
                result["actual_action"] = "unchanged"
        else:
            if processed and output_text == case["injection_chunk"]:
                result["actual_action"] = "allowed"
                result["passed"] = True
                result["output_snippet"] = output_text[:120]
            else:
                result["actual_action"] = "modified"

    except PromptInjectionException as exc:
        result["error"] = str(exc)
        if expected == "blocked":
            result["actual_action"] = "blocked"
            result["passed"] = True
        else:
            result["actual_action"] = "blocked"

    return result


def run_middleware_evaluation(
    test_set_path: str = "data/test_set/injection_payloads.jsonl",
    policy: str = "block",
    threshold: float = 0.5,
    pii_enabled: bool = True,
):
    """Runs the full M3 adversarial test suite and writes a markdown scorecard."""
    print("=" * 70)
    print(f"RAG-GUARD PRE-GENERATION MIDDLEWARE EVALUATION (Milestone 3)")
    print("=" * 70)

    print(f"\n[1/3] Loading adversarial test set from '{test_set_path}'...")
    test_cases = load_injection_test_set(test_set_path)
    print(f"Loaded {len(test_cases)} test cases.")

    print(f"\n[2/3] Initializing middleware (policy={policy}, threshold={threshold})...")
    middleware = PreGenerationMiddleware(policy=policy, threshold=threshold, pii_enabled=pii_enabled)

    print(f"\n[3/3] Running injection + PII checkpoint tests...")
    results = []
    for idx, case in enumerate(test_cases):
        result = evaluate_case(middleware, case, idx)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{status}] Case {idx + 1}: expected={case['expected_action']}, actual={result['actual_action']}")

    blocked_cases = [r for r in results if r["expected_action"] == "blocked"]
    allowed_cases = [r for r in results if r["expected_action"] == "allowed"]
    redacted_cases = [r for r in results if r["expected_action"] == "redacted"]

    injection_block_rate = (
        sum(1 for r in blocked_cases if r["passed"]) / len(blocked_cases) if blocked_cases else 0.0
    )
    false_positive_rate = (
        sum(1 for r in allowed_cases if not r["passed"]) / len(allowed_cases) if allowed_cases else 0.0
    )
    pii_redaction_rate = (
        sum(1 for r in redacted_cases if r["passed"]) / len(redacted_cases) if redacted_cases else 0.0
    )
    overall_pass_rate = sum(1 for r in results if r["passed"]) / len(results)

    print("\n" + "=" * 70)
    print("MIDDLEWARE EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Injection Block Rate:     {injection_block_rate:.2%} ({sum(1 for r in blocked_cases if r['passed'])}/{len(blocked_cases)})")
    print(f"Benign Pass-Through Rate: {1 - false_positive_rate:.2%} ({sum(1 for r in allowed_cases if r['passed'])}/{len(allowed_cases)})")
    print(f"PII Redaction Rate:       {pii_redaction_rate:.2%} ({sum(1 for r in redacted_cases if r['passed'])}/{len(redacted_cases)})")
    print(f"Overall Pass Rate:        {overall_pass_rate:.2%} ({sum(1 for r in results if r['passed'])}/{len(results)})")

    generate_middleware_report(
        policy=policy,
        threshold=threshold,
        pii_enabled=pii_enabled,
        results=results,
        injection_block_rate=injection_block_rate,
        false_positive_rate=false_positive_rate,
        pii_redaction_rate=pii_redaction_rate,
        overall_pass_rate=overall_pass_rate,
    )


def generate_middleware_report(
    policy: str,
    threshold: float,
    pii_enabled: bool,
    results: List[Dict[str, Any]],
    injection_block_rate: float,
    false_positive_rate: float,
    pii_redaction_rate: float,
    overall_pass_rate: float,
):
    """Writes a timestamped M3 middleware scorecard to the reports directory."""
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"reports/middleware_report_{timestamp}.md"

    blocked_count = sum(1 for r in results if r["expected_action"] == "blocked")
    allowed_count = sum(1 for r in results if r["expected_action"] == "allowed")
    redacted_count = sum(1 for r in results if r["expected_action"] == "redacted")

    lines = [
        f"# RAG-Guard Pre-Generation Middleware Report — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "## Executive Summary\n",
        "This scorecard evaluates **Milestone 3 (M3)** — the pre-generation middleware that scans retrieved context chunks for indirect prompt injection and PII before they reach the LLM.\n",
        "### Middleware Configuration",
        f"- **Injection Classifier**: `protectai/deberta-v3-base-prompt-injection-v2` (local DeBERTa)",
        f"- **PII Scanner**: Microsoft Presidio + spaCy `en_core_web_sm`",
        f"- **Injection Policy**: `{policy}` (block / strip / flag)",
        f"- **Injection Threshold**: `{threshold}`",
        f"- **PII Redaction Enabled**: `{pii_enabled}`\n",
        "### Aggregate Scorecard",
        "| Metric | Score | Description |",
        "|---|---|---|",
        f"| **Injection Block Rate** | {injection_block_rate:.2%} | Adversarial payloads correctly blocked ({sum(1 for r in results if r['expected_action'] == 'blocked' and r['passed'])}/{blocked_count}) |",
        f"| **Benign Pass-Through Rate** | {1 - false_positive_rate:.2%} | Benign chunks allowed without false blocks ({sum(1 for r in results if r['expected_action'] == 'allowed' and r['passed'])}/{allowed_count}) |",
        f"| **PII Redaction Rate** | {pii_redaction_rate:.2%} | PII-containing chunks correctly anonymized ({sum(1 for r in results if r['expected_action'] == 'redacted' and r['passed'])}/{redacted_count}) |",
        f"| **Overall Pass Rate** | {overall_pass_rate:.2%} | All test cases passed ({sum(1 for r in results if r['passed'])}/{len(results)}) |\n",
        "---",
        "## Detailed Test Case Breakdown\n",
        "| # | Query | Expected | Actual | Result |",
        "|---|---|---|---|---|",
    ]

    for idx, r in enumerate(results):
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        short_query = r["query"][:40] + "..." if len(r["query"]) > 40 else r["query"]
        lines.append(f"| {idx + 1} | {short_query} | {r['expected_action']} | {r['actual_action']} | {status} |")

    lines.append("\n---\n## Test Case Details\n")
    for idx, r in enumerate(results):
        lines.append(f"### {idx + 1}. Query: \"{r['query']}\"")
        lines.append(f"- **Expected**: `{r['expected_action']}`")
        lines.append(f"- **Actual**: `{r['actual_action']}`")
        lines.append(f"- **Result**: {'PASS' if r['passed'] else 'FAIL'}")
        if r.get("output_snippet"):
            lines.append(f"- **Output Snippet**: `{r['output_snippet']}`")
        if r.get("error"):
            lines.append(f"- **Block Reason**: {r['error'][:200]}")
        lines.append("")

    with open(report_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nMarkdown middleware report written to: {report_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate M3 pre-generation middleware against adversarial test set.")
    parser.add_argument(
        "--test-set",
        type=str,
        default="data/test_set/injection_payloads.jsonl",
        help="Path to injection payloads test set",
    )
    parser.add_argument("--policy", type=str, default="block", choices=["block", "strip", "flag"])
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--no-pii", action="store_true", help="Disable PII scanning for this eval run")
    args = parser.parse_args()

    run_middleware_evaluation(
        test_set_path=args.test_set,
        policy=args.policy,
        threshold=args.threshold,
        pii_enabled=not args.no_pii,
    )
