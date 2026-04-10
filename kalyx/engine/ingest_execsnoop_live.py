import shutil
import subprocess

from kalyx.core.chain import chain_event
from kalyx.core.normalize import normalize_event
from kalyx.engine.enrichment import enrich_event
from kalyx.engine.parser import parse_execsnoop_line


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


def should_ignore(event: dict) -> bool:
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

    # Ignore obvious daemon/background root noise unless it looks meaningful
    if user == "root" and session == "background_or_daemon" and action == "EXEC":
        return True

    return False


def get_execsnoop_cmd() -> list[str]:
    binary = shutil.which("execsnoop-bpfcc")
    if not binary:
        raise FileNotFoundError("execsnoop-bpfcc not found")

    return ["sudo", "-n", binary, "-U"]


def main():
    try:
        cmd = get_execsnoop_cmd()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return

    print("[INFO] Starting live eBPF ingestion from execsnoop")
    print("[INFO] Press Ctrl+C to stop")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except Exception as e:
        print(f"[ERROR] Failed to start execsnoop: {e}")
        return

    if proc.poll() is not None:
        err = proc.stderr.read()
        print(f"[ERROR] execsnoop failed: {err}")
        return

    ingested = 0
    skipped = 0

    try:
        assert proc.stdout is not None

        for raw_line in proc.stdout:
            event = parse_execsnoop_line(raw_line)
            if event is None:
                continue

            event = enrich_event(event)
            event = normalize_event(event)
            event["source"] = "ebpf_execsnoop"

            if should_ignore(event):
                skipped += 1
                continue

            chain_event(event)
            ingested += 1

            print(
                f"[INGEST] pid={event['pid']} ppid={event['ppid']} "
                f"comm={event['comm']} user={event.get('user', '?')} "
                f"action={event.get('action', '?')} "
                f"target={event.get('target', '?')} "
                f"argv={event['argv']}"
            )

    except KeyboardInterrupt:
        print("\n[INFO] Live ingestion stopped")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass

        print(f"[INFO] Ingested {ingested} live events")
        print(f"[INFO] Skipped {skipped} background/noise events")


if __name__ == "__main__":
    main()