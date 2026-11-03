# Project Janus v0.43 — Provenance Audit & Starting State Reconciliation (Phase A)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Auditor:** Statistical Validation Lead & Independent Audit Engineer  
**Date:** 2026-11-03  
**Status:** RECONCILED & VERIFIED  

---

## 1. Current Repository State (Phase A1)

- **Repository Path:** `E:\ChessXML\project-janus`
- **Active Branch:** `v0.3-benchmark-harness` (tracking `origin/v0.3-benchmark-harness`)
- **Current HEAD Commit:** `41f407d` (`feat: add comprehensive v0.42 analysis reports, decision framework, and audit documentation`)
- **Expected Starting Commit from Brief:** `15964d9`
- **Working-Tree Status:** Clean (`git status --short` returned 0 modified tracked files)
- **Untracked Files:** `analysis/v0.43/` (new milestone directory)
- **Runtime Environment:**
  - Python: `3.13.2` (tags/v3.13.2:4f8bb39, Feb 4 2025, 15:23:48) [MSC v.1942 64 bit (AMD64)]
  - Platform: Windows-11-10.0.26200-SP0
  - python-chess: `1.11.2`
- **Engine Entry Point:** `janus.uci` (`src/janus/uci.py`)
- **Default Search Configuration:** Baseline K0 (`enable_rfp=False`, `enable_killers=True`, `enable_history=True`, `time_policy="arm_c"`)
- **RFP Configuration Switches:** `--enable-rfp` (`rfp_max_depth=2`, `rfp_margin_per_depth=120`)
- **Test Suite Status:** 451 / 451 tests passing (runtime: 90.8s)
- **External Opponent Binary:** Stockfish 19
  - Path: `E:\ChessXML\tools\stockfish\stockfish.exe`
  - SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`
  - UCI Options: `Threads=1, Hash=64, UCI_LimitStrength=true, UCI_Elo=1320`

---

## 2. Commit Ancestry and Lineage Audit (Phase A2)

The execution brief identified potential starting commit discrepancies:
- Expected v0.41 final commit: `f499329`
- Reported v0.42 starting commit: `1d509d0`
- Reported v0.42 final commit: `15964d9`
- Actual current HEAD: `41f407d`

### Ancestry Verification
We performed programmatic git parent-child traversal:

```
f499329 (docs(v0.41): milestone report)
   │
   ▼
1d509d0 (docs: add v0.41 search telemetry audit and rfp qualification reports)
   │
   ▼
0825eaa (test(search): add v0.42 draw semantics and rule compliance regression suite)
   │
   ▼
408c7fc (feat(audit): add v0.42 clean-room verification pipeline and forensic analysis)
   │
   ▼
15964d9 (docs(v0.42): comprehensive milestone report, empirical ablation, and final decision framework)
   │
   ▼
41f407d (feat: add comprehensive v0.42 analysis reports, decision framework, and audit documentation) [HEAD]
```

Every commit in this sequence is a strict, linear ancestor of its successor (`git merge-base --is-ancestor` evaluated `True` across all links).

### Code Diff Audit Across Lineage
We examined `git diff f499329..41f407d src/`:
- **Result:** **Zero lines changed in `src/`**.
- The underlying engine logic, evaluation weights, search tree pruning, quiescence search, and UCI handling remained completely frozen and identical across the entire commit span from v0.41 to HEAD.
- Changes between `f499329` and `1d509d0` consisted solely of trailing newline additions in 3 documentation files.
- Changes between `15964d9` and `41f407d` consisted solely of trailing newline additions in 6 markdown files.

**Conclusion:** The engine binary and code state for v0.43 is identical to the verified engine state of v0.41 and v0.42. No history rewriting or re-basing occurred.

---

## 3. Preservation of v0.42 Artifacts (Phase A3)

All 13 evidence artifacts produced during milestone v0.42 have been cryptographically indexed in:
[`analysis/v0.43/v042_reference_manifest.json`](file:///e:/ChessXML/project-janus/analysis/v0.43/v042_reference_manifest.json)

No original files in `analysis/v0.41/` or `analysis/v0.42/` have been altered or relocated.
