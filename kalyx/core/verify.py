import json
import hashlib
from pathlib import Path
from datetime import datetime

LOG_PATH = Path("logs/exec_chain.jsonl")
STATUS_PATH = Path("logs/.kalyx_status.json")
GENESIS_HASH = "0" * 64


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _canonical(obj: dict) -> str:
    o = dict(obj)
    o.pop("hash", None)
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def save_status(result: str, failure_index=None):
    data = {
        "last_verified": result,
        "timestamp": datetime.utcnow().isoformat(),
        "failure_index": failure_index
    }

    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with STATUS_PATH.open("w") as f:
        json.dump(data, f, indent=2)


def verify_chain():
    if not LOG_PATH.exists():
        print("[!] No ledger file found")
        save_status("NO_LEDGER")
        return False

    prev = GENESIS_HASH

    with LOG_PATH.open() as f:
        for i, line in enumerate(f, 1):
            e = json.loads(line)

            if e["prev_hash"] != prev or e["hash"] != _sha256(_canonical(e)):
                print(f"[!] Tampering detected at entry {i}")
                save_status("FAILED", i)
                return False

            prev = e["hash"]

    print("[✓] Ledger verified — no tampering detected")
    save_status("SUCCESS")
    return True


if __name__ == "__main__":
    verify_chain()
