import sys
import json
import os

from kalyx.engine.ingest_execsnoop import main as ingest
from kalyx.core.verify import verify_chain


def status():
    log_file = "logs/exec_chain.jsonl"

    print("KALYX Ledger Status")
    print("--------------------")
    print(f"Ledger file      : {log_file}")

    if not os.path.exists(log_file):
        print("Entries          : 0")
        print("Last hash        : N/A")
        print("Status           : Ledger not created")
        return

    with open(log_file) as f:
        lines = f.readlines()

    count = len(lines)
    print(f"Entries          : {count}")

    if count > 0:
        last_entry = json.loads(lines[-1])
        last_hash = last_entry.get("hash", "N/A")
        print(f"Last hash        : {last_hash[:20]}...")
    else:
        print("Last hash        : N/A")

    print("Status           : Run `kalyx verify` to validate integrity")


def main():
    if len(sys.argv) < 2:
        print("Usage: kalyx [ingest|verify|status]")
        return

    if sys.argv[1] == "ingest":
        ingest()
    elif sys.argv[1] == "verify":
        verify_chain()
    elif sys.argv[1] == "status":
        status()
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
