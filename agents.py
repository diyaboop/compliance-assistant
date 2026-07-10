import anthropic
from typing import TypedDict, List
from ingest import get_vectorstore

vectorstore = get_vectorstore()
client = anthropic.Anthropic()

SYSTEM_PROMPT = "You are an expert compliance analyst. Write concise, professional briefings in markdown."

class ComplianceState(TypedDict):
    question: str                    # the original user question
    retrieved_docs: List[str]        # chunks from ChromaDB
    analysis: str                    # compliance analysis
    briefing: str                    # final formatted output
    current_agent: str               # which agent is currently working
    retrieved_distances: List[float]
    grounding_status: str            # 'grounded' or 'ambiguous'


def research_agent(state: ComplianceState) -> dict:
    user_query = state["question"]
    results = vectorstore.query(
        query_texts=[user_query],
        n_results=5,
        include=["documents", "distances"]
    )
    retrieved_texts = results["documents"][0]
    distances = results["distances"][0]

    return {
        "retrieved_docs": retrieved_texts,
        "retrieved_distances": distances,
        "current_agent": "analysis"
    }

GROUNDING_JUDGE_PROMPT = """You are checking whether a question can be answered using ONLY the provided document excerpts — no outside knowledge.

DOCUMENT EXCERPTS:
{docs}

QUESTION:
{question}

Can this question be answered accurately using ONLY the content in these excerpts? \
Answer "yes" if the excerpts contain enough relevant information to construct a real \
answer, even if not perfectly complete. Answer "no" if the excerpts are unrelated to \
the question's actual subject matter, or if answering would require significant \
outside knowledge not present in these excerpts.

Respond with ONLY a JSON object: {{"grounded": true or false, "reason": "<one sentence>"}}
"""

def check_grounding_llm(question: str, docs: list[str]) -> dict:
    import json, re
    doc_text = "\n\n---\n\n".join(docs[:5])
    prompt = GROUNDING_JUDGE_PROMPT.format(docs=doc_text, question=question)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    raw = text_blocks[0] if text_blocks else ""

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"grounded": False, "reason": "grounding judge response unparseable, defaulting to ambiguous"}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"grounded": False, "reason": "grounding judge response unparseable, defaulting to ambiguous"}

def analysis_agent(state: ComplianceState) -> dict:
    docs = state["retrieved_docs"]
    user_query = state["question"]

    grounding_result = check_grounding_llm(user_query, docs)

    if not grounding_result.get("grounded", False):
        return {
            "analysis": (
                "I found some potentially related content, but I'm not confident "
                "it directly addresses your question. Could you clarify what "
                "aspect of AI system compliance you're asking about — for example, "
                "which regulatory framework, or what type of AI system? This helps "
                "me confirm I'm answering with content actually grounded in the "
                "indexed regulatory text."
            ),
            "grounding_status": "ambiguous",
            "current_agent": "writing"
        }

    # existing analysis logic, unchanged
    prompt = f"""..."""
    ...

    prompt = f"""
    You are an expert compliance officer. Analyze the compliance and regulatory risks 
    based on the provided context and user question.
    
    Context: {docs}
    User Question: {user_query}
    
    Provide a concise compliance analysis:
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    if not response.content:
        analysis_text = "[No content returned by model — possible refusal or empty response]"
    else:
        text_blocks = [block.text for block in response.content if hasattr(block, "text")]
        analysis_text = text_blocks[0] if text_blocks else "[Response contained no text block]"

    return {
        "analysis": analysis_text,
        "grounding_status": "grounded",
        "current_agent": "writing"
    }


def writing_agent(state: ComplianceState) -> dict:
    if state.get("grounding_status") == "ambiguous":
        # pass through the clarification message as-is, no second API call
        return {"briefing": state["analysis"], "current_agent": "done"}

    docs = state["retrieved_docs"]
    user_query = state["question"]
    analysis = state["analysis"]

    prompt = f"""
    Based on the following materials, please generate a 3-section briefing:
    
    ORIGINAL QUESTION:
    {user_query}
    
    ANALYSIS:
    {analysis}
    
    SUPPORTING DOCUMENTS:
    {chr(10).join(docs)}

    Structure exactly as:
    ## Section 1 — Relevant Regulations
    ## Section 2 — Compliance Gap Analysis
    ## Section 3 — Action Items
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    if not response.content:
        briefing_text = "[No content returned by model — possible refusal or empty response]"
    else:
        text_blocks = [block.text for block in response.content if hasattr(block, "text")]
        briefing_text = text_blocks[0] if text_blocks else "[Response contained no text block]"

    return {
        "briefing": briefing_text,
        "current_agent": "done"
    }# docker rebuild test Fri Jul 10 14:35:19 EDT 2026
