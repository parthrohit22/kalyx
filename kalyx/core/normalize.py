import os
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


def canonical_comm(comm: str) -> str:
    if not comm:
        return "unknown"
    return os.path.basename(comm).strip()


def tokenize_argv(argv: str) -> list[str]:
    try:
        return shlex.split(argv)
    except Exception:
        return []


def extract_target(comm: str, argv: str) -> str:
    tokens = tokenize_argv(argv)
    if not tokens:
        return "unknown"

    cmd = canonical_comm(comm)

    # Remove executable token if present at start
    if tokens and os.path.basename(tokens[0]) == cmd:
        tokens = tokens[1:]

    # Remove flags
    args = [t for t in tokens if not t.startswith("-")]

    if not args:
        return "unknown"

    # Command-specific handling
    if cmd in {"rm", "unlink", "touch", "nano", "vim", "vi"}:
        return args[-1]

    if cmd == "echo":
        # Shell redirection is usually handled by the shell, so echo itself
        # often does not provide a reliable file target.
        return "unknown"

    return "unknown"


def normalize_event(event: dict) -> dict:
    comm = canonical_comm(event.get("comm", ""))
    argv = event.get("argv", "")

    action = ACTION_MAP.get(comm, "EXEC")
    target = extract_target(comm, argv)

    event.update({
        "comm": comm,
        "action": action,
        "target": target,
    })

    return event