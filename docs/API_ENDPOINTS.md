# API Endpoints

The KALYX API is a FastAPI adapter over shared backend services. It does not introduce separate ledger or detection logic.

Base URL for local development:

```text
http://127.0.0.1:8000
```

Start the server:

```bash
kalyx-api
```

## API Key Protection

KALYX supports optional environment-variable API key protection for operational
routes. When `KALYX_API_KEY` is unset, local development behavior is preserved and
protected routes are allowed without a header. When `KALYX_API_KEY` is set,
protected routes require this request header:

```text
X-KALYX-API-Key: <configured-key>
```

Missing or invalid keys return:

```json
{
  "detail": "Missing or invalid API key"
}
```

with HTTP status `401 Unauthorized`.

Example:

```bash
KALYX_API_KEY=example-dev-key kalyx-api

curl -X POST http://127.0.0.1:8000/ingest \
  -H 'Content-Type: application/json' \
  -H 'X-KALYX-API-Key: example-dev-key' \
  -d '{
    "event": {
      "comm": "touch",
      "pid": 5000,
      "ppid": 4000,
      "argv": "touch /tmp/kalyx-api.txt",
      "ret": 0,
      "uid": 1000
    },
    "source": "api"
  }'
```

This is lightweight local API protection. It is not user authentication, sessions,
OAuth, JWT, or role-based access control.

See `docs/CONFIGURATION.md` for the central environment variable reference.
The Angular console sends `X-KALYX-API-Key` only when
`frontend/src/environments/environment.ts` has a non-empty `kalyxApi.apiKey`.

## Endpoint Summary

| Method | Path | Protection | Description |
| --- | --- | --- | --- |
| `GET` | `/` | Unprotected | Serve a minimal API-running status page |
| `GET` | `/status` | Unprotected | Return ledger status, trust state, and checkpoint metadata |
| `POST` | `/verify` | API key when configured | Run deterministic ledger verification and write a local checkpoint when safe |
| `POST` | `/ingest` | API key when configured | Ingest one raw line or structured execution event |
| `POST` | `/detect` | API key when configured | Run deterministic detection through the shared detection service |
| `GET` | `/alerts` | Unprotected | Return persisted alert records |
| `GET` | `/ledger` | Unprotected | Return recent parsed ledger records for inspection |
| `GET` | `/anchor/status` | Unprotected | Compare the latest local checkpoint with the latest Raspberry Pi anchor |
| `POST` | `/anchor` | API key when configured | Create or reuse a safe local checkpoint and submit it through the host anchor client |

## GET /

Serves a minimal status page confirming that the FastAPI backend is running. The real operations console is the separate Angular app in `frontend/`.

```bash
curl http://127.0.0.1:8000/
```

## GET /status

Returns a concise ledger health summary. Internally, this calls `get_status_summary`, which verifies the ledger before building the response.

```bash
curl http://127.0.0.1:8000/status
```

Response schema:

```json
{
  "entries": 3,
  "failure_index": null,
  "failure_reason": null,
  "last_hash": "2aa8b73c...",
  "last_valid_hash": "2aa8b73c...",
  "ledger_file": "logs/exec_chain.jsonl",
  "ledger_state": "READY",
  "checkpoint_available": true,
  "checkpoint_gap_detected": false,
  "checkpoint_last_hash": "2aa8b73c...",
  "checkpoint_reason": null,
  "checkpoint_record_count": 3,
  "checkpoint_state": "MATCHED",
  "trust_state": "VERIFIED",
  "valid_until_index": 3,
  "verification_status": "VALID",
  "verification_timestamp": "2026-05-20T14:12:30.142381+00:00",
  "verification_valid": true
}
```

Important fields:

- `verification_status`: `VALID`, `TAMPERED`, `EMPTY`, or `NO_LEDGER`.
- `verification_valid`: boolean validity flag.
- `failure_index`: first untrusted record, if any.
- `valid_until_index`: last verified record before failure.
- `last_valid_hash`: hash at the last trusted boundary.
- `trust_state`: operational trust state derived from verification and checkpoint continuity.
- `checkpoint_state`: latest checkpoint comparison state, such as `NO_CHECKPOINT`, `MATCHED`, `LEDGER_ADVANCED`, `LEDGER_BEHIND_CHECKPOINT`, or `CHECKPOINT_HASH_MISMATCH`.
- `checkpoint_gap_detected`: true when the current ledger conflicts with the latest local checkpoint.

## POST /verify

Runs deterministic verification over the full ledger. If verification succeeds and the ledger does not conflict with the latest checkpoint, this endpoint writes or reuses a local checkpoint.

```bash
curl -X POST http://127.0.0.1:8000/verify
```

Successful verification:

```json
{
  "failure_index": null,
  "last_valid_hash": "2aa8b73c...",
  "reason": null,
  "record_count": 3,
  "status": "VALID",
  "trust_state": "VERIFIED",
  "valid": true,
  "valid_until_index": 3,
  "checkpoint": {
    "checkpoint_hash": "67f1c6e1...",
    "record_count": 3,
    "written": true
  }
}
```

Verification failure example:

```json
{
  "actual_hash": "7f5a1234...",
  "expected_hash": "bc931234...",
  "failure_index": 2,
  "last_valid_hash": "1d4c1234...",
  "reason": "HASH_MISMATCH",
  "record_count": 3,
  "status": "TAMPERED",
  "trust_state": "PARTIALLY_TRUSTED",
  "valid": false,
  "valid_until_index": 1
}
```

Other failure reasons include:

- `LEDGER_FILE_MISSING`
- `LEDGER_EMPTY`
- `INVALID_JSON`
- `INVALID_RECORD_TYPE`
- `PREV_HASH_MISMATCH`
- `HASH_MISMATCH`

## GET /ledger

Returns recent parsed ledger records for dashboard inspection. This endpoint is not a trust authority; use `/status` and `/verify` to decide whether ledger evidence is trusted.

Query parameters:

| Name | Default | Bounds | Description |
| --- | --- | --- | --- |
| `limit` | `50` | `1..500` | Number of recent parsed records to return |

```bash
curl 'http://127.0.0.1:8000/ledger?limit=5'
```

Response schema:

```json
{
  "records": [
    {
      "action": "CREATE",
      "argv": "touch /tmp/kalyx-api.txt",
      "comm": "touch",
      "hash": "dfc8c2d1...",
      "pid": 5000,
      "ppid": 4000,
      "prev_hash": "2aa8b73c...",
      "seq": 4,
      "session": "interactive_terminal",
      "source": "api",
      "target": "/tmp/kalyx-api.txt",
      "ts": "2026-05-20T14:12:30.142381+00:00",
      "user": "parth"
    }
  ],
  "count": 1
}
```

## GET /anchor/status

Compares the latest local checkpoint with the latest Raspberry Pi anchor for the configured ledger ID. Internally, this route calls the shared anchor client logic used by `kalyx anchor-status`.

Protection: unprotected read endpoint.

Configuration:

- `KALYX_ANCHOR_URL`, default `http://127.0.0.1:8081`
- `KALYX_LEDGER_ID`, default `kalyx-main-host`

```bash
curl http://127.0.0.1:8000/anchor/status
```

Response fields:

```json
{
  "status": "MATCH",
  "ledger_id": "kalyx-main-host",
  "anchor_url": "http://127.0.0.1:8081",
  "local_index": 3,
  "local_hash": "67f1c6e1...",
  "pi_index": 3,
  "pi_hash": "67f1c6e1...",
  "reason": null,
  "message": null
}
```

Status values include:

- `MATCH`: local checkpoint and Pi anchor agree.
- `AHEAD`: local checkpoint is newer than the Pi anchor.
- `BEHIND`: Pi anchor is newer than the local checkpoint.
- `DIVERGENCE`: checkpoint indices match but hashes differ.
- `NO_ANCHOR`: the Pi has no anchor for the configured ledger.
- `UNREACHABLE`: the host could not contact the Pi anchor API.

## POST /anchor

Creates or reuses a safe local checkpoint and submits that checkpoint boundary to the Raspberry Pi anchor authority. Internally, this route calls the shared anchor client logic used by `kalyx anchor`.

Protection: API key when configured.

Configuration:

- `KALYX_ANCHOR_URL`, default `http://127.0.0.1:8081`
- `KALYX_LEDGER_ID`, default `kalyx-main-host`

```bash
curl -X POST http://127.0.0.1:8000/anchor
```

Response fields:

```json
{
  "status": "ACCEPTED",
  "ledger_id": "kalyx-main-host",
  "anchor_url": "http://127.0.0.1:8081",
  "accepted": true,
  "checkpoint_index": 3,
  "checkpoint_hash": "67f1c6e1...",
  "pi_anchor_index": 2,
  "pi_anchor_hash": "8bd1024a...",
  "reason": null
}
```

Expected behavior:

- Trusted ledgers produce or reuse a local checkpoint before submission.
- Untrusted ledgers return `LEDGER_NOT_TRUSTED` without posting to the Pi.
- Pi rejections such as `REJECTED_STALE` are returned as response status values.
- Network failures return `UNREACHABLE` with a reason.

## POST /detect

Runs rule-based detection through `detect_and_persist_alerts`. Detection verifies the ledger first. If the ledger is not trusted, the endpoint returns `skipped: true` instead of an HTTP error.

```bash
curl -X POST http://127.0.0.1:8000/detect
```

Response schema:

```json
{
  "alerts": [],
  "reason": null,
  "skipped": false,
  "verification": {
    "status": "VALID",
    "valid": true
  },
  "written": 0
}
```

Skipped detection example:

```json
{
  "alerts": [],
  "reason": "LEDGER_NOT_TRUSTED",
  "skipped": true,
  "verification": {
    "reason": "LEDGER_FILE_MISSING",
    "status": "NO_LEDGER",
    "valid": false
  },
  "written": 0
}
```

## POST /ingest

Ingests exactly one payload. The request must include either `raw_line` or `event`, but not both.

### Structured Event Request

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "event": {
      "comm": "touch",
      "pid": 5000,
      "ppid": 4000,
      "argv": "touch /tmp/kalyx-api.txt",
      "ret": 0,
      "uid": 1000
    },
    "source": "api"
  }'
```

Structured event schema:

```json
{
  "event": {
    "argv": "touch /tmp/kalyx-api.txt",
    "comm": "touch",
    "pid": 5000,
    "ppid": 4000,
    "ret": 0,
    "uid": 1000
  },
  "source": "api"
}
```

Required event fields:

- `comm`: non-empty command name
- `pid`: positive integer
- `ppid`: non-negative integer
- `argv`: string

Optional event fields:

- `ret`: integer return value
- `uid`: non-negative integer
- additional fields accepted by the Pydantic event model

### Raw Line Request

Raw lines follow the execsnoop-style parser contract:

```text
UID COMM PID PPID RET ARGV
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "raw_line": "1000 touch 5000 4000 0 touch /tmp/kalyx-raw.txt",
    "source": "execsnoop_raw"
  }'
```

Successful response:

```json
{
  "ingested": true,
  "record": {
    "action": "CREATE",
    "argv": "touch /tmp/kalyx-api.txt",
    "comm": "touch",
    "hash": "dfc8c2d1...",
    "pid": 5000,
    "ppid": 4000,
    "prev_hash": "2aa8b73c...",
    "seq": 4,
    "source": "api",
    "target": "/tmp/kalyx-api.txt",
    "ts": "2026-05-20T14:12:30.142381+00:00"
  },
  "reason": null
}
```

Malformed request example:

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "event": {
      "comm": "touch",
      "pid": "not-a-number",
      "ppid": 1,
      "argv": "touch file.txt"
    },
    "source": "api"
  }'
```

Failure response:

```json
{
  "detail": [
    {
      "input": "not-a-number",
      "loc": ["body", "event", "pid"],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "type": "int_parsing"
    }
  ]
}
```

Pipeline validation failure example:

```json
{
  "detail": "Invalid event: comm must not be empty"
}
```

## GET /alerts

Returns persisted alerts from `logs/alerts.jsonl`.

```bash
curl http://127.0.0.1:8000/alerts
```

Response schema:

```json
{
  "alerts": [
    {
      "delta_seconds": 2.0,
      "details": "DELETE followed by CREATE within 300s",
      "seq_end": 12,
      "seq_start": 11,
      "session": "interactive_terminal",
      "severity": "HIGH",
      "target": "/tmp/kalyx-demo.txt",
      "ts_end": "2026-05-20T14:19:04.020000+00:00",
      "ts_start": "2026-05-20T14:19:02.020000+00:00",
      "type": "DELETE_CREATE",
      "user": "parth"
    }
  ],
  "count": 1
}
```

Detection can also be run from the CLI:

```bash
kalyx detect
```

## Raspberry Pi Anchor API

The anchor API is a separate FastAPI application started with `kalyx-anchor`. It is called by the host anchor client, not by Angular.

Base URL for local development:

```text
http://127.0.0.1:8081
```

| Method | Path | Protection | Description |
| --- | --- | --- | --- |
| `POST` | `/anchor` | Unprotected in current prototype | Store a checkpoint boundary in the Pi-side anchor chain |
| `GET` | `/anchor/latest?ledger_id=...` | Unprotected in current prototype | Return the latest anchor accepted for one ledger, or `404` when none exists |

### POST /anchor

Accepts a checkpoint boundary from the host and appends it to the Pi-side anchor chain when valid.

Expected behavior:

- `ACCEPTED` when a new checkpoint boundary is stored.
- `ALREADY_ANCHORED` when the same ledger checkpoint hash already exists.
- `REJECTED_STALE` when the submitted checkpoint index is behind the latest anchor for that ledger.
- `REJECTED_INVALID` when the existing anchor chain or submitted payload cannot be validated.

### GET /anchor/latest

Returns the latest Pi anchor for a ledger ID. This is the endpoint used by host anchor status comparison.
