# KALYX

## Verifiable Execution Integrity Platform  
### Make execution history provable.


## Overview

KALYX converts system execution activity into a tamper-evident, cryptographically verifiable ledger, and performs behavioral analysis on execution patterns.

Traditional logging assumes trust.  
KALYX makes trust testable.

Instead of asking:

> “What does the system say happened?”

KALYX asks:

> “Can this history still be trusted — and does it show suspicious behavior?”


## The Problem

System logs can be:

- Edited after compromise  
- Selectively deleted  
- Injected with fabricated events  
- Rewritten by privileged users  

Traditional systems provide visibility.  
They do not provide integrity guarantees.

KALYX transforms execution history into cryptographic evidence.


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
Enrichment Layer (user, session, context)
      ↓
Normalization Layer (action, target extraction)
      ↓
Hash-Chained Ledger
      ↓
Verification Engine
      ↓
Behavioral Detection Engine
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
```

Example:

```bash
$ kalyx ingest-live
[INFO] Starting live eBPF ingestion...

$ kalyx inspect
# shows enriched + normalized events

$ kalyx detect
[!] Suspicious activity detected
type    : DELETE_CREATE
user    : parth
target  : a.txt
```


## Behavioral Detection

KALYX extends beyond integrity verification by detecting suspicious execution patterns.

Current detection capabilities include:

- DELETE → CREATE sequences (possible file manipulation)
- Repeated command execution patterns
- Basic behavioral anomalies

Detection is based on normalized event semantics:

- action (CREATE, DELETE, MODIFY, EXEC)
- target (file or resource)
- execution sequence

This enables KALYX to move from passive logging to active forensic signal generation.


## Completed Phases

| Phase | Description | Status |
|-------|------------|--------|
| Phase 0 | Hash-chained cryptographic ledger | ✅ |
| Phase 1 | Deterministic verification engine | ✅ |
| Phase 2 | Controlled ingestion pipeline | ✅ |
| Phase 3 | CLI packaging + reproducible tool | ✅ |
| Phase 4 | Operational status + improved feedback | ✅ |
| Phase 5 | eBPF live ingestion + enrichment | ✅ |
| Phase 6 | Behavioral normalization + detection engine | ✅ |


## Security Boundary

KALYX guarantees:

- Integrity of stored execution history  
- Detection of modification  
- Detection of structural tampering  
- Basic behavioral anomaly detection  

KALYX does **not** guarantee:

- Protection against full root compromise  
- Authenticity of malicious but valid events  
- Detection of all advanced adversarial behavior  

Integrity is enforced.  
Authenticity depends on ingestion trust.


## Independent Anchor (Planned)

To prevent retrospective ledger rewriting:

- Periodic root-hash export  
- Time-stamped anchor storage  
- Cryptographic signing  
- Independent Raspberry Pi node  

This introduces external trust anchoring beyond the primary system.


## Roadmap

**Backend API**
- POST /ingest  
- POST /verify  
- GET /status  
- GET /export  

**Web Application**
- Ledger health dashboard  
- Verification interface  
- Event explorer  
- Evidence export bundle  

**Real-Time Capture**
- eBPF or auditd integration  
- Stable ledger contract preserved  


## Academic Contribution

KALYX demonstrates:

- Applied cryptographic integrity design  
- Deterministic hash-domain enforcement  
- Controlled ingestion boundaries  
- Behavioral anomaly detection  
- Reproducible software packaging  
- Explicit security boundary modelling  


## Vision

KALYX is not a logging tool.

It is a trust validation system.