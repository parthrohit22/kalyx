import sys
import json
import os

from kalyx.engine.ingest_execsnoop import main as ingest
from kalyx.core.verify import verify_chain


def status():
    log_file = "logs/exec_chain.jsonl"
    status_file = "logs/.kalyx_status.json"

    print("KALYX Ledger Status")
    print("--------------------")
    print(f"Ledger file      : {log_file}")

    if not os.path.exists(log_file):
        print("Entries          : 0")
        print("Last hash        : N/A")
        print("Last verified    : NO_LEDGER")
        print("Timestamp        : N/A")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    count = len(lines)
    print(f"Entries          : {count}")

    if count > 0:
        last_entry = json.loads(lines[-1])
        last_hash = last_entry.get("hash", "N/A")
        print(f"Last hash        : {last_hash[:20]}...")
    else:
        print("Last hash        : N/A")

    if os.path.exists(status_file):
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"Last verified    : {data.get('last_verified', 'N/A')}")
        print(f"Timestamp        : {data.get('timestamp', 'N/A')}")

        failure_index = data.get("failure_index")
        if failure_index is not None:
            print(f"Failure at entry : {failure_index}")
    else:
        print("Last verified    : Not yet verified")
        print("Timestamp        : N/A")

def inspect():
    log_file = "logs/exec_chain.jsonl"

    print("KALYX Ledger Inspection")
    print("-----------------------")

    if not os.path.exists(log_file):
        print("[!] No ledger file found")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("[!] Ledger is empty")
        return

    for i, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            print(f"[!] Invalid JSON at entry {i}")
            continue

        print(f"Entry {i}")
        print(f"  comm      : {entry.get('comm', 'N/A')}")
        print(f"  argv      : {entry.get('argv', 'N/A')}")
        print(f"  pid       : {entry.get('pid', 'N/A')}")
        print(f"  ppid      : {entry.get('ppid', 'N/A')}")
        print(f"  ret       : {entry.get('ret', 'N/A')}")
        print(f"  prev_hash : {entry.get('prev_hash', 'N/A')[:16]}...")
        print(f"  hash      : {entry.get('hash', 'N/A')[:16]}...")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: kalyx [ingest|verify|status|inspect]")
        return

    if sys.argv[1] == "ingest":
        ingest()
    elif sys.argv[1] == "verify":
        verify_chain()
    elif sys.argv[1] == "status":
        status()
    elif sys.argv[1] == "inspect":
        inspect()
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
