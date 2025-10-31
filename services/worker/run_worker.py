import os
import sys
from pathlib import Path

# Add the repo root to path so services.common can be imported
# This file is at services/worker/run_worker.py
# So we need to go up 2 levels to get to repo root
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

# Debug: Verify the path is correct
print(f"[DEBUG] Repo root: {repo_root}", file=sys.stderr)
print(f"[DEBUG] Services path exists: {(repo_root / 'services').exists()}", file=sys.stderr)
print(f"[DEBUG] Services/common path exists: {(repo_root / 'services' / 'common').exists()}", file=sys.stderr)

# Ensure services package can be imported
# Import services first to make sure the package is recognized
import services
import services.common

# Now import the specific modules we need
from services.common.db import ensure_schema
from services.common.ingest import run_ingest_cycle
from services.common.signals import compute_all_signals

def main():
    print("[worker] Starting worker cycle...")
    ensure_schema()
    print("[worker] Running ingest cycle...")
    run_ingest_cycle()
    print("[worker] Computing signals...")
    compute_all_signals()
    print("[worker] Worker cycle completed successfully!")

if __name__ == "__main__":
    main()