# Crypto Risk Dashboard — Self-Hosted Starter (v2, Timescale-ready)

**What’s inside**
- API: FastAPI
- UI: Streamlit (with automatic API URL detect)
- Worker: scheduled ingest + signal engine
- DB: Postgres schema (Timescale-ready: auto-hypertables + 1h continuous aggregate if extension is available)
- Render Blueprint: `render.yaml` (API + UI + Worker + free Postgres)

**Quick start (Docker Compose, local)**
1) Copy `.env.example` to `.env` and edit as needed. You can set `DATABASE_URL` (preferred) or individual POSTGRES_* vars.
2) `docker compose up --build`
3) UI: http://localhost:8501  |  API: http://localhost:8000

**Render deployment**
- Push to GitHub, then in Render → Blueprints → New from repo.
- Set `API_CANDIDATES` on the UI service (defaults provided in render.yaml). The UI auto-detects API via /health.
- Set `DATABASE_URL` on API + Worker (Render sets it automatically if you bind the included Postgres;
  or paste your Timescale Cloud connection string).

**Security note**
Do NOT commit real secrets (API keys, DB URLs) to Git.
Use Render environment variables or a local `.env` that you do not push.
