from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pipeline import build_pipeline

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
    result = pipeline.invoke({
        "question": request.question,
        "retrieved_docs": [],
        "analysis": "",
        "briefing": "",
        "current_agent": "research"
        })
    return {
        "briefing": result["briefing"],
        "analysis": result["analysis"]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)