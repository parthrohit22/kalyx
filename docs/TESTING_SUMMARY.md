# Testing Summary

KALYX tests focus on correctness properties that support the project's integrity claims. The suite is intentionally direct: each test category maps to a backend guarantee.

Run the suite:

```bash
python3 -m pip install -e . pytest
python3 -m compileall kalyx
python3 -m pytest -q
```

Runtime dependencies are declared in `pyproject.toml`. `requirements.txt` is a
local backend development convenience file that installs this checkout editable
plus `pytest`.

The Angular operations console is built separately:

```bash
cd frontend
npm ci
npm run build
```

Frontend unit tests live under `frontend/src/app/**/*.spec.ts` and can be run with Angular's test runner:

```bash
cd frontend
npm test
```

## Continuous Integration

GitHub Actions runs automated validation on pull requests and pushes to `main`.
The workflow is intentionally small and only checks the project baseline:

- install backend dependencies with `python3 -m pip install -e . pytest`
- compile Python sources with `python3 -m compileall kalyx`
- run backend tests with `python3 -m pytest -q`
- install frontend dependencies with `npm ci`
- build the Angular operations console with `npm run build`

The CI workflow does not deploy, publish Docker images, upload coverage, or run
browser-based Angular/Karma tests. Browser tests are intentionally excluded until
their Chrome/ChromeHeadless setup is stable enough for CI.

## Integrity Verification Tests

Files:

- `kalyx/tests/test_ledger_integrity.py`
- `kalyx/tests/test_ledger_corruption.py`

What they prove:

- A valid ledger record verifies successfully.
- A modified payload is detected as `HASH_MISMATCH`.
- Verification reports the correct `failure_index`.
- Verification reports the correct `valid_until_index`.
- The last trusted boundary is preserved after corruption.

Why it matters:

An integrity ledger is only useful if it can distinguish trusted history from the first untrusted record. These tests prevent verification from becoming a shallow boolean check.

## Tamper Detection Tests

The tamper tests rewrite ledger content after append and then run deterministic verification.

They prove:

- stored hashes are not decorative metadata
- canonical recomputation detects payload edits
- the system reports `TAMPERED` rather than silently loading modified records

## Corruption Tests

Corruption coverage includes:

- truncated JSON lines
- invalid JSON in the middle of the ledger
- record hash corruption
- previous-hash corruption

What they prove:

- malformed ledger content is treated as corruption
- verification stops at the first corrupted entry
- chain-link corruption is reported separately from payload-hash corruption

Why it matters:

Operational investigations need a boundary. If entry 2 is malformed, entry 1 may still be trusted while entry 2 and everything after it should not be.

## Concurrent Append Tests

File:

- `kalyx/tests/test_ledger_integrity.py`

The concurrency test writes 100 events through a `ThreadPoolExecutor`.

It proves:

- concurrent writers do not assign duplicate sequence positions
- concurrent writers do not reuse the same previous hash
- the ledger remains valid after parallel append pressure

Why it matters:

Without locking around previous-hash lookup and append, two writers could both link to the same previous record and break deterministic verification.

## Malformed Input Tests

File:

- `kalyx/tests/test_pipeline_validation.py`

The pipeline validation tests prove that KALYX rejects:

- missing required fields
- invalid PID values
- blank command names

They also prove that valid structured events flow through the shared pipeline and receive `hash` and `prev_hash` fields.

Why it matters:

Bad evidence should not become hash-protected ledger state. Validation is part of the trust boundary.

## Detection Rule Tests

File:

- `kalyx/tests/test_detection_rules.py`

The detection tests cover:

- delete followed by create on the same target
- delete/create outside the configured window
- repeated modify events in a short window
- destructive action bursts
- scripted destructive actions in non-interactive sessions
- interactive scripted activity that should not alert

What they prove:

- rule output is deterministic
- rules respect time windows and session context
- detection produces explainable alert types and severities

Why it matters:

The detection engine is deliberately rule-based. Tests make the expected semantics visible and reviewable.

## Alert Persistence Tests

File:

- `kalyx/tests/test_alert_persistence.py`

The alert persistence tests prove:

- duplicate alerts are written once
- distinct alert signatures are preserved
- concurrent duplicate alert writes result in one persisted alert

Why it matters:

Detection may be run repeatedly from different interfaces. Replay-safe persistence prevents the alert log from growing with duplicate evidence.

## Checkpoint And Trust-State Tests

File:

- `kalyx/tests/test_checkpoint_integrity.py`
- `kalyx/tests/test_ingestion_trust_gate.py`

The checkpoint tests prove:

- valid ledgers can write local checkpoints
- repeated checkpoint creation for the same ledger boundary is deduplicated
- a ledger truncated behind the latest checkpoint is reported as `UNTRUSTED`
- a tampered ledger with a valid prefix is reported as `PARTIALLY_TRUSTED`
- ingestion is blocked when the current ledger or checkpoint state is not trusted

Why it matters:

Hash-chain verification can prove whether the current file is internally consistent. Checkpoints add local memory of a previous trusted boundary, which lets KALYX flag truncation or replacement before external anchoring is available.

## Anchor Service And Client Tests

Files:

- `kalyx/tests/test_anchor_service.py`
- `kalyx/tests/test_anchor_status.py`
- `kalyx/tests/test_cli_anchor.py`

The anchor tests prove:

- the Raspberry Pi anchor service appends checkpoint boundaries to its own chain
- duplicate checkpoint submissions return `ALREADY_ANCHORED`
- stale checkpoint submissions return `REJECTED_STALE`
- broken Pi-side anchor chains reject new anchors
- latest-anchor lookup returns the newest anchor for one ledger
- anchor status comparison reports `MATCH`, `AHEAD`, `BEHIND`, `DIVERGENCE`, `NO_ANCHOR`, and `UNREACHABLE`
- CLI anchor commands use `KALYX_ANCHOR_URL` and `KALYX_LEDGER_ID`

Why it matters:

External anchoring is only useful if the host and Pi agree on checkpoint boundaries and expose disagreement without requiring a live Pi in the test suite.

## API Route Tests

File:

- `kalyx/tests/test_api_endpoints.py`

The API route tests prove:

- status routes expose trust-state and checkpoint metadata
- ingest and verify route handlers share backend state
- verification route handling can create a checkpoint
- malformed ingestion payloads are rejected by the schema layer
- alerts route handling returns persisted alert data consistently
- `GET /anchor/status` returns comparison, no-anchor, and unreachable states through the host API wrapper
- `POST /anchor` returns accepted submissions, Pi rejection states, and untrusted-ledger states without requiring a real Pi

Why it matters:

CLI, API, and the Angular console should remain thin consumers of the same backend services. These tests guard against interface drift.

## API Authentication Tests

File:

- `kalyx/tests/test_api_auth.py`

The API auth tests prove:

- operational routes such as `/ingest`, `/verify`, `/detect`, and `/anchor` are protected when `KALYX_API_KEY` is configured
- read routes such as `/status`, `/alerts`, `/ledger`, and `/anchor/status` remain unprotected
- missing or invalid keys return `401`
- authentication failures block operational side effects

Why it matters:

The API-key mechanism is deliberately lightweight, but protected routes still need consistent enforcement across normal evidence operations and anchor submission.

## Angular API Service Tests

Files:

- `frontend/src/app/core/api/kalyx-api.service.spec.ts`
- `frontend/src/app/core/state/dashboard-state.service.spec.ts`

The Angular tests prove:

- configured API keys are attached to protected frontend requests
- 401 responses produce a clear frontend error message
- Angular calls host `/anchor/status` and host `/anchor`
- Angular does not construct Raspberry Pi anchor API URLs
- trust-state display mapping does not upgrade backend `UNTRUSTED` states

## Residual Test Gaps

Current tests emphasize backend integrity semantics and typed Angular service behavior. They do not claim:

- Angular component and route tests for the operations console
- formal typed alert schema validation
- incremental verification beyond current full-ledger verification
