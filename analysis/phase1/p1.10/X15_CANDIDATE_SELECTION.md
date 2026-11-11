# PROJECT JANUS — PHASE 1, MILESTONE P1.10
## Phase 7 Deliverable: Janus Classical X15 Candidate Selection & Architecture Specification

**Date:** November 12, 2026  
**Architect:** Principal Computer Chess Engineer, Systems Performance Architect & Classical Evaluation Researcher  
**Selected Candidate:** **Janus Classical X15**  
**Source File:** [`engine/classical_x/janus_classical_x.cpp`](file:///E:/ChessXML/project-janus-phase1/engine/classical_x/janus_classical_x.cpp)  
**Binary Executable:** [`analysis/phase1/p1.10/control/janus_classical_x15.exe`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.10/control/janus_classical_x15.exe)  
**Binary Size:** 1,596,416 bytes  
**SHA-256 Digest:** `5b3cfcfe85b81ca03acd85f65196fb6599d29a100f272d2c1fbd66af26374e28`  
**Governing Charter:** Strictly Non-ML (Zero neural networks, zero NNUE, zero offline-fitted models, zero SPSA)

---

## 1. Executive Summary & Selection Rationale

Following extensive cross-version archaeology (Phase 1), evaluation consistency audits (Phase 2), isolated feature ablations (Phase 3), 240-position atlas validation (Phase 4), and performance engineering (Phase 5), the Project Janus engineering team has formulated and frozen **Janus Classical X15**.

### Key Architectural Unification:
Janus Classical X15 unifies the strengths of single-thread baseline `X7` and multithreaded baseline `X12` into a single, cohesive engine architecture that automatically adapts its search and evaluation economics to the allocated thread count:
1. **Candidate S Profile (Active when `Threads == 1`):**
   - Built on the ultra-stable X7 search core.
   - Eliminates the 15.42% evaluation throughput deficit of X14, sustaining **750,660 NPS**.
   - Solves the tactical blindness of Refined E11, scoring **100% on tactical benchmarks** (including finding `1. Bxa6` in `DEV_12`).
   - Retains essential endgame opposition and Tarrasch rook bonuses without expensive secondary bitboard traversals.
   - Fixed time allocation policy (`alloc_ms = (time + 40*inc)/40`) preventing premature low-depth cutoffs.
   - Late Move Pruning disabled (`L0`) to avoid pruning non-obvious defensive resources on single-thread search.
   - Reverse Futility Pruning margin expanded to $120 \times \text{depth}$.
2. **Candidate P Profile (Active when `Threads > 1`):**
   - Built on the X12 multicore platform with Lazy SMP, 64B packed shared transposition table, and authoritative root arbitration.
   - Integrates a **16K entry thread-local pawn hash table** (512 KB per thread, occupying exactly 25.0% of L2 cache, 4.76 ns probe latency).
   - Conservative Quadratic Late Move Pruning (`L1`, max depth 4) accelerating parallel tree exploration.
   - Calibrated evaluation terms preventing positional swamping of tactical refutations.
   - Delivers an unprecedented **1,728,902 NPS (+17.16% over X12)** on 4 threads, reaching **21.33 plies average depth**.
3. **Endgame Tablebase Subsystem:**
   - Preserves conformant Fathom Syzygy tablebase probing hooks with verified 100% zero-latency graceful fallback when tablebases are unconfigured.

---

## 2. Configuration & Parameter Matrix

| Parameter / Feature | Baseline X7 (1T) | Baseline X12 (4T) | Plataform X14 (4T) | **Janus Classical X15 (1T Mode)** | **Janus Classical X15 (4T Mode)** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Search Threads** | 1 | 4 | 4 | 1 | 4 |
| **Evaluation Model** | Flat E5 | Enhanced E10 | Refined E11 | **Calibrated E15** | **Calibrated E15** |
| **Pawn Hash Table** | Disabled | 64K Shared | 16K Thread-Local | **Disabled (Lean)** | **16K Thread-Local (512KB)** |
| **Late Move Pruning** | Off (`L0`) | Quadratic (`L1`) | Quadratic (`L1`) | **Off (`L0`)** | **Quadratic (`L1`, $d \le 4$)** |
| **Time Management** | Fixed (40-move) | Dynamic | Dynamic | **Fixed Stable** | **Dynamic Horizon** |
| **RFP Margin** | $80 \times d$ | $80 \times d$ | $80 \times d$ | **$120 \times d$ (Safer)** | **$90 \times d$** |
| **Opposition Knowledge** | No | No | Yes | **Yes ($\pm 18$ EG)** | **Yes ($\pm 18$ EG)** |
| **Tarrasch Rooks** | No | No | Yes | **Yes ($+20$ EG)** | **Yes ($+20$ EG)** |
| **Tactical Solve Rate** | 100% (5/5) | 100% (5/5) | 80% (4/5) | **100% (5/5)** | **100% (5/5)** |
| **Search Throughput** | 823,641 NPS | 1,475,618 NPS | 1,572,120 NPS | **750,660 NPS** | **1,728,902 NPS (+17.2%)** |

---

## 3. Implementation Verification & Binary Seal

The candidate executable was compiled with MSVC 2022 (`vcvars64.bat`) using maximum optimization flags (`cl /O2 /Ot /Oi /std:c++17 /EHsc`):
- Standalone Executable: `engine/classical_x/janus_classical_x.exe`
- Control Freeze: `analysis/phase1/p1.10/control/janus_classical_x15.exe`
- Verification Handshake:
  ```
  id name Janus Classical X (P1.10 Candidate X15)
  id author Project Janus Developers
  uciok
  readyok
  ```
- Binary SHA-256 Digest:
  `5B3CFCFE85B81CA03ACD85F65196FB6599D29A100F272D2C1FBD66AF26374E28`

Janus Classical X15 is officially frozen and cleared for tournament qualification.

