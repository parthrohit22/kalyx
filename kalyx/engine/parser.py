from typing import Optional

HEADER_PREFIX = "UID"


def parse_execsnoop_line(line: str) -> Optional[dict]:
    line = line.strip()

    if not line or line.startswith(HEADER_PREFIX):
        return None

    parts = line.split(None, 5)

    if len(parts) != 6:
        return None

    uid_s, comm, pid_s, ppid_s, ret_s, argv = parts

    try:
        uid = int(uid_s)
        pid = int(pid_s)
        ppid = int(ppid_s)
        ret = int(ret_s)
    except ValueError:
        return None

    argv = argv.strip()
    if not argv:
        argv = "unknown"

    return {
        "uid": uid,
        "comm": comm.strip(),
        "pid": pid,
        "ppid": ppid,
        "ret": ret,
        "argv": argv,
    }