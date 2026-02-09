import os
from kalyx.core.chain import build_record, chain_record

RAW_INPUT = "logs/raw_exec_log.txt"  # adjust if your raw file name differs

def parse_line(line: str) -> dict | None:
    # expected format like: "ls 1484 978 0 "
    parts = line.strip().split(maxsplit=4)
    if len(parts) < 4:
        return None

    comm = parts[0]
    pid = int(parts[1])
    ppid = int(parts[2])
    ret = int(parts[3])
    argv = parts[4] if len(parts) == 5 else ""

    # ignore header lines
    if comm == "PCOMM":
        return None

    return {
        "ts": "N/A",
        "comm": comm,
        "pid": pid,
        "ppid": ppid,
        "uid": None,
        "argv": argv,
        "ret": ret
    }

def main():
    if not os.path.exists(RAW_INPUT):
        return

    with open(RAW_INPUT, "r", encoding="utf-8") as f:
        for line in f:
            e = parse_line(line)
            if not e:
                continue
            rec = build_record(e, source="execsnoop-bpfcc")
            chain_record(rec)

if __name__ == "__main__":
    main()
