# Crypto Risk Dashboard — Free Cloud Deployment

**Deployment**: Render (API + UI) + GitHub Actions (Worker)

## Quick Deploy:

1. **Deploy to Render**:
   - Connect your GitHub repo to Render
   - Use the `render.yaml` blueprint
   - Render will automatically create API, UI, and PostgreSQL

2. **Setup GitHub Actions Worker**:
   - Get `DATABASE_URL` from Render dashboard
   - Add to GitHub Secrets: `DATABASE_URL = your_render_postgres_url`
   - Push the code - worker runs automatically every 5 minutes

3. **Access Your Dashboard**:
   - UI: `https://crypto-risk-ui.onrender.com`
   - API: `https://crypto-risk-api.onrender.com`

## Local Development:
```bash
docker compose up --build