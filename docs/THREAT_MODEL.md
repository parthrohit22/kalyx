# Threat Model

KALYX has a narrow trust boundary. It provides local tamper-evident ledger verification for records it accepts. It does not provide source authentication, malware prevention, or complete host attestation.

## Assets

- `logs/exec_chain.jsonl`: hash-chained execution ledger.
- `logs/.kalyx_status.json`: last verification status metadata.
- `logs/checkpoints.jsonl`: local checkpoint history for previously verified ledger boundaries.
- `logs/alerts.jsonl`: persisted detection alerts.
- shared backend services that perform ingestion, verification, and detection.

## Trusted Components

Within the current model, KALYX trusts:

- local Python runtime while KALYX is executing
- KALYX source code and installed dependencies
- local filesystem semantics needed for append, flush, fsync, and `fcntl` locks
- validation, canonical hashing, and verification code
- process metadata read from `/proc` as best-effort local context

These are engineering assumptions for a local integrity project, not host-compromise guarantees.

## Untrusted Components

KALYX treats these as untrusted or only partially trusted:

- raw execsnoop lines
- structured API ingestion payloads
- sample log contents
- Angular-console-submitted test events
- malformed ledger lines
- persisted alerts loaded from disk
- event source truthfulness
- callers that know the optional local API key, because the key gates operational
  API access but does not prove event truth

## Ingestion Assumptions

KALYX validates event structure before append, but it does not prove the event source is authentic.

It assumes:

- an accepted event is the payload KALYX received
- required fields can be validated for shape and type
- enrichment is useful context, not authoritative proof
- if `KALYX_API_KEY` is configured, protected operational API requests have
  presented the shared local API key

It does not assume:

- a raw line came from a trusted kernel source
- an API caller is a known user or trusted event source
- a process event cannot be forged before ingestion

When `KALYX_API_KEY` is unset, local API development remains open. When it is set,
the key is lightweight local API protection, not full authentication, RBAC, source
attestation, or tamper-proofing.

## Ledger Assumptions

The ledger model assumes:

- records are appended locally to JSONL storage
- each record includes a previous hash and canonical record hash
- verification starts from a fixed genesis hash
- any local payload edit that does not also produce a consistent chain will be detected
- local checkpoints can record previous trusted ledger boundaries

Without external anchoring, KALYX cannot prove that an attacker did not rewrite the complete ledger history, checkpoints, and all local metadata.

## Checkpoint Assumptions

Local checkpoints are useful local memory, not independent trust anchors.

KALYX assumes:

- a checkpoint written after verification records a trusted local boundary
- a later ledger should still contain the checkpointed hash at the checkpointed record count
- a ledger that falls behind the latest checkpoint is suspicious even if it is internally valid

KALYX does not assume:

- local checkpoints survive full host compromise
- local checkpoints are equivalent to Raspberry Pi or remote anchoring
- deleting both ledger and checkpoints is detectable without an external copy

## Replay Assumptions

Detection is replay-safe in the alert persistence sense:

- repeated rule execution can recompute the same alerts
- stable alert signatures prevent duplicate persisted alerts
- alert writes are serialized with a file lock

Replay-safe alerting does not mean event replay attacks are impossible. It means repeated detection over the same trusted ledger records should not duplicate persisted alerts.

## Local Compromise Assumptions

Out of scope:

- full host compromise
- attacker control of the Python runtime
- attacker control of KALYX source code
- attacker control of the filesystem below KALYX
- attacker rewriting the entire ledger plus all local status metadata
- attacker rewriting the entire ledger plus all local checkpoint metadata

In those cases, local-only verification is not sufficient. External anchoring or remote attestation would be needed for stronger guarantees.

## Detectable Attacks

KALYX can detect:

- a modified ledger record whose stored hash is not updated correctly
- a broken previous-hash link
- invalid JSON inserted into the ledger
- truncated JSON lines
- non-object ledger entries
- truncation or replacement behind the latest local checkpoint
- duplicate alert persistence attempts with the same stable alert signature
- deterministic behavioural patterns implemented by the rule engine

Examples of detectable behavioural patterns:

- delete followed by create on the same target within a time window
- repeated modifications against the same target
- bursts of destructive actions
- destructive actions launched by scripting parents in non-interactive sessions

## Undetectable or Not Guaranteed

KALYX does not currently detect or guarantee protection against:

- forged events before ingestion
- unauthenticated API callers
- complete ledger rewrite with recomputed hashes and no external anchor
- deletion of the whole ledger and local checkpoints followed by replacement
- tampering by an attacker with full local filesystem and runtime control
- kernel-level compromise
- malware prevention or process blocking
- authoritative identity of the user or process that generated an event

## Current Security Boundary

```text
KALYX guarantees local deterministic verification of accepted records.
KALYX does not guarantee authenticity of the original event source.
```

That sentence is the core boundary. The design keeps this explicit so the project remains honest and reviewable.
