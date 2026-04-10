import os
import pwd


def get_user_from_uid(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return "unknown"


def get_tty(pid: int) -> str:
    try:
        path = f"/proc/{pid}/fd/0"
        if os.path.exists(path):
            value = os.readlink(path)

            if value.startswith("/dev/pts") or value.startswith("/dev/tty") or value.startswith("socket:"):
                return value
    except Exception:
        pass

    return "unknown"


def detect_session(tty: str) -> str:
    if tty.startswith("/dev/pts"):
        return "interactive_terminal"

    if tty.startswith("/dev/tty"):
        return "local_console"

    if tty.startswith("socket:"):
        return "network_or_ipc"

    if tty == "unknown":
        return "background_or_daemon"

    return "unknown"


def get_process_comm(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "unknown"


def get_process_exe(pid: int) -> str:
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except Exception:
        return "unknown"


def enrich_event(event: dict) -> dict:
    uid = event.get("uid", -1)
    pid = event.get("pid", -1)
    ppid = event.get("ppid", -1)

    user = get_user_from_uid(uid)
    tty = get_tty(pid)
    session = detect_session(tty)
    parent_comm = get_process_comm(ppid) if ppid > 0 else "unknown"
    parent_exe = get_process_exe(ppid) if ppid > 0 else "unknown"

    event.update({
        "user": user,
        "tty": tty,
        "session": session,
        "parent_comm": parent_comm,
        "parent_exe": parent_exe,
    })

    return event