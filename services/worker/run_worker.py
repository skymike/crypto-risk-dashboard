import os
import sys
from pathlib import Path

# Add the repo root to path so services_common imports work
# This file is at services/worker/run_worker.py
# So we need to go up 2 levels to get to repo root
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

# Import the services_common namespace package FIRST
# This must be imported before any services_common.* imports
import services_common

# Now we can import from services_common
from services_common.db import ensure_schema
from services_common.ingest import run_ingest_cycle
from services_common.signals import compute_all_signals

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