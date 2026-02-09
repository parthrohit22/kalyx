import json
import hashlib
from pathlib import Path

LOG_PATH = Path("logs/exec_chain.jsonl")
GENESIS_HASH = "0" * 64

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def _last_hash() -> str:
    if not LOG_PATH.exists():
        return GENESIS_HASH
    last = None
    with LOG_PATH.open() as f:
        for line in f:
            last = line
    return json.loads(last)["hash"] if last else GENESIS_HASH

def chain_event(event: dict) -> dict:
    prev = _last_hash()
    record = {**event, "prev_hash": prev}
    record["hash"] = _sha256(_canonical(record))
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(_canonical(record) + "\n")
    return record
