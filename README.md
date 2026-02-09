# KALYX — Verifiable Execution History System

## Project Overview
KALYX is a tamper-evident execution history system that records execution events as an append-only cryptographic ledger.  
Its purpose is not monitoring “for performance”, but ensuring that system execution history remains *verifiably trustworthy* for audit, compliance, and incident investigations.

---

## Current Status (Checkpoint)
**Phase 0:** ✅ Completed  
**Phase 1:** ✅ Completed  
**Phase 2:** ✅ Completed  
**Phase 3 (Foundation):** ✅ Completed  
**Next:** Phase 3 (Application Layer) → Phase 4 (Real ingestion) → Phase 5 (UI + workflows)

---

## What Problem KALYX Solves
Traditional logs are easy to modify after compromise (edit/delete/inject).  
KALYX turns execution history into cryptographic evidence:
- If an attacker changes history, verification fails at the earliest break point.
- Trust boundaries are explicit and testable.

---

## Architecture (High Level)

### Data Flow
1. **Event Source**
   - (Current) File-based exec-like input
   - (Later) Real exec stream (execsnoop/eBPF/auditd)
2. **Ingestion Layer**
   - Parses events and wraps into a standard record format
3. **Ledger Core**
   - Append-only hash-chained records (prev_hash → hash)
4. **Verification**
   - Recomputes hashes, detects tampering, pinpoints trust collapse
5. **Interface Layer**
   - (Current) CLI commands
   - (Next) API + UI software application

---

## Ledger Record Model (Current)
Each record contains:
- `event`: execution details (comm, pid, ppid, argv, ret, ts if available)
- `prev_hash`: link to previous record
- `hash`: integrity proof

(Optionally: schema/provenance envelope — depending on your current branch)

---

## Completed Phases

### Phase 0 — Ledger Core
**Goal:** Implement append-only cryptographic ledger with hash chaining.  
**Output:** `chain_event()` writes deterministic records to `logs/exec_chain.jsonl`.

### Phase 1 — Verification + Tamper Detection
**Goal:** Verify ledger integrity and detect modifications.  
**Output:** `verify_chain()` flags earliest break point; clean ledger verifies successfully.

### Phase 2 — Ingestion (Controlled)
**Goal:** Ingest external execution-like events into the ledger without breaking integrity.  
**Output:** `ingest_execsnoop.py` reads execution lines → normalises → chains into ledger.

### Phase 3 — Tool Packaging + CLI (Foundation)
**Goal:** Convert prototype scripts into a usable tool with a stable interface.  
**Output:** `kalyx` CLI supports:
- `kalyx ingest`
- `kalyx verify`

---

## Evidence (Screenshots to Insert)
- [ ] Verification success output (`[✓] Ledger verified — no tampering detected`)
- [ ] Example ledger line showing fields
- [ ] Tamper test showing failure at entry X
- [ ] CLI commands working end-to-end
- [ ] Git commit history (phases)

---

## Known Issues Encountered (and How They Were Resolved)
- Hash-domain mismatch between writer and verifier → unified canonical hash contract
- Missing/empty input prevented ledger creation → controlled sample input introduced
- CLI not found due to PATH/directory collisions → corrected launcher installation
- Python package import failures → venv + package structure fixed
- PEP 668 blocked system pip installs → virtual environment adopted

---

## Roadmap to a Software Application (BSc Requirement)

### Milestone A — Backend API (4–6 weeks)
- Provide REST API for:
  - ingesting events
  - verifying ledger
  - status/summary endpoints
  - exporting reports (JSON/CSV)

### Milestone B — Frontend UI (3–5 weeks)
- UI pages:
  - Dashboard (ledger health, last verified, entry counts)
  - Verify page (run verification + show trust break point)
  - Evidence view (search/filter events)
  - Export report (download evidence bundle)

### Milestone C — Real Event Collection (Optional/Extension)
- Replace file ingestion with:
  - auditd OR execsnoop OR eBPF stream
- Keep the ledger contract unchanged.

---

## Deliverables for Final Submission
- Source code repo + tags by phase
- Report (phases, evaluation, limitations)
- Demo walkthrough (CLI + UI)
- Evidence bundle: screenshots, sample ledgers, tamper tests

---
