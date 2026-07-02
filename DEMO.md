# KALYX Local Walkthrough

Use this walkthrough to run the current product locally and check its main workflows.

## 1. What You Will Check

You will ingest execution evidence, verify the hash-chained ledger, create checkpoints, anchor checkpoint boundaries, inspect anchor status, check tamper detection, and run detection.

## 2. Prerequisites

- Python virtual environment installed and activated.
- Frontend dependencies installed under `frontend/`.
- Raspberry Pi anchor service available, or a local anchor service for testing.
- `kalyx-api` available.
- `kalyx-anchor` available.
- Angular frontend available.

See `README.md` and `docs/` for full setup details.

## 3. Local Topology

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

### Checked-In Network Setup

The checked-in frontend configuration points Angular to the Linux host running the FastAPI backend at `http://192.168.64.2:8000`. This address belongs to the current development setup, where the backend runs inside a Linux virtual machine. The host backend reaches the Raspberry Pi through `KALYX_ANCHOR_URL`.

`frontend/src/environments/environment.ts` controls Angular-to-host communication. `KALYX_ANCHOR_URL` controls host-to-Pi communication. Angular should never be pointed at the Raspberry Pi anchor API.

## 4. Start Services

Start the Raspberry Pi first, the host backend second, and Angular last.

### Terminal 1 — Raspberry Pi

```bash
cd ~/kalyx
source .venv/bin/activate
kalyx-anchor
```

### Terminal 2 — Host Backend

```bash
cd ~/kalyx
source .venv/bin/activate
export KALYX_ANCHOR_URL=http://<pi-ip>:8081
export KALYX_LEDGER_ID=kalyx-demo
kalyx-api --host 0.0.0.0 --port 8000
```

### Terminal 3 — Angular

```bash
cd ~/kalyx/frontend
npm start
```

Service addresses:

- Host API: `http://<host-ip>:8000`
- Raspberry Pi Anchor API: `http://<pi-ip>:8081`
- Angular Dashboard: `http://127.0.0.1:4200`

### Local Anchor Fallback

If the Raspberry Pi is unavailable, run the anchor service in a separate terminal on the host:

```bash
cd ~/kalyx
source .venv/bin/activate
kalyx-anchor
```

Then configure the host backend terminal to use the local anchor before starting `kalyx-api`:

```bash
export KALYX_ANCHOR_URL=http://127.0.0.1:8081
export KALYX_LEDGER_ID=kalyx-demo
kalyx-api --host 0.0.0.0 --port 8000
```

For a complete same-machine setup, set `frontend/src/environments/environment.ts` to `http://127.0.0.1:8000`.

## 5. Verify Initial State

```bash
kalyx status
kalyx verify
```

You should see `VERIFIED`, `EMPTY`, or `NO_LEDGER`, depending on the current local state.

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

You should see:

```text
Anchor Status : MATCH
```

Dashboard route:

- Open the Verification screen.
- Check the Anchor Status card.
- Click `Check Anchor Status`.
- Click `Anchor Latest Checkpoint`.
- Confirm the resulting anchor state.

Verification creates or reuses the latest safe local checkpoint; it does not anchor that checkpoint automatically. `Anchor Latest Checkpoint` sends the checkpoint through the Host FastAPI API and host anchor client. `MATCH` means the local and Pi checkpoint indices and hashes agree.

## 8. Check The Anchor Lifecycle

Anchor lifecycle:

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

## 9. Check Tamper Detection

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

Verification should fail or report an untrusted boundary while the ledger is modified, then return to the restored state after the backup is copied back.

## 10. Run Detection

```bash
kalyx detect
kalyx alerts
```

Detection skips when full-ledger hash-chain verification fails. It does not currently evaluate checkpoint continuity, so use `/status` or the Overview screen separately when checking checkpoint trust state.

## 11. Completion Checklist

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
- Frontend cannot reach backend: confirm `kalyx-api` is running and check `frontend/src/environments/environment.ts`. Use `http://127.0.0.1:8000` for same-machine operation or a host API address reachable from the browser in any multi-machine setup.
- Raspberry Pi anchor unreachable: confirm `kalyx-anchor` is running, the Pi IP is reachable, and port `8081` is open.
- Localhost confusion between the browser machine, Linux host, and Pi: `127.0.0.1` means the current machine. Use the Pi IP from the host when anchoring to Raspberry Pi.
- No ledger found: run `kalyx ingest`, then `kalyx verify`.
- Anchor status `AHEAD` after new checkpoint: run `kalyx anchor --anchor-url http://<anchor-host>:8081 --ledger-id kalyx-demo`, then check status again.

## 13. Cleanup

If you ran the tamper check, restore the backup if it still exists:

```bash
test -f logs/exec_chain.jsonl.demo.bak && cp logs/exec_chain.jsonl.demo.bak logs/exec_chain.jsonl
rm -f logs/exec_chain.jsonl.demo.bak
```

Stop services with `Ctrl+C` in each terminal.

Runtime evidence and Pi anchor data can be useful for later inspection. Keep `logs/`, `reports/`, and `anchors/` unless you intentionally want a clean local state.
