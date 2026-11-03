# Baseline Freeze & Configuration Snapshot — v0.46

**Milestone:** Project Janus v0.46  
**Date:** 2026-11-03  
**Status:** PASS (Gate A Validated)

---

## 1. Repository Provenance & Environment

| Parameter | Recorded Value |
|---|---|
| **Repository Root** | `E:\ChessXML\project-janus` |
| **Git Branch** | `v0.3-benchmark-harness` |
| **Git HEAD** | `bd874ac2d6e63694280d66e21292dd4108d70b02` |
| **Parent Baseline Commit** | `bd874ac` (v0.45 Final) |
| **Working Tree Status** | Clean |
| **Python Version** | Python 3.13.2 (64-bit AMD64) |
| **Stockfish Path** | `E:\ChessXML\tools\stockfish\stockfish.exe` |
| **Stockfish SHA-256** | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` |

---

## 2. Baseline Test Suite Verification

- **Command:** `& 'E:\ChessXML\project-janus\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_*.py'`
- **Total Tests:** 462
- **Passed:** 462 (100.0%)
- **Failed:** 0
- **Errors:** 0
- **Execution Time:** 131.253 seconds

---

## 3. Configuration Comparison: K0 vs RFP

| Parameter | K0 (Production Default) | RFP (Experimental) | Note |
|---|---|---|---|
| `enable_rfp` | **`False`** | **`True`** | Primary ablation variable |
| `rfp_max_depth` | `2` | `2` | Frontier depth limit |
| `rfp_margin_per_depth` | `120` | `120` | Centipawns per depth |
| `tt_max_entries` | `200,000` | `200,000` | Transposition table size |
| `tt_replacement_policy` | `always_replace` | `always_replace` | TT replacement rule |
| `qsearch_max_ply` | `12` | `12` | Max quiescence plies |
| `max_killers_ply` | `64` | `64` | Killer table depth |
| `enable_history` | `True` | `True` | Butterfly history heuristic |
| `enable_history_malus` | `False` | `False` | Quiet history penalty |
| `enable_countermoves` | `False` | `False` | Countermove heuristic |
| `enable_pvs` | `True` | `True` | Principal variation search |
| `enable_aspiration` | `True` | `True` | Aspiration windows ($d \ge 2$) |
| `aspiration_delta` | `35` | `35` | Initial aspiration half-window |
| `max_aspiration_retries` | `3` | `3` | Max aspiration window widening |
| `enable_lmr` | `True` | `True` | Late move reductions |
| `enable_nmp` | `True` | `True` | Null move pruning ($d \ge 3$) |
| `nmp_reduction` | `2` | `2` | NMP depth reduction $R$ |
| `enable_nmp_verification` | `True` | `True` | NMP verification search |
| `check_extension_policy` | `disabled` | `disabled` | Check extension policy |
| `enable_see_ordering` | `False` | `False` | Static exchange move ordering |
| `enable_see_pruning` | `False` | `False` | Static exchange pruning |
| `time_policy` | `adaptive` | `adaptive` | Fischer adaptive allocator |
| `evaluation_features` | Standard + KingSafety | Standard + KingSafety | Material + PST + King safety |

---

## 4. Gate A Verification & Sign-Off

- [x] Repository HEAD, branch, and clean status confirmed.
- [x] Stockfish 19 binary digest validated.
- [x] Complete test suite executed with 100% pass rate (462/462).
- [x] Search parameters frozen and cataloged.

**Gate A Status:** **PASS** — Proceeding to Phase B (Search Architecture and Move-Ordering Audit).
