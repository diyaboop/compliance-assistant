"""Keyword-overlap relevance check: do the retrieved chunks actually contain the
concepts a correct answer should touch on? No LLM judge needed here."""


def score_relevance(retrieved_docs: list[str], expected_topics: list[str]) -> dict:
    if not expected_topics:
        return {"score": None, "matched_topics": [], "missed_topics": []}

    combined = " ".join(retrieved_docs).lower()

    matched = [topic for topic in expected_topics if topic.lower() in combined]
    missed = [topic for topic in expected_topics if topic.lower() not in combined]

    return {
        "score": round(len(matched) / len(expected_topics), 2),
        "matched_topics": matched,
        "missed_topics": missed,
    }
