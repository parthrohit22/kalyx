import json
import hashlib
from pathlib import Path

LOG_PATH = Path("logs/exec_chain.jsonl")

GENESIS_HASH = "0" * 64


def _hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def get_last_hash():
    if not LOG_PATH.exists():
        return GENESIS_HASH

    with LOG_PATH.open("r") as f:
        last = None
        for line in f:
            last = line
        if last:
            return json.loads(last)["hash"]

    return GENESIS_HASH


def chain_event(event: dict) -> dict:
    prev_hash = get_last_hash()

    payload = json.dumps(event, sort_keys=True)
    curr_hash = _hash(prev_hash + payload)

    record = {
        **event,
        "prev_hash": prev_hash,
        "hash": curr_hash,
    }

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")

    return record
