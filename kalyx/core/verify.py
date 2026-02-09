import json
import hashlib

LOG_FILE = "logs/exec_chain.jsonl"
GENESIS_HASH = "0" * 64

def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def canonical_payload(entry: dict) -> str:
    """
    Recreate the exact payload that was hashed during chaining.
    Exclude the 'hash' field itself.
    """
    e = dict(entry)
    e.pop("hash", None)
    return json.dumps(e, sort_keys=True, separators=(",", ":"))

def verify_chain():
    prev_hash = GENESIS_HASH

    with open(LOG_FILE, "r") as f:
        for idx, line in enumerate(f, start=1):
            entry = json.loads(line)

            expected_hash = sha256_hex(
                prev_hash + canonical_payload(entry)
            )

            if entry["hash"] != expected_hash:
                print(f"[!] Tampering detected at entry {idx}")
                return False

            prev_hash = entry["hash"]

    print("[✓] Ledger verified — no tampering detected")
    return True

if __name__ == "__main__":
    verify_chain()
