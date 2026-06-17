"""Command-line interface for KALYX."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any
from urllib import error

from kalyx.services import (
    LedgerNotTrustedError,
    compare_anchor_status,
    create_checkpoint,
    detect_and_persist_alerts,
    export_ledger_bundle,
    get_status_summary,
    ingest_execsnoop_file,
    ingest_live_stream,
    load_alerts,
    load_ledger_records,
    post_anchor_payload as _post_anchor_payload,
    verify_ledger_state,
)


HELP_TEXT = """KALYX CLI

Usage:
  kalyx ingest
  kalyx ingest-live
  kalyx verify [--format json]
  kalyx status
  kalyx checkpoint [--format json]
  kalyx anchor [--anchor-url URL] [--ledger-id ID]
  kalyx anchor-status [--anchor-url URL] [--ledger-id ID]
  kalyx inspect
  kalyx export
  kalyx audit
  kalyx detect
  kalyx alerts
  kalyx --help
"""


DEFAULT_ANCHOR_URL = "http://127.0.0.1:8081"
DEFAULT_LEDGER_ID = "kalyx-main-host"
ANCHOR_REQUIRED_FIELDS = (
    "checkpoint_index",
    "record_count",
    "last_seq",
    "last_hash",
    "previous_checkpoint_hash",
    "checkpoint_hash",
)


def print_help() -> None:
    """Print CLI usage help."""
    print(HELP_TEXT)


def status() -> None:
    """Print current ledger status."""
    summary = get_status_summary()

    print("KALYX Ledger Status")
    print("--------------------")
    print(f"Ledger file      : {summary['ledger_file']}")
    print(f"Entries          : {summary['entries']}")

    last_hash = summary.get("last_hash")
    print(f"Last hash        : {last_hash[:20]}..." if last_hash else "Last hash        : N/A")

    print(f"Verification     : {summary.get('verification_status')}")
    print(f"Trust state      : {summary.get('trust_state')}")
    print(f"Valid            : {summary.get('verification_valid')}")
    print(f"Failure reason   : {summary.get('failure_reason')}")
    print(f"Failure index    : {summary.get('failure_index')}")
    print(f"Valid until      : {summary.get('valid_until_index')}")
    print(f"Checkpoint state : {summary.get('checkpoint_state')}")
    print(f"Checkpoint reason: {summary.get('checkpoint_reason')}")
    print(f"Checkpoint count : {summary.get('checkpoint_record_count')}")

    checkpoint_hash = summary.get("checkpoint_last_hash")
    print(
        f"Checkpoint hash  : {checkpoint_hash[:20]}..."
        if checkpoint_hash
        else "Checkpoint hash  : N/A"
    )


def checkpoint(output_format: str = "text") -> None:
    """Create a local checkpoint for the current trusted ledger state."""
    verification = verify_ledger_state()
    checkpoint_record = create_checkpoint(verification=verification)
    payload = {
        "verification": verification,
        "checkpoint": checkpoint_record,
    }

    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("KALYX Local Checkpoint")
    print("----------------------")

    if not verification.get("valid"):
        print("[ERROR] Ledger is not trusted; checkpoint skipped")
        print(f"[ERROR] Verification status: {verification.get('status')}")
        print(f"[ERROR] Reason: {verification.get('reason')}")
        raise SystemExit(1)

    if checkpoint_record is None:
        print("[ERROR] No checkpoint was written")
        raise SystemExit(1)

    if checkpoint_record.get("written"):
        print("[OK] Checkpoint written")
    else:
        print("[INFO] Checkpoint not written")
        print(f"[INFO] Reason: {checkpoint_record.get('reason')}")

    print(f"Checkpoint index : {checkpoint_record.get('checkpoint_index')}")
    print(f"Record count     : {checkpoint_record.get('record_count')}")
    print(f"Last seq         : {checkpoint_record.get('last_seq')}")
    print(f"Last hash        : {checkpoint_record.get('last_hash')}")
    print(f"Checkpoint hash  : {checkpoint_record.get('checkpoint_hash')}")

    if checkpoint_record.get("reason") not in {None, "CHECKPOINT_ALREADY_CURRENT"}:
        raise SystemExit(1)


def _parse_option(args: list[str], name: str, default: str) -> str:
    """Parse a simple string option from CLI args."""
    if name not in args:
        return default

    index = args.index(name)
    try:
        value = args[index + 1]
    except IndexError as exc:
        raise ValueError(f"Missing value for {name}") from exc

    if not value.strip():
        raise ValueError(f"Missing value for {name}")

    return value.strip()


def _build_anchor_payload(
    checkpoint_record: dict[str, Any],
    ledger_id: str,
) -> dict[str, Any]:
    """Build the Phase 2 host-to-anchor payload from an existing checkpoint."""
    missing = [field for field in ANCHOR_REQUIRED_FIELDS if field not in checkpoint_record]
    if missing:
        raise ValueError(f"Checkpoint missing anchor field(s): {', '.join(missing)}")

    return {
        "ledger_id": ledger_id,
        "checkpoint_index": checkpoint_record["checkpoint_index"],
        "record_count": checkpoint_record["record_count"],
        "last_seq": checkpoint_record["last_seq"],
        "last_hash": checkpoint_record["last_hash"],
        "previous_checkpoint_hash": checkpoint_record["previous_checkpoint_hash"],
        "checkpoint_hash": checkpoint_record["checkpoint_hash"],
    }


def anchor(args: list[str]) -> None:
    """Create or reuse a local checkpoint and send it to the external anchor."""
    anchor_url = _parse_option(
        args,
        "--anchor-url",
        os.getenv("KALYX_ANCHOR_URL", DEFAULT_ANCHOR_URL),
    )
    ledger_id = _parse_option(
        args,
        "--ledger-id",
        os.getenv("KALYX_LEDGER_ID", DEFAULT_LEDGER_ID),
    )

    verification = verify_ledger_state()
    checkpoint_record = create_checkpoint(verification=verification)

    print("KALYX External Anchor")
    print("---------------------")

    if not verification.get("valid"):
        print("[ERROR] Ledger is not trusted; anchor skipped")
        print(f"[ERROR] Verification status: {verification.get('status')}")
        print(f"[ERROR] Reason: {verification.get('reason')}")
        raise SystemExit(1)

    if checkpoint_record is None:
        print("[ERROR] No checkpoint available to anchor")
        raise SystemExit(1)

    if checkpoint_record.get("reason") not in {None, "CHECKPOINT_ALREADY_CURRENT"}:
        print("[ERROR] Checkpoint is not anchorable")
        print(f"[ERROR] Reason: {checkpoint_record.get('reason')}")
        raise SystemExit(1)

    payload = _build_anchor_payload(checkpoint_record, ledger_id)

    try:
        result = _post_anchor_payload(payload, anchor_url)
    except (OSError, error.URLError) as exc:
        print(f"[ERROR] Anchor service unreachable: {exc}")
        raise SystemExit(1) from exc
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"[ERROR] Anchor service returned an invalid response: {exc}")
        raise SystemExit(1) from exc

    status_value = result.get("status")
    if status_value not in {"ACCEPTED", "ALREADY_ANCHORED"}:
        print(f"[ERROR] Anchor rejected checkpoint: {status_value}")
        reason = result.get("reason")
        if reason:
            print(f"[ERROR] Reason: {reason}")
        raise SystemExit(1)

    print(f"[OK] Anchor status    : {status_value}")
    print(f"Ledger ID           : {ledger_id}")
    print(f"Anchor URL          : {anchor_url.rstrip('/')}")
    print(f"Checkpoint index    : {payload['checkpoint_index']}")
    print(f"Checkpoint hash     : {payload['checkpoint_hash']}")
    print(f"Pi anchor index     : {result.get('anchor_index')}")
    print(f"Pi anchor hash      : {result.get('pi_anchor_hash')}")


def print_anchor_status_result(result: dict[str, Any]) -> None:
    """Render the external anchor comparison result."""
    status_value = result.get("status")
    print(f"Anchor Status : {status_value}")

    if status_value == "MATCH":
        print(f"Checkpoint    : {result.get('local_index')}")
        return

    if status_value in {"BEHIND", "AHEAD"}:
        print(f"Local Index   : {result.get('local_index')}")
        print(f"Pi Index      : {result.get('pi_index')}")
        return

    if status_value == "DIVERGENCE":
        print(f"Local Hash    : {result.get('local_hash')}")
        print(f"Pi Hash       : {result.get('pi_hash')}")
        return

    if status_value == "UNREACHABLE":
        print(f"Reason        : {result.get('reason')}")


def anchor_status(args: list[str]) -> None:
    """Compare the latest local checkpoint with the latest external anchor."""
    anchor_url = _parse_option(
        args,
        "--anchor-url",
        os.getenv("KALYX_ANCHOR_URL", DEFAULT_ANCHOR_URL),
    )
    ledger_id = _parse_option(
        args,
        "--ledger-id",
        os.getenv("KALYX_LEDGER_ID", DEFAULT_LEDGER_ID),
    )

    result = compare_anchor_status(anchor_url=anchor_url, ledger_id=ledger_id)
    print_anchor_status_result(result)


def inspect() -> None:
    """Print ledger entries in a readable format."""
    print("KALYX Ledger Inspection")
    print("-----------------------")

    records = load_ledger_records()
    if not records:
        print("[!] No ledger records found")
        return

    for index, entry in enumerate(records, start=1):
        print(f"Entry {index}")
        for key in (
            "seq",
            "ts",
            "source",
            "comm",
            "argv",
            "pid",
            "ppid",
            "ret",
            "uid",
            "user",
            "tty",
            "session",
            "parent_comm",
            "parent_exe",
            "action",
            "target",
        ):
            print(f"  {key:<12}: {entry.get(key, 'N/A')}")

        prev_hash = entry.get("prev_hash")
        record_hash = entry.get("hash")

        print(f"  prev_hash   : {prev_hash[:16]}..." if prev_hash else "  prev_hash   : N/A")
        print(f"  hash        : {record_hash[:16]}..." if record_hash else "  hash        : N/A")
        print()


def export() -> None:
    """Export the ledger and verification state."""
    print("KALYX Export")
    print("------------")

    bundle = export_ledger_bundle()
    if bundle is None:
        print("[!] No ledger records to export")
        raise SystemExit(1)

    verification = bundle.get("verification", {})
    verification_status = (
        verification.get("status")
        if isinstance(verification, dict)
        else verification
    )

    print(f"[+] Exported {bundle['total_records']} records")
    print(f"[+] Verification status: {verification_status}")
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

        event_time = None
        process = None
        action = None

        for line in block.strip().splitlines():
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
            elif "O_TRUNC" in line:
                action = "WRITE/TRUNCATE"
            elif "O_WRONLY" in line and action is None:
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
        print(f"[!] {action} detected")
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
        _print_alert(alert)
        print()


def _print_alert(alert: dict[str, Any]) -> None:
    """Print one alert consistently."""
    for key in (
        "type",
        "severity",
        "user",
        "target",
        "session",
        "seq_start",
        "seq_end",
        "ts_start",
        "ts_end",
        "delta_seconds",
        "details",
    ):
        print(f"  {key:<13}: {alert.get(key, 'N/A')}")


def print_verify_result(result: dict[str, Any], output_format: str) -> None:
    """Render verification output in text or JSON format."""
    if output_format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    status_value = result.get("status")

    if status_value == "VALID":
        print("[OK] Ledger verified")
        print(f"[OK] Records checked: {result.get('record_count')}")
        print(f"[OK] Trust state: {result.get('trust_state')}")
        print(f"[OK] Last trusted hash: {result.get('last_valid_hash')}")

        checkpoint_record = result.get("checkpoint")
        if isinstance(checkpoint_record, dict):
            if checkpoint_record.get("written"):
                print(f"[OK] Checkpoint written: {checkpoint_record.get('checkpoint_hash')}")
            else:
                print(f"[INFO] Checkpoint: {checkpoint_record.get('reason')}")
        return

    if status_value == "TAMPERED":
        print("[ERROR] Ledger verification failed")
        print(f"[ERROR] Trust state: {result.get('trust_state')}")
        print(f"[ERROR] Reason: {result.get('reason')}")
        print(f"[ERROR] Failure index: {result.get('failure_index')}")
        print(f"[ERROR] Valid until index: {result.get('valid_until_index')}")
        print(f"[ERROR] Last trusted hash: {result.get('last_valid_hash')}")
        return

    if status_value == "EMPTY":
        print("[ERROR] Ledger empty")
        return

    if status_value == "NO_LEDGER":
        print("[ERROR] Ledger not found")
        return

    print(f"[ERROR] Unknown verification state: {status_value}")


def _parse_output_format(args: list[str]) -> str:
    """Parse optional --format flag."""
    if "--format" not in args:
        return "text"

    index = args.index("--format")
    try:
        output_format = args[index + 1]
    except IndexError as exc:
        raise ValueError("Missing value for --format") from exc

    if output_format not in {"text", "json"}:
        raise ValueError("Format must be 'text' or 'json'")

    return output_format


def main() -> None:
    """Dispatch CLI commands."""
    args = sys.argv[1:]

    if not args or args[0] in {"--help", "-h", "help"}:
        print_help()
        return

    cmd = args[0]

    try:
        output_format = _parse_output_format(args)
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(2) from exc

    if cmd == "ingest":
        try:
            count = ingest_execsnoop_file()
        except LedgerNotTrustedError as exc:
            print(f"[ERROR] {exc}")
            raise SystemExit(1) from exc

        print(f"[+] Ingested {count} event(s)" if count else "[!] No valid events found")
        return

    if cmd == "ingest-live":
        try:
            print("[INFO] Starting live eBPF ingestion from execsnoop")
            print("[INFO] Press Ctrl+C to stop")
            result = ingest_live_stream()
            print(f"[INFO] Ingested {result.get('ingested', 0)} live event(s)")
            print(f"[INFO] Skipped {result.get('skipped', 0)} background/noise event(s)")
            print(f"[INFO] Rejected {result.get('rejected', 0)} malformed event(s)")
        except FileNotFoundError as exc:
            print(f"[ERROR] {exc}")
            raise SystemExit(1) from exc
        except RuntimeError as exc:
            print(f"[ERROR] {exc}")
            raise SystemExit(1) from exc
        except LedgerNotTrustedError as exc:
            print(f"[ERROR] {exc}")
            raise SystemExit(1) from exc
        except KeyboardInterrupt:
            print("\n[INFO] Live ingestion stopped")
        return

    if cmd == "verify":
        result = verify_ledger_state(write_checkpoint=True)
        print_verify_result(result, output_format=output_format)
        raise SystemExit(0 if result.get("valid") else 1)

    if cmd == "status":
        status()
        return

    if cmd == "checkpoint":
        checkpoint(output_format=output_format)
        return

    if cmd == "anchor":
        try:
            anchor(args[1:])
        except ValueError as exc:
            print(f"[ERROR] {exc}")
            raise SystemExit(2) from exc
        return

    if cmd == "anchor-status":
        try:
            anchor_status(args[1:])
        except ValueError as exc:
            print(f"[ERROR] {exc}")
            raise SystemExit(2) from exc
        return

    if cmd == "inspect":
        inspect()
        return

    if cmd == "export":
        export()
        return

    if cmd == "audit":
        audit()
        return

    if cmd == "detect":
        result = detect_and_persist_alerts()
        alerts = result.get("alerts", [])

        if not alerts:
            print("[+] No suspicious patterns detected")
            return

        print("[!] Suspicious activity detected")
        print()

        for alert in alerts:
            _print_alert(alert)
            print()

        print(f"[+] Persisted {result.get('written', 0)} new alert(s)")
        return

    if cmd == "alerts":
        show_alerts()
        return

    print(f"[ERROR] Unknown command: {cmd}")
    print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
