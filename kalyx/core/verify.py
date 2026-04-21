import json

from kalyx.services.ledger import verify_ledger_state


def verify_ledger(output_format: str = "text") -> bool:
    """Verify the ledger and preserve the original CLI-oriented output contract."""

    result = verify_ledger_state()
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

    return result["valid"]


if __name__ == "__main__":
    verify_ledger()
