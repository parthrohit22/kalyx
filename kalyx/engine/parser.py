import re
from typing import Optional

HEADER_PREFIX = "UID"


def parse_execsnoop_line(line: str) -> Optional[dict]:
    line = line.strip()
    if not line or line.startswith(HEADER_PREFIX):
        return None

    parts = line.split(None, 5)  # split on any whitespace, max 6 parts

    if len(parts) < 6:
        return None

    uid_s, comm, pid_s, ppid_s, ret_s, argv = parts

    try:
        return {
            "uid": int(uid_s),
            "comm": comm,
            "pid": int(pid_s),
            "ppid": int(ppid_s),
            "ret": int(ret_s),
            "argv": argv.strip(),
        }
    except ValueError:
        return None