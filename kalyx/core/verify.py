import json
import hashlib
from pathlib import Path

LOG_PATH = Path("logs/exec_chain.jsonl")
GENESIS_HASH = "0" * 64

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def _canonical(obj: dict) -> str:
    o = dict(obj)
    o.pop("hash", None)
    return json.dumps(o, sort_keys=True, separators=(",", ":"))

def verify_chain():
    if not LOG_PATH.exists():
        print("[!] No ledger file found")
        return False

    prev = GENESIS_HASH
    with LOG_PATH.open() as f:
        for i, line in enumerate(f, 1):
            e = json.loads(line)
            if e["prev_hash"] != prev or e["hash"] != _sha256(_canonical(e)):
                print(f"[!] Tampering detected at entry {i}")
                return False
            prev = e["hash"]

    print("[✓] Ledger verified — no tampering detected")
    return True

if __name__ == "__main__":
    verify_chain()
