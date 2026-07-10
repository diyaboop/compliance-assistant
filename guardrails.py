import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from agents import SYSTEM_PROMPT
except ImportError:
    SYSTEM_PROMPT = "You are an expert compliance analyst. Write concise, professional briefings in markdown."

MAX_QUESTION_LENGTH = 2000

# Prompt-injection patterns, checked individually so any one match rejects the input.
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"),  # base64-looking string over 40 chars
]

# Basic PII patterns.
PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN: 123-45-6789
    re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),  # 16-digit credit card
]

# Fragments checked for system-prompt leakage in model output.
SYSTEM_PROMPT_LEAK_FRAGMENTS = [
    SYSTEM_PROMPT,
    "expert compliance analyst",
    "concise, professional briefings",
]

FALLBACK_EMPTY_MESSAGE = (
    "I wasn't able to generate a response for this request. "
    "Please try rephrasing your question or try again shortly."
)
FALLBACK_LEAK_MESSAGE = (
    "This response was withheld by a safety check. Please rephrase your question."
)

AUDIT_LOG_PATH = os.path.join("logs", "audit.jsonl")


def validate_input(question: str) -> tuple[bool, str]:
    if question is None or not question.strip():
        return False, "Question must not be empty."

    if len(question) > MAX_QUESTION_LENGTH:
        return False, f"Question exceeds the {MAX_QUESTION_LENGTH} character limit."

    for pattern in INJECTION_PATTERNS:
        if pattern.search(question):
            return False, "Question contains a disallowed prompt-injection pattern."

    for pattern in PII_PATTERNS:
        if pattern.search(question):
            return False, "Question appears to contain PII (SSN or credit card number)."

    return True, "OK"


def _extract_text(response_content: Any) -> Optional[str]:
    if response_content is None:
        return None

    if isinstance(response_content, str):
        return response_content.strip() or None

    # anthropic Message-like object
    blocks = getattr(response_content, "content", response_content)

    if not blocks or not isinstance(blocks, list):
        return None

    text_blocks = [block.text for block in blocks if hasattr(block, "text")]
    return text_blocks[0] if text_blocks else None


def validate_output(response_content: Any) -> tuple[bool, str, str]:
    text = _extract_text(response_content)

    if not text:
        return False, FALLBACK_EMPTY_MESSAGE, "empty_or_no_text_blocks"

    lowered = text.lower()
    for fragment in SYSTEM_PROMPT_LEAK_FRAGMENTS:
        if fragment.lower() in lowered:
            return False, FALLBACK_LEAK_MESSAGE, "system_prompt_leak_detected"

    return True, text, "OK"


def _question_preview(question: str, input_valid: bool, input_reason: str, max_len: int = 100) -> str:
    if not question:
        return ""

    if not input_valid and "PII" in input_reason:
        return "[REDACTED - PII pattern detected]"

    preview = question.strip()[:max_len]
    if len(question) > max_len:
        preview += "..."
    return preview


def log_audit_event(
    question: str,
    input_valid: bool,
    input_reason: str,
    output_valid: Optional[bool] = None,
    output_reason: Optional[str] = None,
) -> None:
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question_preview": _question_preview(question, input_valid, input_reason),
        "input_valid": input_valid,
        "input_reason": input_reason,
        "output_valid": output_valid,
        "output_reason": output_reason,
    }

    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
