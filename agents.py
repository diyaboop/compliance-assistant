import anthropic
from typing import TypedDict, List
from ingest import build_vectorstore

vectorstore = build_vectorstore()
client = anthropic.Anthropic()

class ComplianceState(TypedDict):
    question: str               #the original user question
    retrieved_docs: List[str]   #chunks from ChromaDB
    analysis: str               #compliance analysis
    briefing: str               #final formatted output
    current_agent: str          #which agent is currently working

def research_agent(state: ComplianceState) -> dict:
    user_query = state["question"]
    results = vectorstore.query(
        query_texts=[user_query],
        n_results=5
    )
    retrieved_texts = results["documents"][0]
    return {
        "retrieved_docs": retrieved_texts,
        "current_agent": "analysis"
    }

def analysis_agent(state: ComplianceState) -> dict:
    docs = state["retrieved_docs"]
    user_query = state["question"]
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
            messages=[{"role":"user", "content":prompt}]
        )
    return {
        "analysis": response.content[0].text,
        "current_agent": "writing"
    }

def writing_agent(state: ComplianceState) -> dict:
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
        system="You are an expert compliance analyst. Write concise, professional briefings in markdown.",
        messages=[{"role": "user", "content": prompt}]
    )
    return {
        "briefing": response.content[0].text,
        "current_agent": "done"
    }