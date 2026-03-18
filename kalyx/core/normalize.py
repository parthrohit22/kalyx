import shlex

ACTION_MAP = {
    "rm": "DELETE",
    "unlink": "DELETE",

    "touch": "CREATE",

    "nano": "MODIFY",
    "vim": "MODIFY",
    "vi": "MODIFY",
    "echo": "MODIFY",
}


def extract_target(argv: str) -> str:
    try:
        parts = shlex.split(argv)
        if len(parts) >= 2:
            return parts[-1]
    except Exception:
        pass
    return "unknown"


def normalize_event(event: dict) -> dict:
    comm = event.get("comm", "")
    argv = event.get("argv", "")

    action = ACTION_MAP.get(comm, "EXEC")

    target = extract_target(argv)

    event.update({
        "action": action,
        "target": target,
    })

    return event