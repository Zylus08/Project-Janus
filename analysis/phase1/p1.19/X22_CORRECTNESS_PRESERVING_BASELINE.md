# Milestone P1.19 Phase 1: Certified Starting Architecture (X22 Correctness Baseline)

**Date:** November 14, 2026  
**Status:** Certified & Frozen  
**Branch:** `phase1/classical-janus`  
**Reference Architecture:** Janus Classical X22 (`e33f292`)  
**Executable Checksum:** `35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C`  
**Source Checksum:** `FD67D0B2B7659E8EA013BF7E38252B9ABDD6627B4EAD991C46E340BF27CD02A8`

---

## 1. Executive Summary & Provenance Verification

Milestone P1.19 selects **Janus Classical X22** as the immutable correctness-preserving reference foundation for all classical evaluation research in this milestone. Janus Classical X22 was developed and frozen in Milestone P1.17, resolving the critical quiescence stand-pat bug of P1.16 while establishing the 64K thread-local pawn hash table and true outpost evaluation terms.

### Certified Control Binary Provenance
| Artifact | Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| **Executable** | `analysis/phase1/p1.17/control/janus_classical_x22.exe` | 1,610,752 | `35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C` |
| **Shared Lib** | `analysis/phase1/p1.17/control/janus_classical_x22.dll` | 1,514,496 | `004ACE07C31F9D8124B8C0EA9D402C497D906CC3042A4A3C171A7D5A5D710DA4` |
| **Source** | `analysis/phase1/p1.17/control/janus_classical_x22.cpp` | 245,537 | `FD67D0B2B7659E8EA013BF7E38252B9ABDD6627B4EAD991C46E340BF27CD02A8` |

All checksums match the project ledger with 100% bitwise fidelity.

---

## 2. Compiler Toolchain & Invariant Specification

Janus Classical X22 was built using the standard project toolchain:
- **Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.42/19.43 for x64
- **Flags:** `/O2 /Oi /Ot /std:c++17 /EHsc`
- **CPU Target:** x86-64 with AVX2 instruction acceleration

### Critical Invariants Preserved in Reference Architecture
1. **Quiescence Search Correctness ($Q1$ Policy):**
   - **Stand-pat suppression under check:** When `native_is_check(b)` is true, `stand_pat = -INF`. The engine is strictly forbidden from pruning or assuming an evaluation when the side to move is in check.
   - **Mandatory legal check evasion generation:** When in check, all pseudo-legal and capture filters are bypassed; `native_generate_legal_moves(b, legal_m)` is invoked.
   - **Terminal mate and stalemate handling:** If `n_legal == 0` when in check, the engine immediately returns `-(MATE_SCORE - ply)`. If `n_legal == 0` and not in check, stalemate returns $0\text{ cp}$.
   - **Negative-SEE evasion exemption:** In-check evasions are completely exempt from negative-SEE pruning, ensuring no mate escapes are discarded.
   - **Horizon fallback limit:** `MAX_QSEARCH_PLY = 24` bounds quiescence depth without compromising tactical stability.

2. **Positional Evaluation & Outpost Semantics:**
   - **True Outpost Ray Spans:** Knight outposts require that enemy pawns cannot attack the square currently or in future ranks (verified via forward attack ray spans `pawn_attacks_span`).
   - **Central Bishop Outposts:** Supported bishops on central files (c, d, e, f) receive permanent outpost bonuses ($+22\text{ mg} / +14\text{ eg}$) if immune to enemy pawn attack.
   - **Transient Outpost Degradation:** Squares that can be driven off by enemy pawn advances receive degraded bonuses ($+8\text{ mg} / +4\text{ eg}$).

3. **Pawn Hash Table Architecture:**
   - Direct-mapped 64K-entry thread-local table (`g_pawn_table`) consuming 2 MB per thread.
   - Keyed on full 64-bit pawn Zobrist hash (`compute_pawn_zobrist(b)`).
   - Zero-latency caching ($\approx 12.4\text{ ns}$ probe latency) providing $+13.5\%$ evaluation speedup and $+10.6\%$ search NPS.

---

## 3. Baseline Role in Milestone P1.19

Janus Classical X22 serves two indispensable roles in P1.19:
1. **Ablation Comparator ($A_0$ Baseline):** Serves as the control reference to measure the exact strength contribution of isolated backward pawn evaluation ($A_1$) in development and confirmatory tournament play.
2. **Feature-Disabled Identity Invariant:** Candidate X24 must satisfy the strict constraint that when backward pawns are toggled off (`UCI_BackwardPawns = false`), the evaluation and search output must match X22 bit-for-bit across all legal chess positions.
