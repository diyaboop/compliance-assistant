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

## Deployment

### Running Locally

```bash
git clone https://github.com/diyaboop/compliance-assistant.git
cd compliance-assistant
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY
docker compose up --build
```

- Uses `Dockerfile` — volume-backed ChromaDB via the `chroma_data` named volume, so ingested documents persist across restarts
- If the volume is empty (first run, or a fresh volume), build the vector store once:
  ```bash
  docker compose exec compliance-assistant python -c "from ingest import build_vectorstore; build_vectorstore()"
  ```
- Requires `.env` with `ANTHROPIC_API_KEY` set. `ENABLE_DEBUG_ROUTES` is optional, defaults to `false`. When `true`, exposes `/debug/insert_chunk` for local testing — see `AGENT_SECURITY_AUDIT.md` Section 5 for why this should never be enabled in a deployed environment.

<details>
<summary>Running without Docker</summary>

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
python main.py
```

</details>

### Production Image

- `Dockerfile.prod` — stateless, bakes in the 741-chunk EU AI Act vector store at build time, debug routes disabled by default
- Verified standalone (`docker run`, no compose, real `ANTHROPIC_API_KEY` passed via `-e`):
  - Healthcheck reports `healthy`
  - Zero volume mounts required
  - `/debug/insert_chunk` correctly returns 404
  - A real question posted to `/query` returned a substantive, correctly-grounded briefing (citing Article 14 human oversight and Article 29 user obligations) — not an error, not empty
- Build: `docker build -f Dockerfile.prod -t compliance-assistant-prod .`
- Run: `docker run -d -p 8000:8000 -e ANTHROPIC_API_KEY=<key> compliance-assistant-prod`

### Cloud Deployment Status

Not currently deployed to a public URL. Three platforms evaluated:

- **Render (free tier):** insufficient memory for ChromaDB + ONNX embedding model footprint (~512MB free-tier ceiling)
- **AWS App Runner:** closed to new customers as of April 30, 2026 ([AWS App Runner availability change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html))
- **AWS ECS Express Mode:** viable, but requires an Application Load Balancer (~$16-25/mo fixed cost even at zero traffic, unless shared across other services) — not justified for a portfolio demo meant to be spun up/torn down

The image itself is confirmed production-ready and portable to any container host supporting standard Docker images and env-var injection (Render paid tier, Fly.io, Google Cloud Run, a raw EC2/VPS instance, etc.) — deployment is blocked on hosting economics, not on the artifact.

---

## CI/CD

GitHub Actions workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

| Job | Trigger | Needs `ANTHROPIC_API_KEY`? |
|---|---|---|
| `smoke-test` | push / PR to `main` | No |
| `docker-build` | push / PR to `main` | No |
| `eval-regression` | manual (`workflow_dispatch`) only | **Yes** |

- **`smoke-test`** — installs `requirements.txt` and imports `main`, `agents`, `ingest`, `guardrails`, so a broken import (e.g. a duplicate function definition, a bad merge) fails CI immediately instead of surfacing at deploy time.
- **`docker-build`** — builds both `Dockerfile` (local-dev) and `Dockerfile.prod` (stateless prod image), then runs the prod image once to confirm the vector store baked in at build time has a non-zero document count. `build_vectorstore()` only calls ChromaDB's local `DefaultEmbeddingFunction` (on-disk ONNX model) — it never calls the Anthropic API, so this job needs no secret and incurs no API cost.
- **`eval-regression`** — runs a 3-case subset of `eval/test_set.py` (one `legitimate`, one `jailbreak`, one `out_of_scope`) chosen to exercise `analysis_agent`'s LLM grounding check (`check_grounding_llm`), since a regression there is the highest-risk failure mode in this pipeline: it's what stops the model from hallucinating on out-of-scope questions or acting on an injected instruction. This job calls Claude directly and only runs when someone manually triggers it from the Actions tab (`Run workflow`), never automatically on push or PR.

### Setting up the `ANTHROPIC_API_KEY` secret

Required only for `eval-regression`. In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**, name `ANTHROPIC_API_KEY`, value = a real Anthropic API key. Without it, `eval-regression` will fail on the first Claude call the moment it's triggered.

---

## Tech Stack

Python · FastAPI · LangGraph · ChromaDB · Sentence Transformers · Anthropic Claude · LangChain

---

## Built by

Shrijani (Diya) Manna · Duke MEM '26
github.com/diyaboop · linkedin.com/in/shrijani-manna
