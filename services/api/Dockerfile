FROM python:3.11-slim
WORKDIR /app

# Copy common module (services_common needs this)
# Note: Railway uses repo root as build context when Root Directory is set
COPY services/common /app/services/common

# Copy API service files
COPY services/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/api /app

# Use PORT env var (Railway) or default to 8000
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
