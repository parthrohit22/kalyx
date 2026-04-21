"""Command-line interface for KALYX."""

from __future__ import annotations

import json
import subprocess
import sys

from kalyx.services import (
    detect_and_persist_alerts,
    export_ledger_bundle,
    get_status_summary,
    ingest_execsnoop_file,
    ingest_live_stream,
    load_alerts,
    load_ledger_records,
    verify_ledger_state,
)


def status() -> None:
    """Print current ledger status."""

    summary = get_status_summary()
    print("KALYX Ledger Status")
    print("--------------------")
    print(f"Ledger file      : {summary['ledger_file']}")
    print(f"Entries          : {summary['entries']}")
    if summary["last_hash"]:
        print(f"Last hash        : {summary['last_hash'][:20]}...")
    else:
        print("Last hash        : N/A")
    print(f"Status           : {summary['verification_status'] or 'Run `kalyx verify` to validate integrity'}")


def inspect() -> None:
    """Print ledger entries in a readable format."""

    print("KALYX Ledger Inspection")
    print("-----------------------")
    records = load_ledger_records()
    if not records:
        print("[!] No ledger file found")
        return

    for index, entry in enumerate(records, start=1):
        print(f"Entry {index}")
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
        print(f"  parent_comm: {entry.get('parent_comm', 'N/A')}")
        print(f"  parent_exe : {entry.get('parent_exe', 'N/A')}")
        print(f"  action    : {entry.get('action', 'N/A')}")
        print(f"  target    : {entry.get('target', 'N/A')}")
        print(f"  prev_hash : {entry.get('prev_hash', 'N/A')[:16]}...")
        print(f"  hash      : {entry.get('hash', 'N/A')[:16]}...")
        print()


def export() -> None:
    """Export the ledger and verification state."""

    print("KALYX Export")
    print("------------")
    bundle = export_ledger_bundle()
    if bundle is None:
        print("[!] No valid records to export")
        return
    print(f"[+] Exported {bundle['total_records']} records")
    print(f"[+] Verification status: {bundle['verification']}")
    print("[+] Output file: reports/ledger_export.json")


def audit() -> None:
    """Display auditd access events for the ledger."""

    print("KALYX Audit Trail (Ledger Access)")
    print("---------------------------------")
    try:
        result = subprocess.run(
            ["ausearch", "-k", "kalyx_ledger_watch", "-i"],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as exc:
        print(f"[!] Failed to run ausearch: {exc}")
        return

    output = result.stdout.split("----")
    seen: set[tuple[str | None, str | None, str | None]] = set()
    events: list[tuple[str | None, str | None, str | None]] = []

    for block in output:
        if not block.strip():
            continue
        lines = block.strip().split("\n")
        event_time = None
        process = None
        action = None

        for line in lines:
            if "msg=audit(" in line:
                try:
                    raw = line.split("msg=audit(")[1].split(")")[0]
                    parts = raw.rsplit(":", 1)
                    event_time = parts[0] if len(parts) > 1 else raw
                except Exception:
                    event_time = None
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

        key = (event_time, process, action)
        if key in seen:
            continue
        seen.add(key)
        events.append(key)

    if not events:
        print("[+] No relevant audit events found")
        return

    for event_time, process, action in events:
        flag = "[!]" if action in ["DELETE", "WRITE/TRUNCATE", "WRITE"] else "[+]"
        print(f"{flag} {action} detected")
        print(f"  time    : {event_time}")
        print(f"  process : {process}")
        print(f"  action  : {action}")
        print()


def show_alerts() -> None:
    """Print persisted alerts."""

    print("KALYX Alert Log")
    print("----------------")
    alerts = load_alerts()
    if not alerts:
        print("[+] No persisted alerts")
        return

    for index, alert in enumerate(alerts, start=1):
        print(f"Alert {index}")
        print(f"  type         : {alert.get('type', 'N/A')}")
        print(f"  severity     : {alert.get('severity', 'N/A')}")
        print(f"  user         : {alert.get('user', 'N/A')}")
        print(f"  target       : {alert.get('target', 'N/A')}")
        print(f"  session      : {alert.get('session', 'N/A')}")
        print(f"  seq_start    : {alert.get('seq_start', 'N/A')}")
        print(f"  seq_end      : {alert.get('seq_end', 'N/A')}")
        print(f"  ts_start     : {alert.get('ts_start', 'N/A')}")
        print(f"  ts_end       : {alert.get('ts_end', 'N/A')}")
        print(f"  delta_sec    : {alert.get('delta_seconds', 'N/A')}")
        print(f"  details      : {alert.get('details', 'N/A')}")
        print()


def print_verify_result(result: dict[str, object], output_format: str) -> None:
    """Render verification output in text or JSON format."""

    if output_format == "json":
        print(json.dumps(result, indent=2))
        return
    if result["status"] == "VALID":
        print("[OK]    Ledger verified")
    elif result["status"] == "TAMPERED":
        print("[ERROR] Ledger tampered")
        if result["reason"]:
            print(f"[ERROR] Reason: {result['reason']}")
        if result["entry"]:
            print(f"[ERROR] Entry: {result['entry']}")
    elif result["status"] == "EMPTY":
        print("[ERROR] Ledger empty")
    elif result["status"] == "NO_LEDGER":
        print("[ERROR] Ledger not found")


def main() -> None:
    """Dispatch CLI commands."""

    if len(sys.argv) < 2:
        print("Usage: kalyx [ingest|ingest-live|verify|status|inspect|export|audit|detect|alerts] [--format json]")
        return

    cmd = sys.argv[1]
    output_format = "text"
    if "--format" in sys.argv:
        try:
            idx = sys.argv.index("--format")
            output_format = sys.argv[idx + 1]
        except Exception:
            print("[ERROR] Invalid format flag")
            return

    if cmd == "ingest":
        count = ingest_execsnoop_file()
        if count > 0:
            print(f"[+] Ingested {count} events")
            print("[+] Ledger updated")
        else:
            print("[!] No valid events found")
    elif cmd == "ingest-live":
        try:
            print("[INFO] Starting live eBPF ingestion from execsnoop")
            print("[INFO] Press Ctrl+C to stop")
            result = ingest_live_stream()
            print(f"[INFO] Ingested {result['ingested']} live events")
            print(f"[INFO] Skipped {result['skipped']} background/noise events")
        except FileNotFoundError as exc:
            print(f"[ERROR] {exc}")
        except RuntimeError as exc:
            print(f"[ERROR] {exc}")
        except KeyboardInterrupt:
            print("\n[INFO] Live ingestion stopped")
    elif cmd == "verify":
        print_verify_result(verify_ledger_state(), output_format=output_format)
    elif cmd == "status":
        status()
    elif cmd == "inspect":
        inspect()
    elif cmd == "export":
        export()
    elif cmd == "audit":
        audit()
    elif cmd == "detect":
        result = detect_and_persist_alerts()
        alerts = result["alerts"]
        if not alerts:
            print("[+] No suspicious patterns detected")
            return
        print("[!] Suspicious activity detected")
        print()
        for alert in alerts:
            print(f"  type         : {alert.get('type', 'N/A')}")
            print(f"  severity     : {alert.get('severity', 'N/A')}")
            print(f"  user         : {alert.get('user', 'N/A')}")
            print(f"  target       : {alert.get('target', 'N/A')}")
            print(f"  session      : {alert.get('session', 'N/A')}")
            print(f"  seq_start    : {alert.get('seq_start', 'N/A')}")
            print(f"  seq_end      : {alert.get('seq_end', 'N/A')}")
            print(f"  ts_start     : {alert.get('ts_start', 'N/A')}")
            print(f"  ts_end       : {alert.get('ts_end', 'N/A')}")
            print(f"  delta_sec    : {alert.get('delta_seconds', 'N/A')}")
            print(f"  details      : {alert.get('details', 'N/A')}")
            print()
        print(f"[+] Persisted {result['written']} new alert(s)")
    elif cmd == "alerts":
        show_alerts()
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
