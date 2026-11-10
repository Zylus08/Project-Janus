# Project Janus — Phase 1, Milestone P1.4
## Search Invariants, Perft Correctness & Classical Regression Qualification Report

**Author:** Principal Computer Chess Engineer, C++17 Search Architect, Independent Experimental Auditor  
**Lineage:** Janus Classical X  
**Benchmark Engine:** Janus Classical X9 Candidate vs Classical X7 Control  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary

Prior to initiating formal head-to-head match validation between Candidate X9 and Baseline X7, this suite verifies the move generation soundness, bit-exact regression safety, mate detection accuracy, and search invariants of Candidate X9.

All five critical invariant domains passed with **100% compliance**:
1. **Perft Move Generation Integrity:** 12/12 perft depth checks (Depths 1..4 across standard benchmark positions) matched the mathematical ground truth bit-for-bit.
2. **Strict Bit-Exact Fallback Invariance:** When configured with `UCI_Variant X7`, Janus Classical X reproduced bit-exact node counts, evaluation centipawns, and principal variation moves identical to the frozen control `janus_classical_x7.exe`.
3. **Mate Detection & Mate-in-N Soundness:** Successfully resolved mate-in-1 (Scholar's Mate, Back Rank Mate) and mate-in-2 (Légal's Mate) returning proper mate distance centipawn scores ($29,000 - \text{ply}$).
4. **Threefold Repetition Invariance:** Verified exact 0 cp score assignment upon detecting threefold repetition in the transposition history.
5. **Score Boundedness:** All evaluations remain strictly bounded within $[-30000, +30000]$ with zero arithmetic overflow or signed integer wrap-around.

---

### 2. Perft Move Generation Audit

| Position | Depth | Actual Nodes | Expected Nodes | Status |
|---|---|---|---|---|
| **Startpos** | 1 | 20 | 20 | **PASS** |
| **Startpos** | 2 | 400 | 400 | **PASS** |
| **Startpos** | 3 | 8,902 | 8,902 | **PASS** |
| **Startpos** | 4 | 197,281 | 197,281 | **PASS** |
| **KiwiPete** | 1 | 48 | 48 | **PASS** |
| **KiwiPete** | 2 | 2,039 | 2,039 | **PASS** |
| **KiwiPete** | 3 | 97,862 | 97,862 | **PASS** |
| **KiwiPete** | 4 | 4,085,603 | 4,085,603 | **PASS** |
| **Position 3** | 1 | 14 | 14 | **PASS** |
| **Position 3** | 2 | 191 | 191 | **PASS** |
| **Position 3** | 3 | 2,812 | 2,812 | **PASS** |
| **Position 3** | 4 | 43,238 | 43,238 | **PASS** |

---

### 3. Bit-Exact Fallback Invariance Audit vs Frozen X7 Control

| Test Position | Depth | Frozen X7 Control (`nodes`, `score`, `bestmove`) | New Engine in `UCI_Variant X7` | Status |
|---|---|---|---|---|
| **Startpos** | 6 | `(32663, 0, b1c3)` | `(32663, 0, b1c3)` | **PASS** |
| **KiwiPete** | 5 | `(49254, 42, d5e6)` | `(49254, 42, d5e6)` | **PASS** |
| **Middlegame Pos 3** | 7 | `(18778, 23, b4f4)` | `(18778, 23, b4f4)` | **PASS** |
| **Tactical Pos 4** | 6 | `(24815, -71, b1c3)` | `(24815, -71, b1c3)` | **PASS** |
| **Endgame Pos 5** | 8 | `(11135, 141, e3f3)` | `(11135, 141, e3f3)` | **PASS** |

---

### 4. Mate Detection & Repetition Invariants

- **Scholar's Mate in 1:** `bestmove h5f7`, score: `cp 28999` (Distance: 1 ply) — **PASS**
- **Back Rank Mate in 1:** `bestmove e2e8`, score: `cp 28999` (Distance: 1 ply) — **PASS**
- **Légal's Mate in 2:** `bestmove d5f6` (PV: `d5f6 g7f6 c4f7#`), score: `cp 28997` (Distance: 3 ply) — **PASS**
- **Threefold Repetition:** `score cp 0` correctly evaluated on repeating line — **PASS**

**Qualification Verdict:** **PASSED & QUALIFIED FOR MATCH VALIDATION**.

