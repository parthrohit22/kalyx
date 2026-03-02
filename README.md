# KALYX
## Verifiable Execution Integrity Platform
### Make execution history *verifiable*.

## Overview
KALYX converts execution activity into a **tamper-evident**, **cryptographically verifiable** ledger.

Traditional logging assumes stored history remains trustworthy.  
KALYX makes that trust **testable**.

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

Most logging stacks prioritise visibility, storage, and search.  
They do not *by default* provide a deterministic way to **prove** whether history was modified after capture.

KALYX treats execution history as evidence: if it changes, the change becomes detectable.

## Core Integrity Model
Each execution event is written as a hash-linked record.

```json
{
  "event": { ... },
  "prev_hash": "...",
  "hash": "..."
} 
```

How it works:
	•	Each record includes the previous record’s hash (prev_hash)
	•	A new hash is computed over a canonical representation of the record
	•	Verification recomputes hashes from the beginning and checks link consistency

What this provides (within the defined trust boundary):
	•	Detects post-capture modification of records
	•	Detects deletion/reordering (chain break)
	•	Detects naive insertion (prev_hash mismatch)
	•	Identifies the earliest point where integrity no longer holds (“trust collapse”)

If any record is changed without correctly recomputing the chain, verification fails.

Architecture

Event Source
   ↓
Ingestion Layer
   ↓
Hash-Chained Ledger (JSONL)
   ↓
Verification Engine
   ↓
CLI (current) → API/UI (planned)

Current ingestion: controlled execution input (repeatable testing)
Planned ingestion options: auditd / eBPF / real-time streams
The ledger contract is designed to remain stable across ingestion sources.

CLI Usage

kalyx ingest
kalyx verify
kalyx status

Example:

$ kalyx ingest
[+] Ingested 3 events
[+] Ledger updated

$ kalyx verify
[✓] Ledger verified — no tampering detected

$ kalyx status
Ledger file : logs/exec_chain.jsonl
Entries     : 3
Last hash   : 1a9af64...

Implemented Phases (Current)

Phase	Description	Status
0	Hash-chained ledger core	✅
1	Deterministic verification + tamper detection	✅
2	Controlled ingestion pipeline	✅
3	CLI packaging + reproducible tool	✅
4	Status command + improved ingestion feedback	✅

Security Boundary (Important)

KALYX does provide:
	•	Integrity verification of stored execution history
	•	Detection of modification, deletion, reordering, naive insertion
	•	Deterministic verification that localises trust collapse

KALYX does not provide (by itself):
	•	Protection against full root compromise
	•	Authenticity guarantees if the ingestion source is malicious
	•	Prevention of system takeover

Key distinction:
	•	Integrity = “Was the recorded history modified after capture?”
	•	Authenticity = “Did the event truly occur?”
KALYX focuses on integrity; authenticity depends on the trustworthiness of event collection.

Independent Anchoring (Planned)

To reduce the risk of a privileged attacker rewriting the entire ledger and recomputing hashes, KALYX plans an independent anchor:
	•	Periodic export of the latest ledger hash
	•	Time-stamped + signed anchor record
	•	Stored on an independent node (e.g., Raspberry Pi)

This creates an external “witness” so retrospective rewriting becomes detectable.

Roadmap (Planned Work)

Backend API
	•	POST /ingest
	•	POST /verify
	•	GET /status
	•	GET /export

Web Application
	•	Ledger health dashboard
	•	Verification view (show trust collapse point)
	•	Event explorer (filter/search)
	•	Evidence export bundle

Real-Time Capture (Optional Extension)
	•	Integrate auditd/eBPF as an ingestion source
	•	Preserve the same ledger contract

Academic Contribution

KALYX demonstrates:
	•	Applied cryptographic integrity design for execution provenance
	•	Deterministic hash-domain enforcement
	•	Controlled ingestion boundaries
	•	Attack simulation validation
	•	Reproducible software packaging
	•	Explicit security boundary modelling

Vision

KALYX is not “monitoring for alerts”.
It is a trust validation layer for execution history.

---

### What changed (so you can justify it if asked)
- Replaced “**guarantees append-only history**” with “**detects modification/deletion/reordering** within boundary” (more defensible).
- Made “**integrity vs authenticity**” explicit (reviewers love that).
- Marked anchor/API/UI as **planned**, not implied as done.
- Softened “not a logging tool” into “not monitoring for alerts” (less arguable, still keeps your USP).
