"""Shared ingestion pipeline used by CLI and API interfaces."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from kalyx.core.chain import chain_event
from kalyx.core.normalize import normalize_event
from kalyx.engine.enrichment import enrich_event
from kalyx.engine.parser import parse_execsnoop_line

RAW_SAMPLE_LOG = "sample_exec.log"
IGNORE_PREFIXES = (
    "systemd",
    "sshd",
    "run-parts",
    "landscape",
    "update-motd",
    "debian-sa1",
    "grep",
    "cut",
    "find",
    "cat",
    "awk",
    "date",
    "stat",
    "sort",
    "egrep",
    "basename",
    "dirname",
    "locale",
    "locale-check",
    "lesspipe",
    "dircolors",
)
IGNORE_EXACT = {
    "env",
    "sh",
    "bash",
    "uname",
    "who",
    "tr",
    "head",
    "id",
    "expr",
    "bc",
    "release-upgrade",
}


def should_ignore(event: dict[str, Any]) -> bool:
    """Filter obvious background noise out of live ingestion."""

    comm = event.get("comm", "")
    argv = event.get("argv", "")
    pid = event.get("pid", -1)
    ppid = event.get("ppid", -1)
    user = event.get("user", "unknown")
    session = event.get("session", "unknown")
    action = event.get("action", "EXEC")

    if pid <= 0 or ppid <= 0:
        return True
    if comm in IGNORE_EXACT:
        return True
    if comm.startswith(IGNORE_PREFIXES):
        return True
    if "update-motd" in argv or "landscape" in argv:
        return True
    if user == "root" and session == "background_or_daemon" and action == "EXEC":
        return True
    return False


def build_record(event: dict[str, Any], source: str) -> dict[str, Any]:
    """Run enrichment and normalization before chaining an event."""

    enriched = enrich_event(dict(event))
    normalized = normalize_event(enriched)
    normalized["source"] = source
    return normalized


def ingest_payload(*, raw_line: str | None = None, event: dict[str, Any] | None = None, source: str = "api") -> dict[str, Any]:
    """Ingest a single payload through the shared processing pipeline."""

    if raw_line:
        parsed_event = parse_execsnoop_line(raw_line)
    elif event is not None:
        parsed_event = dict(event)
    else:
        raise ValueError("Either raw_line or event must be provided")

    if parsed_event is None:
        raise ValueError("Payload could not be parsed into an event")

    record = build_record(parsed_event, source=source)
    chained = chain_event(record)
    return chained


def parse_sample_line(line: str) -> dict[str, Any] | None:
    """Parse the existing sample ingestion format used by the CLI."""

    parts = line.strip().split(maxsplit=4)
    if len(parts) < 4:
        return None

    try:
        return {
            "comm": parts[0],
            "pid": int(parts[1]),
            "ppid": int(parts[2]),
            "ret": int(parts[3]),
            "argv": parts[4] if len(parts) == 5 else "",
        }
    except ValueError:
        return None


def ingest_execsnoop_file(path: str = RAW_SAMPLE_LOG, source: str = "sample_exec_log") -> int:
    """Ingest the existing demo log file through the shared pipeline."""

    count = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            event = parse_sample_line(line)
            if event is None:
                continue
            ingest_payload(event=event, source=source)
            count += 1
    return count


def get_execsnoop_cmd() -> list[str]:
    """Return the eBPF execsnoop command."""

    binary = shutil.which("execsnoop-bpfcc")
    if not binary:
        raise FileNotFoundError("execsnoop-bpfcc not found")
    return ["sudo", "-n", binary, "-U"]


def ingest_live_stream() -> dict[str, int]:
    """Run live execsnoop ingestion using the shared pipeline."""

    cmd = get_execsnoop_cmd()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    if proc.poll() is not None:
        err = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(f"execsnoop failed: {err}")

    ingested = 0
    skipped = 0
    try:
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            event = parse_execsnoop_line(raw_line)
            if event is None:
                continue

            record = build_record(event, source="ebpf_execsnoop")
            if should_ignore(record):
                skipped += 1
                continue

            chain_event(record)
            ingested += 1
            print(
                f"[INGEST] pid={record['pid']} ppid={record['ppid']} "
                f"comm={record['comm']} user={record.get('user', '?')} "
                f"action={record.get('action', '?')} target={record.get('target', '?')} "
                f"argv={record['argv']}"
            )
    finally:
        try:
            proc.terminate()
        except Exception:
            pass

    return {"ingested": ingested, "skipped": skipped}
