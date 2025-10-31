# Crypto Risk Dashboard — Self-Hosted Starter

Self-hosted, Dockerized stack with:
- **API** (FastAPI)
- **Worker** (scheduled ingest + signals)
- **DB** (Postgres; Timescale-ready)
- **UI** (Streamlit) with graphs, meters, hot signals
- **Adapters** for candles, funding, OI, sentiment, headlines (mock by default)

## Quick start (local Docker)
1) `cp .env.example .env`
2) `docker compose up --build`
3) UI: http://localhost:8501, API: http://localhost:8000

## Render deploy
Use the `render.yaml` blueprint (free Postgres + API + UI + worker).
