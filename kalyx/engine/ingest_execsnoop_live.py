"""Live eBPF ingestion entry point."""

from kalyx.services.pipeline import ingest_live_stream


def main() -> None:
    """Run live execsnoop ingestion through the shared backend pipeline."""

    try:
        print("[INFO] Starting live eBPF ingestion from execsnoop")
        print("[INFO] Press Ctrl+C to stop")
        result = ingest_live_stream()
        print(f"[INFO] Ingested {result['ingested']} live events")
        print(f"[INFO] Skipped {result['skipped']} background/noise events")
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
    except KeyboardInterrupt:
        print("\n[INFO] Live ingestion stopped")


if __name__ == "__main__":
    main()
