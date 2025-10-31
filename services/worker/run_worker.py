import os, time
from services_common.db import ensure_schema
from services_common.ingest import run_ingest_cycle
from services_common.signals import compute_all_signals
from services_common.config import load_config

def main():
    ensure_schema()
    interval = int(os.getenv("SCHEDULE_MINUTES", "5"))
    print(f"[worker] schedule every {interval} minutes.")
    while True:
        print("[worker] ingest cycle...")
        run_ingest_cycle()
        print("[worker] compute signals...")
        compute_all_signals()
        print("[worker] sleep...")
        time.sleep(60 * interval)

if __name__ == "__main__":
    main()
