# EU AI Act Compliance Assistant

A RAG-powered multi-agent compliance briefing system grounded in EU AI Act source text. Ask any compliance question and receive a structured 3-section briefing with specific article citations.

---

## What it does

- Retrieves relevant EU AI Act provisions using semantic search over 741 embedded chunks
- Analyzes regulatory implications for your specific AI system
- Generates a structured compliance briefing with gap analysis and action items

---

## Example questions

- What are the EU AI Act obligations for a fraud detection system used in credit scoring?
- What are the requirements for high-risk AI systems?
- What transparency obligations exist for AI providers?
- How should training data be prepared under Article 10?

---

## How to run locally

```bash
git clone https://github.com/diyaboop/compliance-assistant.git
cd compliance-assistant
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
python main.py
```

Open `http://localhost:8000` in your browser. On first startup the app ingests the EU AI Act PDF and builds the vector database — this takes 60-90 seconds.

---

## Deploying to Render

This app requires at least 1GB RAM due to the embedding model and vector database. Deploy on Render's Starter tier ($7/month) or higher.

1. Go to render.com → New → Web Service
2. Connect this GitHub repository
3. Add environment variable: `ANTHROPIC_API_KEY`
4. Select Starter instance type (1GB RAM)
5. Deploy

Note: The free tier (512MB) is insufficient for this stack. The sentence-transformers embedding model and ChromaDB together exceed the memory limit.

---

## Tech Stack

Python · FastAPI · LangGraph · ChromaDB · Sentence Transformers · Anthropic Claude · LangChain

---

## Built by

Shrijani (Diya) Manna · Duke MEM '26
github.com/diyaboop · linkedin.com/in/shrijani-manna
