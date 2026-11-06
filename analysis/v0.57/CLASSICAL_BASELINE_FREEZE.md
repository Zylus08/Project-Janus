# Project Janus — Classical Baseline Freeze Specification
## Designation: Janus Classical Baseline C1

**Milestone:** Project Janus v0.57  
**Document Classification:** Permanent Classical Engineering Baseline Specification  
**Designation:** **Janus Classical Baseline C1**  
**Author:** Principal Chess Engine Architect & Lead Systems Engineer  
**Date of Freeze:** 2026-11-06  
**Git Anchor Commit:** `e543dab`  
**Parent Anchor Commit:** `f6025c3`  
**Repository Branch:** `v0.3-benchmark-harness`  
**Status:** **PERMANENTLY FROZEN & IMMUTABLE**  

---

## 1. Baseline Designation & Objective

This document establishes the permanent, immutable engineering specification for **Janus Classical Baseline C1**.

All future machine learning prototypes (beginning with Janus v0.58) must benchmark their playing strength, tactical decision accuracy, search throughput, and node efficiency against precisely this frozen baseline. Under no circumstances may C1's source code, compiler flags, default options, or evaluation terms be modified.

---

## 2. Toolchain, Compiler & Binary Cryptographic Manifest

### 2.1 Build Environment
- **Operating System:** Windows 11 Enterprise AMD64 (16 logical cores, 3.20 GHz base).
- **Toolchain:** Microsoft Visual C++ Build Tools 2022 (`v19.43.34809 x64`).
- **Compilation Flags:** `/O2 /Ot /Oi /std:c++17 /EHsc`.
- **Target Architecture:** x86_64 / Native AMD64.

### 2.2 Source & Executable Cryptographic Manifest
| Artifact Description | File Path | File Size (Bytes) | SHA-256 Digest |
| :--- | :--- | :---: | :--- |
| **C1 Production Source** | `analysis/v0.56/native/janus_native.cpp` | 80,677 | `bb57b5fb31be013ceca162a8435d6eeb184be5b74681fb80cb2b0051185aa861` |
| **C1 Standalone Engine** | `analysis/v0.56/native/janus_native_engine.exe` | 341,504 | `a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f` |
| **C1 Shared DLL** | `analysis/v0.56/native/janus_native.dll` | 259,072 | `db06d15b0bfa9da16dfa99f196a642eeb9491629858aa58cf27393e1ea66518f` |
| **C1 Python Native Bridge**| `analysis/v0.56/native/janus_native_bridge.py` | 14,350 | `a41a46cf988849b29cb115e5df1176b6b71f9cfd5fe4e11fa05470d55e8c1566` |

---

## 3. Production Engine Search & Evaluation Configuration

### 3.1 UCI Protocol Options & Frozen Defaults
When instantiated via UCI, Janus C1 initializes with the following production defaults:

```text
id name Janus 0.56 Native (N7 Candidate)
id author Project Janus Team
option name UseKillerOrdering type check default true
option name UseHistoryOrdering type check default true
option name UsePVS type check default false
option name UseLMR type check default true
option name LMRMinDepth type spin default 3 min 2 max 8
option name LMRMoveThreshold type spin default 4 min 2 max 16
option name LMRBaseReduction type spin default 1 min 1 max 3
option name UseSEEOrdering type check default false
option name UseSEEInQuiescence type check default false
uciok
```

### 3.2 Algorithmic Subsystems
1. **Board Representation:** 64-bit Bitboards (`uint64_t pieces[2][6]`, `occupancy[2]`, `all_occupancy`).
2. **Move Generation:** Strict legal move generation with pin-awareness and king check evasion.
3. **Zobrist Hashing:** 64-bit keys with incremental updates for pieces, side to move, castling, and en passant squares.
4. **Transposition Table:** 64 MB (1,048,576 slots) with depth-preferred replacement, 2-bit flag (`EXACT`, `LOWER`, `UPPER`), and normalized distance-to-mate scoring.
5. **Move Ordering:**
   - Hash move from Transposition Table: $10,000,000$
   - Pawn Promotions: $800,000 - 900,000$
   - MVV-LVA Captures: $100,000 + (10 \times \text{Victim}) - \text{Attacker}$
   - Primary Killer Move (Quiet): $90,000$
   - Secondary Killer Move (Quiet): $80,000$
   - Butterfly History Table: $\le 16,384$
   - Unscored Quiet Moves: $0$
6. **Search Heuristics:**
   - **Late Move Reductions (LMR):** Active for quiet moves where $\text{depth} \ge 3$, $\text{move\_index} \ge 4$, with 1-ply base reduction protected by 10 tactical invariants (no reductions in check, on PV, on killers, or on tactical moves).
   - **Quiescence Search:** Captures and promotions with delta pruning ($1100$ cp margin).
7. **Static Evaluation:** Handcrafted piece-square tables with game-phase interpolation (Opening/Endgame piece square weights: Pawn 100, Knight 320, Bishop 330, Rook 500, Queen 900).

---

## 4. Empirical Baseline Qualification Evidence

### 4.1 Inherited Unit Test Suite
- Total Tests: **639** (spanning v0.10 through v0.56).
- Passing Tests: **639 / 639 (100.0%)**.
- Execution Time: **169.61 seconds**.
- Regressions: **Zero**.

### 4.2 Tactical Decision Quality
- **Benchmark Corpus:** 64 benchmark positions across 4 standard suites.
- **Solution Retention:** 16 / 16 (100% solution retention at Depth 5).
- **Move Selection Consistency:** 64 / 64 (100.0% agreement with audited baseline).

### 4.3 Search Throughput
- **Single-Core NPS:** $1,500,000 - 1,750,000$ nodes/sec under 64-bit MSVC `/O2`.
- **Clock Discipline:** $0.00$ ms mean overshoot across all tested time tiers.

### 4.4 External Stockfish 19 Calibration Benchmark
Contested over 10 balanced opening pairs (20 games per tier, 80 total games) under Fischer 3.0s+100ms:
- **SF19-A (`UCI_Elo = 1320`):** 16.0 / 20 (80.0%) [+16 =0 -4] $\to$ Performance: **+240.8 Elo**
- **SF19-B (`UCI_Elo = 1600`):** 7.0 / 20 (35.0%) [+5 =4 -11] $\to$ Performance: **-107.5 Elo**
- **SF19-C (`UCI_Elo = 2000`):** 5.0 / 20 (25.0%) [+4 =2 -14] $\to$ Performance: **-190.8 Elo**
- **SF19-D (Unrestricted NNUE):** 0.0 / 20 (0.0%) [+0 =0 -20] $\to$ Classical Ceiling
- **Calibrated Baseline Anchor:** **$1500 \pm 50$ Stockfish-calibrated Blitz Elo**.
- **Tournament Integrity:** 0 crashes, 0 timeouts, 0 illegal moves across all 80 games.

---

## 5. Known Limitations & Architectural Deficiencies

Janus Classical Baseline C1 possesses clear, documented limitations:
1. **Positional Evaluation Blindness:** Evaluation is purely additive over material and 64-square static tables. It cannot detect dynamic pawn structure weaknesses (isolated, backward, doubled pawns) or piece coordination synergies.
2. **Endgame King Passivity:** Lacks dedicated endgame king centralization and passed pawn escort evaluation terms.
3. **Quiescence Search Horizon:** Restricted strictly to captures and promotions; quiet checks and intermezzos are not explored beyond the main search horizon.
4. **No Neural Pruning or Evaluation:** All decisions stem from classical alpha-beta minimax with handcrafted static terms.

---

## 6. Freeze Protocol & Future Milestone Requirements

1. **Immutability:** Baseline C1 is locked. Future experiments must not alter `analysis/v0.56/native/janus_native.cpp` or change default UCI behavior.
2. **Control Reference:** When evaluating the first neural candidate in v0.58, C1 will serve as the invariant control opponent.
3. **Reproducibility:** Any researcher compiling `analysis/v0.56/native/janus_native.cpp` with MSVC 2022 `/O2 /Ot /Oi /std:c++17` will reproduce identical node counts, moves, and calibrated performance.

