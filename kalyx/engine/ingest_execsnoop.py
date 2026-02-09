from kalyx.core.chain import chain_event

RAW = "sample_exec.log"

def main():
    with open(RAW) as f:
        for line in f:
            p = line.strip().split(maxsplit=4)
            if len(p) < 4:
                continue
            event = {
                "comm": p[0],
                "pid": int(p[1]),
                "ppid": int(p[2]),
                "ret": int(p[3]),
                "argv": p[4] if len(p) == 5 else ""
            }
            chain_event(event)

if __name__ == "__main__":
    main()
