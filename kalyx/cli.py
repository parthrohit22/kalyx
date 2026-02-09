import sys
from kalyx.engine.ingest_execsnoop import main as ingest
from kalyx.core.verify import verify_chain

def main():
    if len(sys.argv) < 2:
        print("Usage: kalyx [ingest|verify]")
        return

    if sys.argv[1] == "ingest":
        ingest()
    elif sys.argv[1] == "verify":
        verify_chain()
    else:
        print("Unknown command")

if __name__ == "__main__":
    main()
