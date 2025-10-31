import os, time
from services_common.db import ensure_schema
from services_common.ingest import run_ingest_cycle
from services_common.signals import compute_all_signals

def main():
    ensure_schema()
    interval = int(os.getenv("SCHEDULE_MINUTES","5"))
    print(f"[worker] schedule {interval}m")
    while True:
        print("[worker] ingest..."); run_ingest_cycle()
        print("[worker] signals..."); compute_all_signals()
        print("[worker] sleep..."); time.sleep(interval*60)

if __name__ == "__main__":
    main()
