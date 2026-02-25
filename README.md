KALYX — Verifiable Execution Integrity Platform

Overview

KALYX is a tamper-evident execution integrity platform designed to transform system execution history into cryptographically verifiable evidence.

Traditional logs assume trust.
KALYX makes trust testable.

Instead of preventing modification, the system guarantees that any unauthorised change to execution history is detectable and localisable.

The platform is designed for:
	•	Audit and compliance verification
	•	Incident response and forensic validation
	•	Trust assessment of system activity records


Problem Statement

System logs can be modified, deleted, or injected after compromise.
Administrators or attackers with elevated privileges can rewrite history.

This creates a gap between:

What happened
vs
What can be proven

KALYX addresses this gap by converting execution events into an append-only cryptographic ledger with deterministic verification.


Core Architecture

Data Flow
	1.	Event Source
	•	(Current) File-based execution input
	•	(Future) Kernel-level capture (eBPF / auditd)
	2.	Ingestion Layer
	•	Normalises execution records
	•	Wraps into structured ledger format
	3.	Ledger Core
	•	Append-only hash-linked records
	•	Deterministic canonical hashing
	4.	Verification Engine
	•	Recomputes hash chain
	•	Detects earliest integrity violation
	5.	Interface Layer
	•	CLI (current)
	•	Backend API + UI (planned)


Ledger Model

Each ledger entry contains:
	•	Execution event metadata
	•	command name
	•	pid / ppid
	•	arguments
	•	return code
	•	timestamp (when available)
	•	prev_hash
	•	hash

Hash Contract:

hash = SHA-256(canonical JSON of record excluding "hash")

This ensures deterministic reproducibility across environments.


Completed Phases

Phase 0 — Cryptographic Ledger Core
	•	Implemented append-only JSONL ledger
	•	Hash chaining using prev_hash → hash
	•	Deterministic canonical hashing

Outcome:
Execution history becomes tamper-evident.


Phase 1 — Integrity Verification
	•	Built sequential verifier
	•	Detects modification, deletion, insertion
	•	Reports earliest trust collapse

Outcome:
Ledger integrity is testable and defensible.


Phase 2 — Controlled Ingestion Pipeline
	•	Built ingestion parser
	•	Converts execution-like data into ledger records
	•	Preserved integrity guarantees during ingestion

Issues resolved:
	•	Hash-domain mismatch between writer and verifier
	•	Empty ingestion producing false failures
	•	Deterministic canonical contract enforced

Outcome:
Full pipeline operational:

input → parse → chain → verify


Phase 3 — Tool Packaging & CLI Integration
	•	Converted prototype scripts into structured package
	•	Implemented CLI:

kalyx ingest
kalyx verify
kalyx status


	•	Resolved packaging issues:
	•	PATH collisions
	•	launcher directory conflicts
	•	Python import failures
	•	PEP 668 restrictions
	•	package reconstruction

Outcome:
KALYX is now a reproducible, version-controlled tool.


Security Properties

KALYX guarantees:
	•	Integrity of stored sequence
	•	Order preservation
	•	Detection of modification and naive insertion
	•	Localisation of integrity failure

KALYX does NOT attempt to:
	•	Prevent kernel-level compromise
	•	Guarantee authenticity of ingestion source
	•	Stop root-level attackers

It guarantees that tampering cannot occur silently.


Independent Anchoring (Planned)

To protect against full-system compromise and ledger recomputation attacks, KALYX will introduce independent external anchoring.

Planned mechanism:
	•	Periodic extraction of the current ledger root hash
	•	Transmission to an external anchor service
	•	Time-stamping and cryptographic signing of the root
	•	Append-only storage of signed anchor records

This ensures that a rewritten ledger cannot retroactively match previously anchored roots.

The anchor service will be implemented on an independent device or environment to maintain adversarial separation.


Roadmap

Stage 1 — Backend API
	•	REST endpoints:
	•	ingest
	•	verify
	•	status
	•	export
	•	Structured evidence responses

Stage 2 — Frontend Application
	•	Dashboard: ledger health
	•	Verification view
	•	Event explorer
	•	Evidence export bundle

Stage 3 — Real Event Collection
	•	Integrate kernel-level execution capture
	•	Maintain unchanged ledger contract


Academic Scope

This project integrates:
	•	Operating systems concepts
	•	Cryptographic integrity mechanisms
	•	Secure logging theory
	•	Software engineering practices
	•	Reproducible development workflows

The final deliverable will include:
	•	Full source code
	•	Evaluation results
	•	Controlled tamper simulations
	•	Documented limitations


Current Status
	•	Ledger Core: Complete
	•	Verification: Complete
	•	Ingestion Pipeline: Complete
	•	CLI Tooling: Complete
	•	Independent Anchoring: Planned
	•	API + UI: Planned


Repository Structure

kalyx/
├── kalyx/
│   ├── cli.py
│   ├── core/
│   │   ├── chain.py
│   │   └── verify.py
│   └── engine/
│       └── ingest_execsnoop.py
├── logs/
├── reports/
└── setup.py

