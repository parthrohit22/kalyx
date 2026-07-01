# KALYX Architecture

KALYX v0.6.2 is organized as an integrity and anchoring workflow with thin interfaces. The core design goal is to keep verification, chaining, ingestion, detection, and anchor semantics in shared services so the CLI, FastAPI API, and Angular operations console all reflect the same backend behaviour.

## Layered Architecture

```mermaid
flowchart TD
    subgraph InterfaceLayer["Interface Layer"]
        CLI["CLI<br/>kalyx commands"]
        API["FastAPI API<br/>route adapter"]
        Frontend["Angular Frontend<br/>operations console"]
    end

    subgraph ServiceLayer["Shared Service Layer"]
        Pipeline["Pipeline Service<br/>parse -> validate -> enrich -> normalize -> chain"]
        Ledger["Ledger Service<br/>load -> verify -> checkpoint -> status -> export"]
        Detection["Detection Service<br/>verify ledger chain -> replay window -> persist alerts"]
        AnchorClient["Anchor Client<br/>checkpoint submit -> status compare"]
    end

    subgraph CoreLayer["Core and Engine Layer"]
        Chain["chain.py<br/>file-lock append<br/>canonical hashing"]
        Verify["ledger.py / verify.py<br/>deterministic verification<br/>corruption boundary"]
        Rules["detector.py / alerts.py<br/>rules and deduplication"]
        Engine["parser.py / enrichment.py<br/>execsnoop parsing<br/>local process context"]
        Schemas["models/schema.py<br/>Pydantic contracts"]
    end

    subgraph Storage["Local Append-Only Storage"]
        ExecLedger[("logs/exec_chain.jsonl")]
        Checkpoints[("logs/checkpoints.jsonl")]
        AlertLog[("logs/alerts.jsonl")]
        StatusFile[("logs/.kalyx_status.json")]
    end

    subgraph ExternalAnchor["Raspberry Pi Anchor Authority"]
        AnchorAPI["Anchor API<br/>kalyx-anchor"]
        AnchorChain[("anchors/anchor_chain.jsonl")]
    end

    CLI --> Pipeline
    API --> Pipeline
    Frontend --> API

    CLI --> Ledger
    API --> Ledger
    CLI --> Detection
    API --> Detection
    CLI --> AnchorClient
    API --> AnchorClient

    Pipeline --> Engine
    Pipeline --> Schemas
    Pipeline --> Chain
    Chain --> ExecLedger

    Ledger --> Verify
    Verify --> ExecLedger
    Ledger --> Checkpoints
    Ledger --> StatusFile

    Detection --> Ledger
    Detection --> Rules
    Rules --> AlertLog

    AnchorClient --> Ledger
    AnchorClient --> Checkpoints
    AnchorClient --> AnchorAPI
    AnchorAPI --> AnchorChain
    AnchorAPI -. latest anchor .-> AnchorClient
```

## Component Responsibilities

- `kalyx/api/main.py`: FastAPI route adapter and minimal API status page.
- `frontend/`: Angular operations console with routing, typed API service, forms, tables, filters, drawers, and evidence views.
- `kalyx/cli/app.py`: command dispatch and terminal rendering.
- `kalyx/models/schema.py`: API request and response contracts.
- `kalyx/services/pipeline.py`: shared parse, validate, enrich, normalize, and chain workflow.
- `kalyx/services/ledger.py`: ledger loading, deterministic verification, local checkpoints, trust-state classification, status, and export services.
- `kalyx/services/detection.py`: hash-chain-verified record replay, deterministic rule execution, and alert persistence.
- `kalyx/services/anchor_client.py`: host-side checkpoint submission and local-vs-Pi anchor status comparison.
- `kalyx/anchor/api.py`: Raspberry Pi FastAPI anchor authority for checkpoint submission and latest-anchor lookup.
- `kalyx/anchor/storage.py`: Pi-side append-only anchor chain validation and persistence.
- `kalyx/core/chain.py`: file-lock protected append-only hash chaining.
- `kalyx/core/detector.py`: deterministic behavioural rules and in-memory alert deduplication.
- `kalyx/core/alerts.py`: file-lock protected alert persistence and persisted alert deduplication.
- `kalyx/engine/parser.py`: execsnoop-style raw line parsing.
- `kalyx/engine/enrichment.py`: local user, TTY, session, and parent process enrichment.
- `kalyx/core/normalize.py`: command normalization into `action` and `target`.

## Shared Service Pipeline

Ingestion follows one backend path regardless of interface:

```text
raw_line or event
  -> parse raw line when supplied
  -> validate required fields
  -> enrich from local process context
  -> normalize command/action/target
  -> validate normalized event
  -> append to hash-chained ledger
```

The API, CLI, and Angular frontend do not implement their own ledger logic. They call or display results from `ingest_payload`, `verify_ledger_state`, `create_checkpoint`, `get_status_summary`, `detect_and_persist_alerts`, `load_ledger_records`, `load_alerts`, `submit_latest_checkpoint_to_anchor`, and `compare_anchor_status`.

The Angular console is the primary local demo interface, but it remains a presentation layer. It calls FastAPI endpoints for status, verification, ingestion, detection, alert retrieval, ledger inspection, anchor status, and anchor submission. It never decides whether evidence is trusted, and it never calls the Raspberry Pi anchor service directly.

## Trust Boundaries

```text
Untrusted input
  raw event lines
  structured API payloads
  local process metadata
        |
        v
Validation boundary
  required field checks
  integer coercion
  positive pid checks
  non-empty command checks
        |
        v
Local integrity boundary
  canonical record hashing
  previous-hash linking
  append serialization
  deterministic verification
```

KALYX can verify the continuity of records it has accepted. It does not prove that an external event source was truthful. Ingestion authenticity is outside the current boundary.

Local checkpoints add another local boundary: KALYX can compare the current ledger against the latest checkpoint and report if the ledger has been truncated or replaced behind that checkpoint. Because checkpoints are still local files, an independently stored anchor is needed to compare local state against a boundary held elsewhere. External anchoring does not attest the host runtime or prevent full host compromise.

External anchoring adds a separate authority boundary:

```text
Host verified checkpoint
        |
        v
Host Anchor Client
        |
        v
Raspberry Pi Anchor API
        |
        v
Pi append-only anchor chain
```

The host submits checkpoint boundaries and later compares the latest local checkpoint against the latest Pi anchor for the configured ledger ID. The Pi stores checkpoint boundaries; it does not verify full host state or replace local ledger verification.

## Concurrency Model

Ledger appends are serialized with an exclusive `fcntl` file lock in `chain_event`.

While holding the lock, KALYX:

1. Reads existing ledger lines.
2. Finds the last valid JSON object.
3. Reads the previous hash.
4. Assigns the next sequence number.
5. Computes the canonical record hash.
6. Appends the JSONL line.
7. Flushes and fsyncs the file.

This prevents concurrent writers from reading the same previous hash and producing duplicate or conflicting chain links.

Alert persistence uses the same file-lock pattern. While holding the alert lock, KALYX reloads existing alert signatures and only writes alerts whose stable signature is new.

## Local Checkpoint Model

Checkpoints are append-only records in `logs/checkpoints.jsonl`. A checkpoint is written only after successful verification and only when the current ledger does not conflict with the latest checkpoint.

Each checkpoint records:

- `record_count`
- `last_seq`
- `last_hash`
- `previous_checkpoint_hash`
- `checkpoint_hash`
- verification status and timestamp metadata

If a later ledger has fewer records than the checkpoint or the checkpointed record no longer has the checkpointed hash, KALYX reports a checkpoint gap and marks the operational `trust_state` as `UNTRUSTED`.

## Verification Semantics

Verification is deterministic and conservative.

For each ledger line, KALYX checks:

- the line is valid JSON
- the decoded value is an object
- `prev_hash` equals the expected previous hash
- `hash` equals the recomputed canonical hash

On the first failure, verification stops and returns:

- `status`
- `reason`
- `record_count`
- `failure_index`
- `valid_until_index`
- `last_valid_hash`
- mismatch-specific expected and actual values when available
- `trust_state`, derived from verification and checkpoint continuity

The failed record and every following record are treated as untrusted.

## Corruption Handling

KALYX distinguishes corruption classes:

- `INVALID_JSON`: a ledger line cannot be decoded.
- `INVALID_RECORD_TYPE`: a line decodes to something other than an object.
- `PREV_HASH_MISMATCH`: the chain link does not point to the expected previous hash.
- `HASH_MISMATCH`: the record payload no longer matches its stored hash.

This gives reviewers an exact corruption boundary rather than a vague pass/fail result.

## Detection Separation

Detection is intentionally separate from integrity verification.

`detect_and_persist_alerts` performs full-ledger hash-chain verification first. If that verification fails, detection is skipped with `LEDGER_NOT_TRUSTED`. This prevents KALYX from generating behavioural alerts from a malformed or hash-chain-invalid ledger.

The detection service does not currently load `logs/checkpoints.jsonl` or evaluate checkpoint continuity. An internally valid ledger that has fallen behind a local checkpoint can therefore be marked `UNTRUSTED` by status and ingestion checks while still passing detection's narrower hash-chain gate.

When verification succeeds, detection replays recent records, normalizes them, runs deterministic rules, deduplicates alerts, and persists new alerts to `logs/alerts.jsonl`.

`GET /ledger` exposes recent parsed ledger records for inspection in the Angular console. It is not a trust authority; trust decisions still come from deterministic verification and status metadata.

## Angular Request Flow Diagram

```mermaid
sequenceDiagram
    participant Angular as Angular Dashboard
    participant API as Host FastAPI API
    participant Pipeline as Pipeline Service
    participant Ledger as Ledger File
    participant Verify as verify_ledger_state
    participant Detect as Detection Service
    participant AnchorClient as Anchor Client
    participant Pi as Raspberry Pi Anchor API

    Angular->>API: POST /ingest
    API->>Pipeline: ingest_payload()
    Pipeline->>Ledger: validate, normalize, hash, append
    API-->>Angular: chained record

    Angular->>API: POST /verify
    API->>Verify: verify_ledger_state()
    Verify->>Ledger: read lines in order
    API-->>Angular: verification and checkpoint state

    Angular->>API: POST /detect
    API->>Detect: detect_and_persist_alerts()
    Detect->>Verify: verify full ledger hash chain
    Detect->>Ledger: replay verified records
    API-->>Angular: detection and alert summary

    Angular->>API: POST /anchor
    API->>AnchorClient: submit_latest_checkpoint_to_anchor()
    AnchorClient->>Verify: verify full ledger hash chain
    AnchorClient->>Ledger: validate continuity and create or reuse checkpoint
    AnchorClient->>Pi: POST /anchor
    Pi-->>AnchorClient: accepted, duplicate, or rejection state
    AnchorClient-->>API: submission result
    API-->>Angular: anchor submission result

    Angular->>API: GET /anchor/status
    API->>AnchorClient: compare_anchor_status()
    AnchorClient->>Ledger: load latest local checkpoint
    AnchorClient->>Pi: GET /anchor/latest
    Pi-->>AnchorClient: latest anchor or missing/unreachable state
    AnchorClient-->>API: comparison state
    API-->>Angular: comparison state
```

## Data Flow Diagram

```mermaid
flowchart LR
    Source[Event Source] --> Validation[Validation]
    Validation --> Enrichment[Enrichment]
    Enrichment --> Normalize[Normalization]
    Normalize --> Chain[Hash Chain Append]
    Chain --> Ledger[(exec_chain.jsonl)]
    Ledger --> Verify[Deterministic Verification]
    Verify --> Checkpoint[(checkpoints.jsonl)]
    Checkpoint --> AnchorClient[Host Anchor Client]
    AnchorClient --> PiAnchor[Raspberry Pi Anchor API]
    PiAnchor --> AnchorChain[(anchor_chain.jsonl)]
    Ledger --> Detect[Rule Detection]
    Verify -. hash-chain gate .-> Detect
    Detect --> Alerts[(alerts.jsonl)]
    Verify --> Interfaces[CLI / API / Angular]
    AnchorClient --> Interfaces
    Alerts --> Interfaces
```
