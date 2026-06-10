# EduGraph-Agent Backend

FastAPI backend for the Neo4j-only GraphRAG MVP.

## Run locally

```cmd
cd /d D:\Code\EduGraph-Agent\backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Neo4j must be running at `bolt://localhost:7687`.

## Optional LangChain resolver

The NodeResolver uses local heuristic fallback by default. To enable LangChain structured-output resolution, set:

```cmd
set LLM_RESOLVER_ENABLED=true
set LLM_PROVIDER=openai
set LLM_MODEL=gpt-4o-mini
set LLM_API_KEY=your_api_key
```

For OpenAI-compatible gateways, also set:

```cmd
set LLM_BASE_URL=https://your-compatible-endpoint/v1
```

## P0 endpoints

- `GET /health`
- `GET /api/graph/node/{uid}`
- `GET /api/graph/subgraph/{uid}`
- `GET /api/graphrag/evidence?uid=ml_kmeans`
- `POST /api/graphrag/query`
