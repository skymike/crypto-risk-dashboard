import os
import sys
# Add the common module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))

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