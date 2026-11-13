# PROJECT JANUS — PHASE 1, MILESTONE P1.12
## Janus Classical X17 Candidate Freeze Specification

**Document ID:** `analysis/phase1/p1.12/X17_CANDIDATE_FREEZE.md`  
**Milestone:** Phase 1, Milestone P1.12  
**Status:** Certified Candidate Freeze Record  
**Date:** 2026-11-12  
**Auditor:** Principal Computer Chess Engineer & Independent Statistical Auditor  
**Certified Binary Path:** `analysis/phase1/p1.12/control/janus_classical_x17.exe`  
**Certified Source Path:** `analysis/phase1/p1.12/control/janus_classical_x17.cpp`  

---

## 1. Candidate Overview & Freezing Declaration

Following $100\%$ compliance across all Stage 1 correctness and reliability qualification benchmarks (detailed in [`P112_CORRECTNESS_AND_REGRESSION.md`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.12/P112_CORRECTNESS_AND_REGRESSION.md)), the experimental search candidate **Janus Classical X17** is hereby formally frozen.

Janus Classical X17 embodies the **Classical Baseline Reboot**:
1. Complete elimination of all Direction A mechanisms (`!improving` LMR dampening and unconditional stack static evaluation) that caused the $-117.2\text{ Elo}$ collapse of X16 in Milestone P1.11.
2. Direct restoration of the qualified classical baseline foundations: **Janus Classical X7** for single-threaded execution (Track S) and **Janus Classical X12** for multithreaded execution (Track P).
3. Implementation of the single empirically justified selective search safeguard: **Targeted Pawn Endgame LMR Safety**, which prevents quiet pawn moves from being reduced in pure pawn endgames (`non_pawn_mat == 0`), directly resolving the pawn breakthrough calculation failure identified in `END_04`.

---

## 2. Technical Specification

### 2.1 Track S Profile: Janus Classical X17-S (Single-Threaded Mode)
- **Execution Target:** Single core / 1 search thread (`Threads 1`).
- **Evaluation Engine:** Handcrafted Classical $E5$ Positional Evaluation (Material + Piece-Square Tables + Mobility + King Safety + Basic Pawn Structure). Zero NNUE, zero learned parameters.
- **Move Ordering:** Staged move generator ($M0$ baseline): Hash move $\to$ Good captures (MVV/LVA + SEE) $\to$ Killers (2 slots) $\to$ History heuristic $\to$ Continuation history ($H3$: 1-ply + 2-ply) $\to$ Bad captures $\to$ Quiets.
- **Selective Pruning:**
  - Reverse Futility Pruning: Active at $\text{depth} \le 3$, static eval computed strictly lazily, margin $= 120\text{ cp} \times d$.
  - Null-Move Pruning: Adaptive $R = 3$, verified against non-pawn zugzwang invariant.
  - Aspiration Windows: $\pm 25\text{ cp}$ iterative re-search window.
- **LMR Architecture:**
  - Calibrated logarithmic-logarithmic reduction table ($L3$).
  - Continuation history modulation ($\pm 1$ ply based on 1-ply/2-ply continuation history).
  - **P1.12 Safeguard:** Quiet pawn moves are exempted from LMR in pure pawn endgames ($\text{non\_pawn\_mat} == 0$).
- **Throughput Profile:** $2.46\text{M}$ to $3.52\text{M}$ NPS on modern x64 hardware.

### 2.2 Track P Profile: Janus Classical X17-P (Four-Thread Parallel Mode)
- **Execution Target:** 4 hardware threads (`Threads 4`).
- **Parallel Search Architecture:** Lazy SMP with lockless shared Transposition Table (128 MB default). Thread divergence via thread-index depth offsets.
- **Evaluation Engine:** Handcrafted Classical $E10$ Enhanced Positional Evaluation + Thread-Local Pawn Hash Table.
- **Move Ordering:** Countermove heuristic enabled ($M2$) + Staged movegen.
- **Selective Pruning:**
  - Conservative Quadratic Late Move Pruning ($LMP$, $\text{max\_depth} \le 4$).
  - Reverse Futility Pruning ($90\text{ cp} \times d$).
  - Dynamic Time Management.
  - Targeted pure pawn endgame LMR safety.
- **Throughput Profile:** $7.2\text{M}$ to $7.5\text{M}$ NPS on 4 physical cores.

---

## 3. Provenance & Cryptographic Artifacts

| Artifact | Location | File Size | SHA-256 Digest |
| :--- | :--- | :---: | :--- |
| **Engine Source** | `engine/classical_x/janus_classical_x.cpp` | 136,894 bytes | `8bc8cf6ee96f7c73a0ef093a0273a5a4c9bfca345fe310864380eb7c95e1e791` |
| **Archived Source** | `analysis/phase1/p1.12/control/janus_classical_x17.cpp` | 136,894 bytes | `8bc8cf6ee96f7c73a0ef093a0273a5a4c9bfca345fe310864380eb7c95e1e791` |
| **Engine Binary** | `engine/classical_x/janus_classical_x.exe` | 1,599,488 bytes | `04c17f68ef4fc327bf3443b60b61ac23a40c6e985c1af5caedb5c42b42ac684a` |
| **Archived Binary** | `analysis/phase1/p1.12/control/janus_classical_x17.exe` | 1,599,488 bytes | `04c17f68ef4fc327bf3443b60b61ac23a40c6e985c1af5caedb5c42b42ac684a` |

### Compilation Environment:
- **Compiler:** Microsoft Visual C++ 2022 (MSVC v143), x64 Command Line Compiler
- **Compilation Command:**
  ```cmd
  cl.exe /c /O2 /Oi /Ot /std:c++17 /EHsc /DNDEBUG janus_classical_x.cpp
  link.exe /INCREMENTAL:NO /NOLOGO janus_classical_x.obj /OUT:janus_classical_x.exe
  ```
- **Compiler Output:** 0 errors, 0 warnings.

---

## 4. Verification Checkpoint

```
[x] Perft Suite (Startpos D1-D5, Kiwipete D1-D4): 100% Exact Pass
[x] Evaluation Symmetry Invariance (8 symmetric FENs): 100% Zero-Delta Pass
[x] Mate Precision Suite (Scholar's, Legal's, Back-rank, Anastasia's): 100% Pass
[x] Search Determinism & Stability (10 positions repeat test): 100% Pass
[x] Low-Clock Resilience (51 searches @ 10-50ms): 100% Zero-Forfeit Pass
[x] Binary & Source Cryptographic Archive: Verified (SHA-256 Match)
```

**Certification:** Candidate Janus Classical X17 is formally frozen and authorized for competitive strength testing against Tier 1 controls and external benchmarks under JCTS v2.
