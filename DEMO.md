# KALYX Demo Guide

## 1. Purpose

This guide demonstrates the working KALYX prototype end-to-end: ingest execution evidence, verify the hash-chained ledger, create checkpoints, anchor checkpoint boundaries, inspect anchor status, detect tampering, and run detection.

## 2. Prerequisites

- Python virtual environment installed and activated.
- Frontend dependencies installed under `frontend/`.
- Raspberry Pi anchor service available, or a local anchor service for testing.
- `kalyx-api` available.
- `kalyx-anchor` available.
- Angular frontend available.

See `README.md` and `docs/` for full setup details.

## 3. Demo Topology

```text
Browser / Angular Dashboard
        ↓
Host FastAPI API
        ↓
Host Evidence Core
        ↓
Anchor Client
        ↓
Raspberry Pi Anchor Authority
```

Angular talks only to the Host FastAPI API. It does not call the Raspberry Pi anchor directly. The Pi anchor may be run locally for testing.

## 4. Start Services

Terminal 1, Host API:

```bash
kalyx-api
```

If the anchor runs on a Raspberry Pi, start the host API with the Pi URL:

```bash
KALYX_ANCHOR_URL=http://<pi-ip>:8081 KALYX_LEDGER_ID=kalyx-demo kalyx-api
```

Terminal 2, Anchor API:

```bash
kalyx-anchor
```

Terminal 3, Angular dashboard:

```bash
cd frontend
npm start
```

Default URLs:

- Host API: `http://127.0.0.1:8000`
- Anchor API: `http://127.0.0.1:8081`
- Angular Dashboard: `http://127.0.0.1:4200`

Use `http://<pi-ip>:8081` when the anchor runs on Raspberry Pi instead of the local machine.

## 5. Verify Initial State

```bash
kalyx status
kalyx verify
```

Expected result: KALYX reports `VERIFIED`, `EMPTY`, or `NO_LEDGER` depending on current local state. The command should not crash with an unhandled exception.

## 6. Ingest And Verify Evidence

CLI route:

```bash
kalyx ingest
kalyx verify
kalyx inspect
```

Dashboard route:

- Open the Ingestion screen.
- Submit an event.
- Open the Verification screen.
- Run verification.
- Open the Ledger screen.

## 7. Create And Anchor A Checkpoint

CLI route:

```bash
kalyx checkpoint
kalyx anchor --anchor-url http://<anchor-host>:8081 --ledger-id kalyx-demo
kalyx anchor-status --anchor-url http://<anchor-host>:8081 --ledger-id kalyx-demo
```

Expected result:

```text
Anchor Status : MATCH
```

Dashboard route:

- Open the Verification screen.
- Check the Anchor Status card.
- Click `Check Anchor Status`.
- Click `Anchor Latest Checkpoint`.
- Confirm the resulting anchor state.

## 8. Demonstrate State Change

Strongest anchor lifecycle:

```text
MATCH
→ ingest new evidence
→ verify/checkpoint
→ AHEAD
→ anchor latest checkpoint
→ MATCH
```

Commands:

```bash
kalyx ingest
kalyx verify
kalyx checkpoint
kalyx anchor-status --anchor-url http://<anchor-host>:8081 --ledger-id kalyx-demo
kalyx anchor --anchor-url http://<anchor-host>:8081 --ledger-id kalyx-demo
kalyx anchor-status --anchor-url http://<anchor-host>:8081 --ledger-id kalyx-demo
```

After the new checkpoint is created but before it is anchored, `anchor-status` should report `AHEAD`. After anchoring, it should return to `MATCH`.

## 9. Demonstrate Tamper Detection

Back up the ledger, tamper with one record, verify that KALYX detects the problem, then restore the backup.

```bash
cp logs/exec_chain.jsonl logs/exec_chain.jsonl.demo.bak

python - <<'PY'
import json
from pathlib import Path

path = Path("logs/exec_chain.jsonl")
lines = path.read_text(encoding="utf-8").splitlines()
if not lines:
    raise SystemExit("No ledger records available to tamper")

record = json.loads(lines[0])
record["comm"] = f"{record.get('comm', 'unknown')}-tampered"
lines[0] = json.dumps(record, sort_keys=True, separators=(",", ":"))
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

kalyx verify

cp logs/exec_chain.jsonl.demo.bak logs/exec_chain.jsonl
rm logs/exec_chain.jsonl.demo.bak
kalyx verify
```

Expected result: verification fails or reports an untrusted boundary while tampered, then returns to the restored ledger state after the backup is copied back.

## 10. Run Detection

```bash
kalyx detect
kalyx alerts
```

Detection runs only on trusted evidence. If verification reports an untrusted state, detection should skip rather than analyze corrupted evidence.

## 11. Expected Success Signals

- Backend starts.
- Frontend serves in the browser.
- Ledger verifies.
- Checkpoint is created or reused.
- Anchor submission is `ACCEPTED` or `ALREADY_ANCHORED`.
- Anchor status reaches `MATCH`.
- Tampering causes verification failure or an untrusted state.
- Detection produces alerts or reports no alerts without crashing.

## 12. Common Problems

- `kalyx` command not found: activate the Python virtual environment or reinstall the package in editable mode.
- Wrong Python virtual environment: confirm `which kalyx`, `which kalyx-api`, and `which kalyx-anchor`.
- Frontend cannot reach backend: confirm `kalyx-api` is running at `http://127.0.0.1:8000` and check `frontend/src/environments/environment.ts`.
- Raspberry Pi anchor unreachable: confirm `kalyx-anchor` is running, the Pi IP is reachable, and port `8081` is open.
- Localhost confusion between Mac, UTM, and Pi: `127.0.0.1` means the current machine. Use the Pi IP from the host when anchoring to Raspberry Pi.
- No ledger found: run `kalyx ingest`, then `kalyx verify`.
- Anchor status `AHEAD` after new checkpoint: run `kalyx anchor --anchor-url http://<anchor-host>:8081 --ledger-id kalyx-demo`, then check status again.

## 13. Cleanup

If you ran the tamper demo, restore the backup if it still exists:

```bash
test -f logs/exec_chain.jsonl.demo.bak && cp logs/exec_chain.jsonl.demo.bak logs/exec_chain.jsonl
rm -f logs/exec_chain.jsonl.demo.bak
```

Stop services with `Ctrl+C` in each terminal.

Do not delete source files. If you want a clean demo state, optionally remove runtime logs only:

```bash
rm -rf logs reports anchors
```
