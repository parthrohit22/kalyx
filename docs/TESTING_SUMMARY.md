# Testing Summary

KALYX tests focus on correctness properties that support the project's integrity claims. The suite is intentionally direct: each test category maps to a backend guarantee.

Run the suite:

```bash
python3 -m compileall kalyx
pytest -q
```

The Angular operations console is built separately:

```bash
cd frontend
npm install
npm run build
```

Frontend unit tests can be added with Angular's test runner. If tests are present, run:

```bash
cd frontend
npm test
```

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

The checkpoint tests prove:

- valid ledgers can write local checkpoints
- repeated checkpoint creation for the same ledger boundary is deduplicated
- a ledger truncated behind the latest checkpoint is reported as `UNTRUSTED`
- a tampered ledger with a valid prefix is reported as `PARTIALLY_TRUSTED`

Why it matters:

Hash-chain verification can prove whether the current file is internally consistent. Checkpoints add local memory of a previous trusted boundary, which lets KALYX flag truncation or replacement before external anchoring is available.

## API Route Tests

File:

- `kalyx/tests/test_api_endpoints.py`

The API route tests prove:

- status routes expose trust-state and checkpoint metadata
- ingest and verify route handlers share backend state
- verification route handling can create a checkpoint
- malformed ingestion payloads are rejected by the schema layer
- alerts route handling returns persisted alert data consistently

Why it matters:

CLI, API, and the Angular console should remain thin consumers of the same backend services. These tests guard against interface drift.

## Residual Test Gaps

Current tests emphasize backend integrity semantics. Useful future coverage would include:

- Angular component and route tests for the operations console
- typed alert schema validation once alert models are formalized
- incremental verification tests after segment checkpoints are introduced
