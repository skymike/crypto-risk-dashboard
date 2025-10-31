# Crypto Risk Dashboard — Cloud Deployment

**Deployment**: Railway (API + UI) + GitHub Actions (Worker)

## Quick Deploy with Railway:

### Step 1: Create Railway Project and Database

1. **Sign up/Login to Railway**: Go to [railway.app](https://railway.app) and connect your GitHub account

2. **Create New Project**:
   - Click "New Project"
   - Select "Empty Project"

3. **Add PostgreSQL Database**:
   - Click "+ New" → "Database" → "Add PostgreSQL"
   - Railway will automatically create a PostgreSQL database
   - Note the database - it will be used in the next steps

### Step 2: Deploy API Service

1. **Add API Service**:
   - In your Railway project, click "+ New" → "GitHub Repo"
   - Select this repository
   - Select the repository and connect it

2. **Configure API Service**:
   - In the service settings:
     - **Root Directory**: Leave empty or set to repository root (Railway will auto-detect Dockerfile)
     - Or set **Root Directory**: `services/api` (Railway uses repo root as build context)
     - Railway will automatically detect the Dockerfile in `services/api/Dockerfile`
   
3. **Add Environment Variables**:
   - Click on "Variables" tab
   - Add `DATABASE_URL` → Reference from PostgreSQL service (Railway will auto-generate this)
   - Add `SYMBOLS` → `binance:BTC/USDT,binance:ETH/USDT,bybit:SOL/USDT`
   - Railway will automatically expose the service and generate a URL

4. **Generate Public URL**:
   - In API service settings → "Networking" → "Generate Domain"
   - Note your API URL (e.g., `https://crypto-risk-api-production.up.railway.app`)

### Step 3: Deploy UI Service

1. **Add UI Service**:
   - Click "+ New" → "GitHub Repo" (same repository)
   - Or duplicate the API service and modify settings

2. **Configure UI Service**:
   - **Root Directory**: Leave empty or set to repository root
   - Or set **Root Directory**: `services/ui` (Railway uses repo root as build context)
   - Railway will automatically detect the Dockerfile in `services/ui/Dockerfile`
   
3. **Add Environment Variables**:
   - `API_CANDIDATES` → Your API URL from Step 2 (e.g., `https://crypto-risk-api-production.up.railway.app,http://api:8000,http://localhost:8000`)
   - `DATABASE_URL` → Reference from PostgreSQL service
   
4. **Generate Public URL**:
   - Generate a domain for UI service (e.g., `https://crypto-risk-ui-production.up.railway.app`)

### Step 4: Setup GitHub Actions Worker

1. **Get Database Connection String**:
   - In Railway project → PostgreSQL database → "Variables" tab
   - Copy the `DATABASE_URL` value (format: `postgresql://user:pass@host:port/dbname`)

2. **Configure GitHub Secrets**:
   - Go to your GitHub repository → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Add: `DATABASE_URL` = your Railway PostgreSQL connection string
   - The worker will run automatically every 5 minutes via GitHub Actions

3. **Verify Worker**:
   - Go to Actions tab in GitHub
   - Check "Crypto Data Worker" workflow runs every 5 minutes
   - You can manually trigger it via "workflow_dispatch"

### Step 5: Access Your Dashboard

- **UI**: Your Railway UI service URL
- **API**: Your Railway API service URL
- Both services will auto-deploy on git push to main branch

## Local Development:
```bash
docker compose up --build