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
            tty = os.readlink(path)
            return tty
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


def enrich_event(event: dict) -> dict:
    uid = event.get("uid", -1)

    user = get_user_from_uid(uid)
    tty = get_tty(event["pid"])
    session = detect_session(tty)

    event.update({
        "user": user,
        "tty": tty,
        "session": session,
    })

    return event