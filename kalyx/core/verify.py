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


def verify_ledger(output_format="text"):
    result = {
        "status": None,
        "reason": None,
        "entry": None
    }

    if not LOG_PATH.exists():
        result["status"] = "NO_LEDGER"
        save_status("NO_LEDGER")
    else:
        prev = GENESIS_HASH

        with LOG_PATH.open() as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            result["status"] = "EMPTY"
            save_status("EMPTY")
        else:
            for i, line in enumerate(lines, 1):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    result["status"] = "TAMPERED"
                    result["reason"] = "INVALID_JSON"
                    result["entry"] = i
                    save_status("CORRUPTED_JSON", i)
                    break

                if (
                    entry.get("prev_hash") != prev
                    or entry.get("hash") != _sha256(_canonical(entry))
                ):
                    result["status"] = "TAMPERED"
                    result["reason"] = "HASH_MISMATCH"
                    result["entry"] = i
                    save_status("FAILED", i)
                    break

                prev = entry["hash"]
            else:
                result["status"] = "VALID"
                save_status("SUCCESS")

    # ---- OUTPUT HANDLING ----
    if output_format == "json":
        print(json.dumps(result, indent=2))
    else:
        if result["status"] == "VALID":
            print("[OK]    Ledger verified")
        elif result["status"] == "TAMPERED":
            print("[ERROR] Ledger tampered")
            if result["reason"]:
                print(f"[ERROR] Reason: {result['reason']}")
            if result["entry"]:
                print(f"[ERROR] Entry: {result['entry']}")
        elif result["status"] == "EMPTY":
            print("[ERROR] Ledger empty")
        elif result["status"] == "NO_LEDGER":
            print("[ERROR] Ledger not found")

    return result["status"] == "VALID"


if __name__ == "__main__":
    verify_ledger()