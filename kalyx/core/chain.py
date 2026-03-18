import json
import hashlib
from pathlib import Path
from datetime import datetime

LOG_PATH = Path("logs/exec_chain.jsonl")
GENESIS_HASH = "0" * 64


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _canonical(obj: dict) -> str:
    o = dict(obj)
    o.pop("hash", None)
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def _get_last_entry():
    if not LOG_PATH.exists():
        return None

    with LOG_PATH.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return None

    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    return None


def chain_event(event: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    last_entry = _get_last_entry()

    if last_entry:
        prev_hash = last_entry["hash"]
        seq = last_entry.get("seq", 0) + 1
    else:
        prev_hash = GENESIS_HASH
        seq = 1

    record = dict(event)
    record["seq"] = seq
    record["ts"] = datetime.utcnow().isoformat()
    record.setdefault("source", "unknown")

    record["prev_hash"] = prev_hash
    record["hash"] = _sha256(_canonical(record))

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")