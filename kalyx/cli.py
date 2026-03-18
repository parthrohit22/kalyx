import sys
import json
import os
import subprocess
from datetime import datetime

from kalyx.engine.ingest_execsnoop import main as ingest
from kalyx.engine.ingest_execsnoop_live import main as ingest_live
from kalyx.core.verify import verify_ledger


LOG_FILE = "logs/exec_chain.jsonl"


def status():
    print("KALYX Ledger Status")
    print("--------------------")
    print(f"Ledger file      : {LOG_FILE}")

    if not os.path.exists(LOG_FILE):
        print("Entries          : 0")
        print("Last hash        : N/A")
        print("Status           : Ledger not created")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    count = len(lines)
    print(f"Entries          : {count}")

    if count > 0:
        try:
            last_entry = json.loads(lines[-1])
            last_hash = last_entry.get("hash", "N/A")
            print(f"Last hash        : {last_hash[:20]}...")
        except json.JSONDecodeError:
            print("Last hash        : [!] Corrupted entry")
    else:
        print("Last hash        : N/A")

    print("Status           : Run `kalyx verify` to validate integrity")


def inspect():
    print("KALYX Ledger Inspection")
    print("-----------------------")

    if not os.path.exists(LOG_FILE):
        print("[!] No ledger file found")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
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
        print(f"  seq       : {entry.get('seq', 'N/A')}")
        print(f"  ts        : {entry.get('ts', 'N/A')}")
        print(f"  source    : {entry.get('source', 'N/A')}")
        print(f"  comm      : {entry.get('comm', 'N/A')}")
        print(f"  argv      : {entry.get('argv', 'N/A')}")
        print(f"  pid       : {entry.get('pid', 'N/A')}")
        print(f"  ppid      : {entry.get('ppid', 'N/A')}")
        print(f"  ret       : {entry.get('ret', 'N/A')}")
        print(f"  uid       : {entry.get('uid', 'N/A')}")
        print(f"  user      : {entry.get('user', 'N/A')}")
        print(f"  tty       : {entry.get('tty', 'N/A')}")
        print(f"  session   : {entry.get('session', 'N/A')}")
        print(f"  action    : {entry.get('action', 'N/A')}")
        print(f"  target    : {entry.get('target', 'N/A')}")
        print(f"  prev_hash : {entry.get('prev_hash', 'N/A')[:16]}...")
        print(f"  hash      : {entry.get('hash', 'N/A')[:16]}...")
        print()


def export():
    output_file = "reports/ledger_export.json"

    print("KALYX Export")
    print("------------")

    if not os.path.exists(LOG_FILE):
        print("[!] No ledger file found")
        return

    os.makedirs("reports", exist_ok=True)

    records = []

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                records.append(entry)
            except json.JSONDecodeError:
                print(f"[!] Skipping invalid JSON at entry {i}")

    if not records:
        print("[!] No valid records to export")
        return

    verification_result = verify_ledger()

    export_bundle = {
        "exported_at": datetime.utcnow().isoformat(),
        "total_records": len(records),
        "verification": "SUCCESS" if verification_result else "FAILED",
        "records": records
    }

    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(export_bundle, out, indent=4)

    print(f"[+] Exported {len(records)} records")
    print(f"[+] Verification status: {export_bundle['verification']}")
    print(f"[+] Output file: {output_file}")


def audit():
    print("KALYX Audit Trail (Ledger Access)")
    print("---------------------------------")

    try:
        result = subprocess.run(
            ["ausearch", "-k", "kalyx_ledger_watch", "-i"],
            capture_output=True,
            text=True,
            check=True
        )
    except Exception as e:
        print(f"[!] Failed to run ausearch: {e}")
        return

    output = result.stdout.split("----")

    seen = set()
    events = []

    for block in output:
        if not block.strip():
            continue

        lines = block.strip().split("\n")

        time = None
        process = None
        action = None

        for line in lines:
            if "msg=audit(" in line:
                try:
                    raw = line.split("msg=audit(")[1].split(")")[0]
                    parts = raw.rsplit(":", 1)
                    time = parts[0] if len(parts) > 1 else raw
                except:
                    pass

            if "comm=" in line:
                process = line.split("comm=")[-1].split()[0]

            if "nametype=DELETE" in line:
                action = "DELETE"

            if "O_TRUNC" in line:
                action = "WRITE/TRUNCATE"

            if "O_WRONLY" in line and action is None:
                action = "WRITE"

        if not action or not process:
            continue

        if process == "python" and action == "WRITE":
            continue

        key = (time, process, action)
        if key in seen:
            continue
        seen.add(key)

        events.append((time, process, action))

    if not events:
        print("[+] No relevant audit events found")
        return

    for time, process, action in events:
        flag = "[!]" if action in ["DELETE", "WRITE/TRUNCATE", "WRITE"] else "[+]"

        print(f"{flag} {action} detected")
        print(f"  time    : {time}")
        print(f"  process : {process}")
        print(f"  action  : {action}")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: kalyx [ingest|ingest-live|verify|status|inspect|export|audit|detect] [--format json]")
        return

    cmd = sys.argv[1]

    output_format = "text"
    if "--format" in sys.argv:
        try:
            idx = sys.argv.index("--format")
            output_format = sys.argv[idx + 1]
        except:
            print("[ERROR] Invalid format flag")
            return

    if cmd == "ingest":
        ingest()

    elif cmd == "ingest-live":
        ingest_live()

    elif cmd == "verify":
        verify_ledger(output_format=output_format)

    elif cmd == "status":
        status()

    elif cmd == "inspect":
        inspect()

    elif cmd == "export":
        export()

    elif cmd == "audit":
        audit()

    elif cmd == "detect":
        from kalyx.core.detector import load_events, detect_suspicious

        events = load_events()
        alerts = detect_suspicious(events)

        if not alerts:
            print("[+] No suspicious patterns detected")
        else:
            print("[!] Suspicious activity detected")
            for a in alerts:
                print(f"  type    : {a['type']}")
                print(f"  user    : {a.get('user', 'N/A')}")
                print(f"  details : {a.get('details', a.get('command', 'N/A'))}")
                print()

    else:
        print("Unknown command")

if __name__ == "__main__":
    main()