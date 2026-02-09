import json
import hashlib
from pathlib import Path

LOG_PATH = Path("logs/exec_chain.jsonl")
GENESIS_HASH = "0" * 64

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def verify_chain() -> bool:
    if not LOG_PATH.exists():
        print("[!] No ledger file found")
        return False

    prev_hash = GENESIS_HASH

    with LOG_PATH.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            entry = json.loads(line)

            # Rebuild the exact payload used during hashing
            payload_obj = {
                "_meta": entry["_meta"],
                "event": entry["event"],
                "ingest": entry["ingest"]
            }
            payload = _canonical_json(payload_obj)
            expected_hash = _sha256_hex(prev_hash + payload)

            if entry["prev_hash"] != prev_hash or entry["hash"] != expected_hash:
                print(f"[!] Tampering detected at entry {idx}")
                return False

            prev_hash = entry["hash"]

    print("[✓] Ledger verified — no tampering detected")
    return True

if __name__ == "__main__":
    verify_chain()
