# Dockerfile: LOCAL DEV ONLY.
# Requires the docker-compose volume mount for chroma_data (see docker-compose.yml).
# Do NOT deploy this to AWS App Runner or any other stateless platform — with no
# mounted volume, ChromaDB starts empty and stays empty, since this image has no
# build-time ingestion step. Use Dockerfile.prod for stateless/production deploys.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
