# Detection Engine

KALYX uses deterministic rule-based behavioural detection. The goal is not to classify threats with a hidden score. The goal is to turn trusted ledger records into explainable alerts when specific, testable patterns appear.

## Why Rule-Based Detection

Rule-based detection was chosen because it is:

- deterministic
- easy to test
- easy to explain
- stable across repeated runs
- suitable for a small integrity-focused backend project

KALYX intentionally avoids ML, external threat intelligence, and opaque scoring. Those would add claims and dependencies that do not match the current trust boundary.

## Detection Preconditions

Detection runs only after successful ledger verification. It can be triggered from the CLI, the FastAPI API, or the Angular console, but all interfaces call the same shared detection service.

`detect_and_persist_alerts` first calls `verify_ledger_state`. If verification fails, detection returns:

```json
{
  "alerts": [],
  "reason": "LEDGER_NOT_TRUSTED",
  "skipped": true,
  "written": 0
}
```

This prevents KALYX from generating behavioural alerts from corrupted evidence.

## Deterministic Semantics

Rules operate over normalized records. Events are sorted deterministically by:

1. numeric `seq` when present
2. timestamp string as a fallback ordering component

Each rule emits stable alert dictionaries with:

- `type`
- `severity`
- `user`
- `target`
- `details`
- `seq_start`
- `seq_end`
- `ts_start`
- `ts_end`
- `delta_seconds`
- `session`

## Implemented Rules

### DELETE_CREATE

Detects a `DELETE` followed by `CREATE` on the same known target by the same known user, or by two unknown users, within a configured time window.

Default window:

```text
300 seconds
```

Severity:

```text
HIGH
```

### MODIFY_BURST

Detects repeated `MODIFY` actions against the same known target within a short window.

Default window:

```text
10 seconds
```

Default threshold:

```text
2 events
```

Severity:

```text
MEDIUM
```

### DESTRUCTIVE_BURST

Detects multiple destructive actions by the same user/session within a short window.

Destructive actions:

```text
DELETE
MODIFY
```

Default window:

```text
15 seconds
```

Default threshold:

```text
3 events
```

Severity:

```text
HIGH
```

### SCRIPTED_DESTRUCTIVE_ACTION

Detects `DELETE` or `MODIFY` actions launched by scripting parents outside interactive terminal sessions.

Risky parents:

```text
python
python3
sh
bash
perl
ruby
```

Severity:

```text
HIGH
```

## Replay-Safe Alerting

Detection may be run repeatedly. To avoid duplicate persisted alerts, KALYX computes a stable alert signature from:

- `type`
- `severity`
- `user`
- `target`
- `seq_start`
- `seq_end`
- `session`

Alert persistence holds an exclusive file lock, reloads existing signatures while locked, and only appends new signatures.

This protects against duplicate writes during repeated or concurrent detection runs.

## Explainability

Each alert includes a human-readable `details` field plus sequence and timestamp boundaries. Reviewers can map an alert back to the exact ledger range that produced it.

Example:

```json
{
  "delta_seconds": 2.0,
  "details": "DELETE followed by CREATE within 300s",
  "seq_end": 12,
  "seq_start": 11,
  "session": "interactive_terminal",
  "severity": "HIGH",
  "target": "/tmp/kalyx-demo.txt",
  "type": "DELETE_CREATE",
  "user": "parth"
}
```

## Limitations

The detection engine is heuristic and intentionally limited.

It does not:

- prove malicious intent
- use threat intelligence
- detect every suspicious process pattern
- authenticate source events
- run if the ledger is not trusted
- index the full ledger for large historical queries

These limits are part of the design. KALYX favours deterministic, explainable backend behaviour over broad but weak claims.
