# PHASE 11: CANDIDATE SELECTION & FORMAL BINARY FREEZE

**Project:** Project Janus — Phase 1, Milestone P1.15  
**Candidate Designation:** Janus Classical X20 (X20-S & X20-P)  
**Date:** November 14, 2026  
**Auditor:** Principal Computer Chess Engine Architect & Systems Performance Engineer  
**Deliverable:** `analysis/phase1/p1.15/X20_CANDIDATE_SELECTION.md`  
**Frozen Binaries Path:** `analysis/phase1/p1.15/control/`  

---

## 1. Candidate Justification & Selection Overview

Following comprehensive empirical auditing across Phases 1 through 10, the creation of Candidate **Janus Classical X20** is fully justified by reproducible evidence:
1. **MovePicker Legality & Completeness:** 100% legal move enumeration preserved across 1,019 stratified test positions and 32,232 legal moves (0 omissions, 0 duplicates, 0 illegal moves).
2. **Tactical Sacrifice Recovery (C1):** Promoting near-even captures ($-100 \le \text{SEE} < 0$) into Stage 4.5 resolves the horizon trap in defensive tactical crises (Game 12 resolved in $18.7\times$ fewer nodes).
3. **History Score Stabilization (H2):** Conservative $\frac{7}{8}$ history aging between searches eliminates stale score persistence, driving first-move beta-cutoff rate ($\text{BF}_1$) to **98.96%**.
4. **Exact Minimax Preservation:** 240 / 240 pairwise comparisons across depths 1–4 matched reference minimax scores with 100.00% exact numerical identity.
5. **Multi-Threaded Superiority:** In factorial testing, X20-P (4T) achieved an average depth of **13.75 plies at 250ms (+1.75 plies ahead of Baseline X12's 12.00 plies)**, searching $3.65\times$ fewer nodes.

---

## 2. Frozen Candidate Configurations

Two distinct resource profiles are frozen under the unified X20 architecture:

### Track S: Janus Classical X20-S (Single-Thread Candidate)
- **Threads:** 1
- **Hash Size:** 16 MB (1,048,576 entries)
- **Variant Flag:** `UCI_Variant X20`
- **MovePicker Policy:** C1 (Near-Even Promotion $[-100, 0)$ to Stage 4.5)
- **History Policy:** H2 (Conservative Decay $\times \frac{7}{8}$ per search)
- **Evaluation:** E5 Combined Classical Evaluation
- **Tactical Ordering:** M2 Countermove Heuristic
- **Pruning & Selectivity:** Calibrated L3 Dynamic LMR, Null-Move Pruning (R=3), Reverse Futility Pruning (margin $120\times d$), Q2 SEE Quiescence Pruning.

### Track P: Janus Classical X20-P (Four-Thread Candidate)
- **Threads:** 4
- **Hash Size:** 64 MB Parallel Lockless Shared Transposition Table
- **Variant Flag:** `UCI_Variant X20`
- **MovePicker Policy:** C1 (Near-Even Promotion $[-100, 0)$ to Stage 4.5)
- **History Policy:** H2 (Conservative Decay $\times \frac{7}{8}$ per search)
- **Evaluation:** E10 Enhanced Classical Evaluation
- **Pawn Cache:** 16K-entry thread-local Pawn Hash Table
- **Pruning & Selectivity:** Calibrated L3 Dynamic LMR, Safe Late Move Pruning (LMP Mode 1), RFP (margin $90\times d$), Adaptive Time Management.

---

## 3. Cryptographic Checksums & Source Verification

All confirmatory tournament testing and external calibrations must execute against these exact frozen artifacts:

| Artifact | File Path | Exact SHA-256 Checksum |
|---|---|---|
| **C++17 Source Snapshot** | `analysis/phase1/p1.15/control/janus_classical_x20.cpp` | `3B9011F6D341F6B4079C60E97F0EB7E65411AD82710269B9163D9A1FD645D734` |
| **Candidate Executable** | `analysis/phase1/p1.15/control/janus_classical_x20.exe` | `AF126A4D22C312F2AE61014A56005B9E9BAFD022F95A17DA81D81769048F7415` |
| **Candidate Shared DLL** | `analysis/phase1/p1.15/control/janus_classical_x20.dll` | `C706D7160D25D37BCD482518DAABE94864ADF2D81F532BB0305DC6E92F4C3255` |

### Frozen Control Baselines & External References:
- **Janus Classical X7 (1T Baseline):** `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B`
- **Janus Classical X12 (4T Baseline):** `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059`
- **Janus Classical X19 (Research Baseline):** `CBB7785A47E5F9EC64C51C20B8387DE3EFE782F42BDFCEA38008F6450E534629`
- **Stockfish 4 (Official Release):** `E:\ChessXML\tools\stockfish_4\stockfish_4.exe`
- **Stockfish 11 (Official Release):** `E:\ChessXML\tools\stockfish_11\stockfish_11.exe`
- **Stockfish 19 (edb0d9d, Default NNUE):** `E:\ChessXML\tools\stockfish\stockfish.exe`

---

## 4. Build Environment & Compilation Flags

The candidate binaries were built using the certified host toolchain:
- **Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64
- **Language Standard:** ISO C++17 (`/std:c++17`)
- **Compilation Flags:** `/O2 /Oi /Ot /GL /std:c++17 /EHsc /DNDEBUG`
- **Linker Flags:** `/link /LTCG /OPT:REF /OPT:ICF`
- **Host OS:** Windows 11 x64 (AMD64 architecture)
- **Opening Corpus:** `analysis/v0.56/corpus/independent_openings_v056.json` (50 unbiased colour-reversed opening pairs).

---

## 5. Candidate Freeze Protocol Declaration

As required by Project Janus governance:
1. No source code modifications may be committed to candidate X20 binaries after this declaration.
2. All confirmatory strength matches (Phases 12 and 13) must run exclusively with the frozen binaries above.
3. If confirmatory tournaments reveal any regression or failure to outperform baselines, the candidate cannot be modified post-hoc; the result will be reported objectively under Phase 14 Adjudication.

