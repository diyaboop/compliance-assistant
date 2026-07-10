"""LLM-judge correctness check: does the generated answer semantically match
the ground-truth reference answer, independent of exact wording?"""

import json
import re

import anthropic

client = anthropic.Anthropic()
JUDGE_MODEL = "claude-sonnet-4-6"

CORRECTNESS_PROMPT = """You are an evaluation judge comparing a generated answer against a reference \
(ground-truth) answer for a compliance question.

Score the GENERATED ANSWER's semantic correctness against the REFERENCE ANSWER \
on a 1-5 scale. Paraphrased-but-correct answers should score well — do not \
penalize different wording, structure, or extra accurate detail. Penalize \
factual contradictions, missing key requirements, or hallucinated information \
not present in the reference.

5 = fully correct, captures all key points of the reference
4 = correct with a minor omission
3 = partially correct, missing an important point
2 = largely incorrect or missing most key points
1 = contradicts the reference or is completely off-topic

QUESTION:
{question}

REFERENCE ANSWER:
{ground_truth_answer}

GENERATED ANSWER:
{answer}

Respond with ONLY a JSON object, no other text, in this exact shape:
{{"score": <1-5 integer>, "rationale": "<one to two sentences>"}}
"""


def _parse_json_response(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"judge did not return JSON: {text!r}")
    return json.loads(match.group(0))

def score_correctness(question: str, answer: str, ground_truth_answer: str) -> dict:
    if not answer or not answer.strip():
        return {"score": 1, "rationale": "no answer was generated"}

    prompt = CORRECTNESS_PROMPT.format(
        question=question,
        ground_truth_answer=ground_truth_answer,
        answer=answer,
    )

    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    raw_text = text_blocks[0] if text_blocks else ""

    try:
        result = _parse_json_response(raw_text)
    except (ValueError, json.JSONDecodeError):
        return {
            "score": None,
            "rationale": f"judge response could not be parsed: {raw_text[:200]}",
        }

    # NEW — coerce whatever the judge returned into a real int, or None
    raw_score = result.get("score")
    try:
        score = int(raw_score) if raw_score is not None else None
    except (ValueError, TypeError):
        score = None

    return {
        "score": score,
        "rationale": result.get("rationale", ""),
    }