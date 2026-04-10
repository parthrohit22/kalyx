# KALYX

## Verifiable Execution Integrity Platform  
### Make execution history provable.


## Overview

KALYX converts system execution activity into a tamper-evident, cryptographically verifiable ledger and performs contextual behavioral analysis on execution patterns.

Traditional logging assumes trust.  
KALYX makes trust testable.

Instead of asking:

> “What does the system say happened?”

KALYX asks:

> “Can this history still be trusted — and does it indicate suspicious behavior?”


## The Problem

System logs can be:

- Edited after compromise  
- Selectively deleted  
- Injected with fabricated events  
- Rewritten by privileged users  

Traditional systems provide visibility.  
They do not provide integrity guarantees.

KALYX transforms execution history into cryptographic evidence and interpretable behavioral signals.


## Core Integrity Model

Each execution event becomes a hash-linked record.

```json
{
  "event": { ... },
  "prev_hash": "...",
  "hash": "..."
}
```

Every record depends on the previous record’s hash.

This guarantees:

- Append-only history  
- Deterministic verification  
- Order preservation  
- Tamper detection  
- Trust-collapse localisation  

If any record is modified, verification fails at the earliest corrupted entry.


## Architecture

```
Event Source
      ↓
Ingestion Layer (eBPF / controlled input)
      ↓
Enrichment Layer (user, session, parent context)
      ↓
Normalization Layer (action + target extraction)
      ↓
Hash-Chained Ledger
      ↓
Verification Engine
      ↓
Behavioral Detection Engine
      ↓
Alert Persistence Layer
      ↓
CLI / API / UI
```


## CLI Usage

```bash
kalyx ingest
kalyx ingest-live
kalyx verify
kalyx status
kalyx inspect
kalyx detect
kalyx alerts
```

Example:

```bash
$ kalyx ingest-live
[INFO] Starting live eBPF ingestion...

$ kalyx inspect
# enriched + normalized events

$ kalyx detect
[!] Suspicious activity detected

type     : DELETE_CREATE
severity : HIGH
user     : parth
target   : a.txt

$ kalyx alerts
# persisted alert history
```


## Behavioral Detection

KALYX extends beyond integrity verification by detecting contextual execution patterns.

Detection operates on enriched and normalized events:

- action (CREATE, DELETE, MODIFY, EXEC)
- target (file or resource)
- user, session, and parent process context
- temporal relationships between events

### Current Detection Capabilities

- **DELETE → CREATE sequences**  
  Detects rapid overwrite or file replacement behavior

- **MODIFY burst patterns**  
  Detects repeated modifications within short intervals

- **DESTRUCTIVE burst activity**  
  Detects multiple destructive actions in constrained time windows

- **SCRIPTED_DESTRUCTIVE_ACTION**  
  Detects destructive actions executed from non-interactive or background contexts

Detection is rule-based and context-aware, enabling KALYX to move from passive logging to active forensic signal generation.


## Alert Model

Each detection produces a structured alert:

- type  
- severity  
- user  
- target  
- session  
- sequence range  
- timestamps  
- delta time  
- contextual details  

Alerts are persisted separately:

```
logs/alerts.jsonl
```

This ensures detection output is retained independently of runtime inspection.


## Completed Phases

| Phase | Description | Status |
|-------|------------|--------|
| Phase 0 | Hash-chained cryptographic ledger | ✅ |
| Phase 1 | Deterministic verification engine | ✅ |
| Phase 2 | Controlled ingestion pipeline | ✅ |
| Phase 3 | CLI packaging + reproducible tool | ✅ |
| Phase 4 | Operational CLI + inspection tooling | ✅ |
| Phase 5 | Semantic enrichment + normalization layer | ✅ |
| Phase 6 | Behavioral detection + alert persistence | ✅ |


## Security Boundary

KALYX guarantees:

- Integrity of stored execution history  
- Detection of modification and structural tampering  
- Deterministic verification of event sequences  
- Contextual behavioral anomaly detection  

KALYX does **not** guarantee:

- Protection against full root compromise  
- Authenticity of malicious but valid events  
- Complete detection of advanced adversarial behavior  
- Prevention of ledger reconstruction by privileged attackers  

Integrity is enforced.  
Authenticity depends on ingestion trust.


## Independent Anchor (Planned)

To prevent retrospective ledger reconstruction:

- Periodic root-hash export  
- External timestamping  
- Cryptographic signing  
- Independent storage (e.g., Raspberry Pi node)  

This introduces external trust anchoring beyond the primary system.


## Roadmap

**Detection Enhancements**
- Parent-child anomaly detection  
- Execution lineage modeling  
- Context-aware severity scoring  

**Backend API**
- POST /ingest  
- POST /verify  
- GET /status  
- GET /export  

**Web Application**
- Ledger health dashboard  
- Verification interface  
- Event explorer  
- Alert timeline  

**Real-Time Capture**
- eBPF stabilization  
- auditd integration  
- unified ingestion interface  


## Academic Contribution

KALYX demonstrates:

- Applied cryptographic integrity enforcement  
- Deterministic hash-domain design  
- Controlled ingestion boundaries  
- Semantic normalization of execution events  
- Contextual behavioral detection  
- Reproducible and modular system architecture  


## Vision

KALYX is not a logging tool.

It is a verifiable execution intelligence system.