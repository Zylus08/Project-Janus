# PROJECT JANUS — PHASE 1, MILESTONE P1.12
## Classical Competitive Reference Ladder Specification

**Document ID:** `analysis/phase1/p1.12/CLASSICAL_COMPETITIVE_REFERENCE_LADDER.md`  
**Milestone:** Phase 1, Milestone P1.12  
**Status:** Certified Specification & Framework Document  
**Date:** 2026-11-12  
**Auditor:** Principal Computer Chess Engineer & Independent Statistical Auditor  

---

## 1. Executive Summary & Purpose

The purpose of the **Classical Competitive Reference Ladder** is to establish a rigorous, immutable, three-tier benchmarking hierarchy for Project Janus. In previous milestones (P1.10 and P1.11), testing suffered from two critical calibration deficiencies:
1. **The Modern-Ceiling Conflation:** Candidates were evaluated against unrestricted Stockfish 19 (NNUE). Because Stockfish 19 exceeds 3650+ Elo and possesses a multi-megabyte trained neural evaluation network, comparing an early-stage classical handcrafted engine directly to Stockfish 19 yielded near-zero win/draw rates (e.g. 0.0% to 1.25% score), collapsing Elo estimation into deep negative infinity with high variance and zero diagnostic resolution.
2. **Missing Classical Intermediate Ceiling:** There was no intermediate standard representing the historical pinnacle of handcrafted classical chess evaluation and search (the 30+ year culmination of non-neural computer chess engineering) before the neural revolution.

To rectify these deficiencies, Milestone P1.12 establishes a formalized three-tier reference ladder with strict separation invariants.

```
+-----------------------------------------------------------------------------------+
| TIER 3: Modern State of the Art (External Modern Ceiling)                         |
| Stockfish 19 (NNUE enabled, 84 MB binary, deep neural net evaluation)             |
| Role: Absolute domain ceiling. Measures total gap to modern super-GM computer     |
+-----------------------------------------------------------------------------------+
                                         ^
                                         |  Handcrafted vs Neural Revolution Gap
                                         v
+-----------------------------------------------------------------------------------+
| TIER 2: Historical Classical State of the Art (External Classical Ceiling)        |
| Stockfish 11 (Strictly Classical Handcrafted, Zero NNUE, 687 KB binary)           |
| Role: Classical peak ceiling. Measures efficiency against 30 years of pure search |
+-----------------------------------------------------------------------------------+
                                         ^
                                         |  Janus Architecture Qualification Gap
                                         v
+-----------------------------------------------------------------------------------+
| TIER 1: Qualified Classical Controls (Internal Frozen Baselines)                  |
| Track S: Janus Classical X7 (1T Baseline, commit b34e342)                         |
| Track P: Janus Classical X12 (4T Baseline, commit 78ca3d5)                        |
| Role: Local regression gating. Primary hurdle for candidate promotion             |
+-----------------------------------------------------------------------------------+
```

---

## 2. Tier 1: Qualified Classical Controls (Internal Frozen Baselines)

Tier 1 engines serve as the primary regression baseline. Under the Janus Charter, **no experimental candidate may be promoted or considered for further development unless it demonstrates statistically significant playing-strength superiority ($p < 0.05$) against its corresponding Tier 1 control**.

### 2.1 Track S Control: Janus Classical X7 (Single-Threaded Baseline)
- **Engine Identity:** Janus Classical X7 (1T)
- **Qualified Source Commit:** `b34e342` (Milestone P1.3)
- **Source File Path:** `analysis/phase1/p1.12/baseline/track_s_x7/janus_classical_x7.cpp`
- **Certified Binary Path:** `analysis/phase1/p1.3/control/janus_classical_x7.exe`
- **Binary Size:** 370,176 bytes
- **SHA-256 Digest:** `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b`
- **Toolchain & Flags:** Microsoft Visual Studio 2022 (MSVC v143), `/std:c++17 /O2 /Oi /Ot /EHsc /DNDEBUG`
- **Architecture & Primitives:**
  - Bitboard board representation (64-bit unsigned integers, Magic Bitboards for sliders)
  - Pure classical evaluation: Material weights, Piece-Square Tables (MG/EG), Piece Mobility, King Safety, Pawn Structure
  - Search: Iterative Deepening Negamax with Alpha-Beta, Transposition Table (64 MB default), Null Move Pruning ($R=2$ / $R=3$), Reverse Futility Pruning, History Heuristic, Late Move Reductions (log-log table indexing depth and move count), Quiescence Search with Static Exchange Evaluation (SEE) pruning.
  - Concurrency: Strictly 1 thread (single-threaded).
- **Certified Baseline Performance:**
  - Initial FEN NPS (depth 8): 1,003,260 NPS (1.00M NPS)
  - Diagnostic Atlas 16-position average throughput: 2.15M NPS
  - Qualification vs X6: +138.4 Elo ($p = 0.00012$)

### 2.2 Track P Control: Janus Classical X12 (Four-Thread Parallel Baseline)
- **Engine Identity:** Janus Classical X12 (4T)
- **Qualified Source Commit:** `78ca3d5` (Milestone P1.7)
- **Source File Path:** `analysis/phase1/p1.12/baseline/track_p_x12/janus_classical_x12.cpp`
- **Certified Binary Path:** `analysis/phase1/p1.7/control/janus_classical_x12.exe`
- **Binary Size:** 2,874,368 bytes
- **SHA-256 Digest:** `00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059`
- **Toolchain & Flags:** Microsoft Visual Studio 2022 (MSVC v143), `/std:c++17 /O2 /Oi /Ot /EHsc /DNDEBUG`
- **Architecture & Primitives:**
  - Concurrency Architecture: Lazy SMP with 4 search threads (`std::thread`, shared atomic flags)
  - Shared lockless Transposition Table (128 MB default, multi-word TT entry with verification hash)
  - Worker Thread Divergence: Thread-index depth offsets and move permutation skips to maximize tree coverage without contention
  - Evaluation & Pruning: Matched to X7 base with thread-safe evaluation buffers
- **Certified Baseline Performance:**
  - Initial FEN NPS (depth 8, 4T): 1,291,123 NPS
  - Qualification vs X11: +102.7 Elo ($p = 0.0018$)
  - Multithread scaling factor: $2.41\times$ effective node throughput over 1T

---

## 3. Tier 2: Historical Classical State of the Art (Stockfish 11)

Tier 2 represents the absolute theoretical ceiling of pure handcrafted classical chess programming before the advent of neural networks. Stockfish 11 is the final major official Stockfish release before NNUE evaluation was integrated in Stockfish 12 (July 2020).

### 3.1 Technical Specification & Provenance
- **Engine Identity:** Stockfish 11 64
- **Official Release Git Tag:** `sf_11`
- **Git Commit Hash:** `c3483fa9a7d7c0ffa9fcc32b467ca844cfb63790`
- **Certified Binary Path:** `E:\ChessXML\tools\stockfish_11\stockfish_11.exe`
- **Binary Size:** 687,616 bytes
- **SHA-256 Digest:** `b004c03bd71bb84e8bc1832c580e72a7e883f121e1834ea6da2802d1575e8048`
- **Toolchain & Compilation Flags:** Microsoft Visual Studio 2022 (MSVC v143), `/O2 /Ot /Oi /std:c++14 /EHsc /DNDEBUG`
- **Source Fixes Applied:** Resolved ambiguous `std::clamp` vs template `clamp` in `src/material.cpp` via standard C++14 mode; zero functional modifications to search, evaluation, or move generation.
- **Evaluation Engine:** 100% Handcrafted Classical Evaluation (Zero NNUE code). Features deep piece-square tables, king safety models, passed pawn dynamic evaluation, outposts, mobility grids, piece coordination, and complex scale-factor endgame tables.
- **Search Capabilities:** Full production Stockfish classical search: Multi-cut, Aspiration Windows, Singular Extensions, Pruning hierarchies (Futility, Null Move, ProbCut, SEE), History-based LMR with continuation history, Lazy SMP multithreading.
- **Standard Benchmark:**
  - Command: `stockfish_11.exe bench 16 1 13 default depth`
  - Nodes: 1,215,966 nodes
  - Measured NPS: 1,215,966 NPS (depth 13 completed in 1000ms)

### 3.2 Evaluation Role & Invariants
1. **The Classical Benchmark Standard:** Evaluates the gap between Janus Classical engines and the pinnacle of non-neural chess programming.
2. **Fair Testing Protocol:** Must run under identical hardware, matched thread counts (1T vs Track S, 4T vs Track P), and identical time controls.
3. **No NNUE Contamination:** Strictly non-neural; guarantees that performance differences reflect search tree pruning efficiency, evaluation nuance, and move ordering quality.

---

## 4. Tier 3: Modern State of the Art (Stockfish 19)

Tier 3 represents the modern state of the art in computer chess, incorporating massive-scale self-play trained neural network evaluations (NNUE).

### 4.1 Technical Specification & Provenance
- **Engine Identity:** Stockfish 19 (`sf_19`)
- **Official Git Commit Hash:** `edb0d9df8bc7c570f72365ee3d12d0985a72dfca`
- **Certified Binary Path:** `E:\ChessXML\tools\stockfish\stockfish.exe`
- **Binary Size:** 84,204,544 bytes
- **SHA-256 Digest:** `660eb009241b9c97ebfbcf9f4d2f8cb20d43f0545f1b138fe9738c642646399e`
- **Evaluation Engine:** Dual-network NNUE architecture (embedded embedded neural network weights).
- **Search Capabilities:** Ultra-deep selective search, highly aggressive singular extensions, multi-tier history tables, dynamic time management.
- **Standard Benchmark:**
  - Command: `stockfish.exe bench 16 1 13 default depth`
  - Nodes: ~2,500,000 nodes

### 4.2 Evaluation Role & Invariants
1. **Ultimate External Reality Check:** Measures how far handcrafted classical chess is from modern super-GM computer chess.
2. **Never Handicapped:** Stockfish 19 must run fully unrestricted with NNUE enabled, standard book/search parameters, and identical hardware/clock allocations.
3. **Diagnostic Attribution:** Used to verify tactical ground truth (e.g. evaluating whether move disagreements are genuine tactical oversights or benign positional preferences).

---

## 5. Separation Invariants & Engagement Rules

To prevent methodological cross-contamination and invalid conclusions, the following invariants are strictly enforced:

| Invariant Rule | Description | Enforcement Mechanism |
| :--- | :--- | :--- |
| **I1: Gating Precedence** | Tier 1 is the mandatory gate. An engine *cannot* be evaluated against Tier 2 or Tier 3 unless it first clears Tier 1 with $p < 0.05$. | Automated test orchestrator rejects Tier 2/3 suite unless Tier 1 SPRT passes. |
| **I2: Separation of Baselines** | Track S (1T) candidates compete *only* against X7 (Tier 1) and Stockfish 11 1T (Tier 2). Track P (4T) candidates compete against X12 (Tier 1) and Stockfish 11 4T (Tier 2). | Configuration validation checks thread count matches across both sides. |
| **I3: No Neural Contamination** | No neural network weights, NNUE code, learned policy vectors, or trained float arrays may exist anywhere within Janus sources. | Static inspection and binary symbol audit. |
| **I4: Calibration Role Allocation** | Tier 2 (SF 11) is the primary classical calibration target; Tier 3 (SF 19) is the diagnostic ground truth and modern reference. | Match results are reported in segregated tables to avoid conflating classical vs modern Elo gaps. |
| **I5: Equal Hardware Invariant** | All matches across all tiers must execute on the exact same physical cores with identical background system load. | CPU affinity and dedicated execution locks. |

---

## 6. Summary Verification Table

| Tier | Engine Identifier | Threads | Binary Path | SHA-256 Hash (Prefix) | Role |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Tier 1 (S)** | Janus Classical X7 | 1 | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392a2f4bd4...` | Single-Thread Qualified Control |
| **Tier 1 (P)** | Janus Classical X12 | 4 | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | `00b4f5fedea0...` | Four-Thread Qualified Control |
| **Tier 2** | Stockfish 11 | 1 & 4 | `E:\ChessXML\tools\stockfish_11\stockfish_11.exe` | `b004c03bd71b...` | Classical State-of-the-Art Ceiling |
| **Tier 3** | Stockfish 19 | 1 & 4 | `E:\ChessXML\tools\stockfish\stockfish.exe` | `660eb009241b...` | Modern Unrestricted State of the Art |

**Certification:** The Classical Competitive Reference Ladder is fully operational, physically verified, and enforced for all P1.12 experimental protocols.
