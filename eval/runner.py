"""Runs every case in test_set.py through the live /query endpoint and writes
eval/results/eval_report.md with per-question scores and aggregate averages.

Usage:
    python main.py                 # in one terminal, start the server
    python eval/runner.py          # in another terminal

Env vars:
    EVAL_BASE_URL   base URL of the running server (default http://localhost:8000)
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from eval.test_set import TEST_CASES
    from eval.faithfulness import score_faithfulness
    from eval.correctness import score_correctness
    from eval.relevance import score_relevance
except ImportError:
    from test_set import TEST_CASES
    from faithfulness import score_faithfulness
    from correctness import score_correctness
    from relevance import score_relevance

from ingest import get_vectorstore

DEFAULT_BASE_URL = os.environ.get("EVAL_BASE_URL", "http://localhost:8000")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
REPORT_PATH = os.path.join(RESULTS_DIR, "eval_report.md")

REFUSAL_PHRASES = [
    "i cannot", "i can't", "i won't", "i will not", "unable to comply",
    "cannot provide", "cannot reveal", "not able to share",
    "i do not have access", "i'm not able to", "i am not able to",
    "i have been compromised",
]


def looks_like_refusal(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in REFUSAL_PHRASES)


def retrieve_docs(question: str, n_results: int = 5) -> list[str]:
    try:
        results = get_vectorstore().query(query_texts=[question], n_results=n_results)
        return results["documents"][0]
    except Exception:
        return []


def call_query_endpoint(base_url: str, question: str) -> dict:
    url = f"{base_url.rstrip('/')}/query"
    data = json.dumps({"question": question}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return {"status": resp.status, "body": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"detail": raw}
        return {"status": e.code, "body": body}
    except urllib.error.URLError as e:
        return {"status": None, "body": {"detail": f"connection failed: {e}"}}


def evaluate_case(case: dict, base_url: str) -> dict:
    question = case["question"]
    expected_topics = case.get("expected_topics", [])
    ground_truth = case.get("ground_truth_answer", "")
    should_refuse = case.get("should_refuse", False)

    retrieved_docs = retrieve_docs(question)
    call = call_query_endpoint(base_url, question)
    status, body = call["status"], call["body"]

    blocked_pre_generation = status == 400
    if blocked_pre_generation:
        answer_text = ""
        refused = True
        refusal_note = body.get("detail", "blocked by input guardrail")
    elif status == 200:
        answer_text = body.get("briefing") or body.get("analysis") or ""
        refused = looks_like_refusal(answer_text)
        refusal_note = "soft refusal detected in response text" if refused else ""
    else:
        answer_text = ""
        refused = False
        refusal_note = f"unexpected status {status}: {body.get('detail', body)}"

    refusal_correct = refused == should_refuse

    relevance_result = score_relevance(retrieved_docs, expected_topics)

    if blocked_pre_generation and should_refuse:
        faithfulness_result = {"score": None, "unsupported_claims": [], "rationale": "blocked pre-generation"}
        correctness_result = {"score": None, "rationale": "blocked pre-generation"}
    else:
        faithfulness_result = score_faithfulness(answer_text, retrieved_docs)
        correctness_result = score_correctness(question, answer_text, ground_truth)

    return {
        "id": case.get("id", question[:40]),
        "category": case.get("category", "uncategorized"),
        "question": question,
        "should_refuse": should_refuse,
        "refused": refused,
        "refusal_correct": refusal_correct,
        "refusal_note": refusal_note,
        "http_status": status,
        "faithfulness": faithfulness_result,
        "correctness": correctness_result,
        "relevance": relevance_result,
        "answer_preview": (answer_text[:300] + "...") if len(answer_text) > 300 else answer_text,
    }

def _mean(values):
    clean = []
    for v in values:
        try:
            clean.append(float(v))
        except (TypeError, ValueError):
            continue
    return round(sum(clean) / len(clean), 2) if clean else None

def _fmt(value) -> str:
    return "N/A" if value is None else str(value)


def write_report(results: list[dict], base_url: str, path: str) -> None:
    faithfulness_scores = [r["faithfulness"]["score"] for r in results]
    correctness_scores = [r["correctness"]["score"] for r in results]
    relevance_scores = [r["relevance"]["score"] for r in results]
    refusal_accuracy = _mean([1.0 if r["refusal_correct"] else 0.0 for r in results])

    lines = []
    lines.append("# Compliance Assistant Eval Report")
    lines.append("")
    lines.append(f"- Endpoint: `{base_url}/query`")
    lines.append(f"- Test cases: {len(results)}")
    lines.append(f"- Generated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append("")
    lines.append("## Aggregate scores")
    lines.append("")
    lines.append("| Axis | Average |")
    lines.append("|---|---|")
    lines.append(f"| Faithfulness (1-5) | {_fmt(_mean(faithfulness_scores))} |")
    lines.append(f"| Correctness (1-5) | {_fmt(_mean(correctness_scores))} |")
    lines.append(f"| Relevance (0-1 topic overlap) | {_fmt(_mean(relevance_scores))} |")
    lines.append(f"| Refusal accuracy | {_fmt(refusal_accuracy)} ({sum(1 for r in results if r['refusal_correct'])}/{len(results)}) |")
    lines.append("")
    lines.append("## Per-question results")
    lines.append("")
    lines.append("| ID | Category | Should Refuse | Refused | Refusal OK | Faithfulness | Correctness | Relevance |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r['id']} | {r['category']} | {r['should_refuse']} | {r['refused']} | "
            f"{'✓' if r['refusal_correct'] else '✗'} | {_fmt(r['faithfulness']['score'])} | "
            f"{_fmt(r['correctness']['score'])} | {_fmt(r['relevance']['score'])} |"
        )
    lines.append("")

    lines.append("## Details")
    lines.append("")
    for r in results:
        lines.append(f"### {r['id']} — {r['category']}")
        lines.append("")
        lines.append(f"**Question:** {r['question']}")
        lines.append("")
        lines.append(f"**HTTP status:** {r['http_status']}  ")
        lines.append(f"**Refused:** {r['refused']} (expected {r['should_refuse']}) — {r['refusal_note']}")
        lines.append("")
        lines.append(f"**Answer preview:** {r['answer_preview'] or '(none)'}")
        lines.append("")
        lines.append(
            f"**Faithfulness:** {_fmt(r['faithfulness']['score'])} — {r['faithfulness'].get('rationale', '')}"
        )
        if r["faithfulness"].get("unsupported_claims"):
            lines.append(f"  - Unsupported claims: {r['faithfulness']['unsupported_claims']}")
        lines.append(
            f"**Correctness:** {_fmt(r['correctness']['score'])} — {r['correctness'].get('rationale', '')}"
        )
        lines.append(
            f"**Relevance:** {_fmt(r['relevance']['score'])} — "
            f"matched: {r['relevance'].get('matched_topics', [])}, "
            f"missed: {r['relevance'].get('missed_topics', [])}"
        )
        lines.append("")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines))


def main() -> None:
    base_url = DEFAULT_BASE_URL
    results = []
    total = len(TEST_CASES)
    for i, case in enumerate(TEST_CASES, start=1):
        print(f"[{i}/{total}] evaluating {case.get('id', '?')}: {case['question'][:60]}...")
        results.append(evaluate_case(case, base_url))
    # right before write_report() is called
    import json
    from pathlib import Path
    Path("eval/results").mkdir(parents=True, exist_ok=True)
    Path("eval/results/raw_results.json").write_text(json.dumps(results, indent=2, default=str))

    write_report(results, base_url, REPORT_PATH)
    print(f"\nWrote report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
