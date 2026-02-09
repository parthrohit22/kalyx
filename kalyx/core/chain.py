import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import socket
import getpass

LOG_PATH = Path("logs/exec_chain.jsonl")
GENESIS_HASH = "0" * 64

SCHEMA = "kalyx-ledger-v1"
TOOL = "kalyx"
TOOL_VER = "0.1"

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _canonical_json(obj: dict) -> str:
    # Stable JSON string (critical for reproducible hashes)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _get_last_hash() -> str:
    if not LOG_PATH.exists():
        return GENESIS_HASH
    last_line = None
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            last_line = line
    if not last_line:
        return GENESIS_HASH
    return json.loads(last_line)["hash"]

def build_record(event: dict, source: str) -> dict:
    return {
        "_meta": {
            "schema": SCHEMA,
            "tool": TOOL,
            "tool_ver": TOOL_VER
        },
        "event": event,
        "ingest": {
            "source": source,
            "host": socket.gethostname(),
            "ingested_by": getpass.getuser(),
            "ts_ingested": _now_utc_iso()
        }
    }

def chain_record(record: dict) -> dict:
    prev_hash = _get_last_hash()

    # Hash must NOT include hash fields themselves
    payload_obj = {
        "_meta": record["_meta"],
        "event": record["event"],
        "ingest": record["ingest"]
    }

    payload = _canonical_json(payload_obj)
    curr_hash = _sha256_hex(prev_hash + payload)

    out = dict(record)
    out["prev_hash"] = prev_hash
    out["hash"] = curr_hash

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(_canonical_json(out) + "\n")

    return out
