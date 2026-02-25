# KALYX

## Verifiable Execution Integrity Platform  
### Make execution history provable.


## Overview

KALYX converts system execution activity into a tamper-evident, cryptographically verifiable ledger.

Traditional logging assumes trust.  
KALYX makes trust testable.

Instead of asking:

> “What does the system say happened?”

KALYX asks:

> “Can this history still be trusted?”


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
Ingestion Layer
      ↓
Hash-Chained Ledger
      ↓
Verification Engine
      ↓
CLI / API / UI
```

Current ingestion: controlled execution input  
Planned ingestion: eBPF / auditd / real-time streams  

The ledger contract remains stable across all ingestion methods.


## CLI Usage

```bash
kalyx ingest
kalyx verify
kalyx status
```

Example:

```bash
$ kalyx ingest
[+] Ingested 3 events
[+] Ledger updated

$ kalyx verify
[✓] Ledger verified — no tampering detected

$ kalyx status
Ledger file : logs/exec_chain.jsonl
Entries     : 3
Last hash   : 1a9af64...
```


## Completed Phases

| Phase | Description | Status |
|-------|------------|--------|
| Phase 0 | Hash-chained cryptographic ledger | ✅ |
| Phase 1 | Deterministic verification engine | ✅ |
| Phase 2 | Controlled ingestion pipeline | ✅ |
| Phase 3 | CLI packaging + reproducible tool | ✅ |
| Phase 4 | Operational status + improved feedback | ✅ |


## Security Boundary

KALYX guarantees:

- Integrity of stored execution history  
- Detection of modification  
- Detection of deletion  
- Detection of naive insertion  
- Strict chronological linkage  

KALYX does **not** guarantee:

- Protection against full root compromise  
- Authenticity of malicious but valid events  
- Prevention of system takeover  

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
- Attack simulation validation  
- Reproducible software packaging  
- Explicit security boundary modelling  


## Vision

KALYX is not a logging tool.

It is a trust validation system.