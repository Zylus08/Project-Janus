# Candidate Selection & Freezing Specification (Phase 12 Report)
**Project Janus — Phase 1, Milestone P1.18**
**Frozen Candidate:** Janus Classical X23 (X23-S / X23-P)
**Control Directory:** `analysis/phase1/p1.18/control/`
**Date:** 2026-11-14

---

## 1. Candidate Nomination & Selection Rationale

Following the exhaustive forensic investigations in Phases 0–6, the targeted C++17 evaluation implementation in Phase 7, the factorial search analysis in Phase 8, the pawn hash latency benchmarking in Phase 9, and the 7-gate correctness qualification in Phase 11, **Janus Classical Candidate X23** is formally selected and frozen as the milestone research candidate.

Candidate X23 represents the convergence of:
1. **P1.16 Corrected Quiescence Semantics (Q1):** Full legal evasion generation in check, eliminating illegal stand-pat assumptions.
2. **P1.17 True Outpost Immunity:** Enemy pawn attack ray spans verified on bitboards to distinguish permanent piece outposts from transient squares.
3. **P1.17 64K Thread-Local Pawn Hash Table:** Enabled on both 1T and 4T configurations, accelerating evaluation by $+13.5\%$ and absorbing pawn structure computation costs.
4. **P1.18 Track A Backward Pawn Detection:** Classical rearmost pawn detection with enemy stop-square control and absence of friendly support behind/alongside ($-10$ mg / $-15$ eg), fully cached in the pawn hash table with zero search latency overhead.
5. **P1.18 Track B Open & Semi-Open File King Exposure Penalty:** Handcrafted positional penalties for rooks and queens bearing down on open and semi-open king files (capped at $-80$ mg).

---

## 2. Frozen Artifact Hashes & Binary Integrity

All candidate binaries and source code are frozen in `analysis/phase1/p1.18/control/`:

| File Name | File Type | Size (Bytes) | SHA-256 Checksum |
| :--- | :---: | :---: | :--- |
| `janus_classical_x23.exe` | Win64 Executable | 258,048 | `39E875841B36AC82F464ABC7F31DB19D7CF5ABCD0F15B0A923B086A5BB393E39` |
| `janus_classical_x23.dll` | Win64 Shared Lib | 239,616 | `482789FAA7069EECEB9B4F2AFA1A9F61D9BBC10CC1F22002C817B6DF87036367` |
| `janus_classical_x23.cpp` | C++17 Source | 232,014 | `CBBDA4A915013E19725628C0B1B5B7FD578639B3AC7174B1D1B8E7E29AE71298` |

### Compiler Record
- Compiler: Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64
- Flags: `/O2 /Oi /Ot /std:c++17 /EHsc`
- Optimization: Maximizing speed, inlining enabled, fast math intrinsics.

---

## 3. Configuration Matrix: X23-S vs X23-P

| Parameter | Track S: Janus Classical X23-S | Track P: Janus Classical X23-P |
| :--- | :---: | :---: |
| **Target Architecture** | Single-Thread (1T) | Symmetric Multiprocessing (4T) |
| **Search Threads** | 1 | 4 |
| **Evaluation Mode** | Mode 5 ($E5$) | Mode 10 ($E10$) |
| **Pawn Hash Table** | 64K entries (Thread-local, 2 MB) | 64K entries per thread (Thread-local, 2 MB/thread) |
| **Quiescence Search** | Mode 1 ($Q1$ Corrected) | Mode 1 ($Q1$ Corrected) |
| **Adaptive Captures** | Mode 1 ($C1$ Near-Even) | Mode 1 ($C1$ Near-Even) |
| **Continuation History** | Mode 3 ($H3$) | Mode 3 ($H3$) |
| **Dynamic LMR** | Mode 3 ($L3$ History Modulated) | Mode 3 ($L3$ History Modulated) |
| **Late Move Pruning** | Disabled | Conservative Quadratic ($L1$, depth $\le 4$) |
| **RFP Margin** | $120\text{ cp/depth}$ | $90\text{ cp/depth}$ |
| **Outpost Semantics** | True Outposts ($+28$ mg / $+18$ eg) | True Outposts ($+28$ mg / $+18$ eg) |
| **Backward Pawns** | Track A Enabled ($-10$ mg / $-15$ eg) | Track A Enabled ($-10$ mg / $-15$ eg) |
| **King File Exposure** | Track B Enabled (Capped $-80$ mg) | Track B Enabled (Capped $-80$ mg) |

---

## 4. Frozen Baselines & Historical Reference Checksums

For the independent strength tournament matches, the following control binaries are utilized:
- **X7 Baseline (1T):** `analysis/phase1/p1.3/control/janus_classical_x7.exe`
  - SHA-256: `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B`
- **X12 Baseline (4T):** `analysis/phase1/p1.7/control/janus_classical_x12.exe`
  - SHA-256: `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059`
- **X22 Reference (1T):** `analysis/phase1/p1.17/control/janus_classical_x22.exe`
  - SHA-256: `35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C`

Candidate X23 is completely frozen and immutable.
