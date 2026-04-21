"""Sample file ingestion entry point."""

from kalyx.services.pipeline import ingest_execsnoop_file


def main() -> None:
    """Run sample log ingestion through the shared backend pipeline."""

    count = ingest_execsnoop_file()
    if count > 0:
        print(f"[+] Ingested {count} events")
        print("[+] Ledger updated")
    else:
        print("[!] No valid events found")

if __name__ == "__main__":
    main()
