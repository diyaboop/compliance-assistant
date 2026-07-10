from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pipeline import build_pipeline # type: ignore
import os
import chromadb
from fastapi import HTTPException
from pydantic import BaseModel
from ingest import chroma_client, collection # type: ignore
from guardrails import validate_input, validate_output, log_audit_event

pipeline = build_pipeline()
app = FastAPI()

class QueryRequest(BaseModel):
    question : str

# serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

#serve the homepage
@app.get("/")
async def home():
    return FileResponse("static/index.html")

#query endpoint (tajes question, return briefing)
@app.post("/query")
async def query(request: QueryRequest):
    input_valid, input_reason = validate_input(request.question)
    if not input_valid:
        log_audit_event(
            question=request.question,
            input_valid=False,
            input_reason=input_reason,
        )
        raise HTTPException(status_code=400, detail=input_reason)

    result = pipeline.invoke({
        "question": request.question,
        "retrieved_docs": [],
        "analysis": "",
        "briefing": "",
        "current_agent": "research"
        })

    analysis_safe, analysis_text, analysis_reason = validate_output(result["analysis"])
    briefing_safe, briefing_text, briefing_reason = validate_output(result["briefing"])

    output_valid = analysis_safe and briefing_safe
    output_reason = analysis_reason if not analysis_safe else briefing_reason

    log_audit_event(
        question=request.question,
        input_valid=True,
        input_reason=input_reason,
        output_valid=output_valid,
        output_reason=output_reason,
    )

    return {
        "briefing": briefing_text,
        "analysis": analysis_text
        }

DEBUG_ROUTES_ENABLED = os.environ.get("ENABLE_DEBUG_ROUTES", "false").lower() == "true"

class InsertChunkRequest(BaseModel):
    text: str
    source: str = "manual_insert"

@app.post("/debug/insert_chunk")
def insert_chunk(req: InsertChunkRequest):
    if not DEBUG_ROUTES_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")

    # use your existing direct ChromaDB client — adjust variable name to match yours
    collection.add(
        documents=[req.text],
        metadatas=[{"source": req.source, "injected_by": "red_team_probe"}],
        ids=[f"red_team_{os.urandom(4).hex()}"],
    )
    return {"status": "inserted", "source": req.source}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)