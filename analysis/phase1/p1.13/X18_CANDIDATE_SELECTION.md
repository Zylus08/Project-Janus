# Candidate X18 Selection & Cryptographic Freeze Report
**Project Janus — Phase 1, Milestone P1.13**
**Author:** Principal Computer Chess Engine Architect & Systems Performance Engineer
**Repository:** `E:\ChessXML\project-janus-phase1`
**Parent Commit:** `5b44c3f`
**Date:** November 13, 2026

---

## 1. Executive Summary & Candidate Specification

Following successful correctness qualification and developmental ablations, the experimental candidate is officially frozen as:
- **Janus Classical X18-S:** Track S candidate for single-threaded classical competition.
- **Janus Classical X18-P:** Track P candidate for four-threaded classical competition.

Candidate X18 introduces a single targeted architectural selectivity intervention: **History-Modulated Late Move Reductions (History-LMR)**, which dynamically modulates quiet-move reduction depth by the move's history heuristic score $H$:
- High-performing quiet moves ($H > +8000$) are preserved ($R = \max(1, R - 1)$).
- Low-performing quiet moves ($H < -2000$ at $d \ge 5$) are truncated ($R = R + 1$).
- Pure pawn endgames are protected from LMR zugzwang truncation.

---

## 2. Cryptographic Manifest & Toolchain Provenance

| Component | Path / Value | Cryptographic Digest (SHA-256) |
| :--- | :--- | :--- |
| **Developmental Source** | `engine/classical_x/janus_classical_x.cpp` | `0dca902ef67767017fb51f89edd986e0144bfbec199ab34a5220a69dcf7d9728` |
| **Certified Binary** | `analysis/phase1/p1.13/control/janus_classical_x18.exe` | `912c8554928a1845d3f16e699fe06b970fc7eeb3ab6ee6c37900fe81662b6b50` |
| **Shared Library** | `engine/classical_x/janus_classical_x.dll` | `e2a53239a52864ea54817d23d8c117b38d33caad8e2e256b27e4db9556d11703` |
| **Binary Size** | 1,600,000 bytes | — |
| **Compiler & Flags** | MSVC 2022 (v143, x64), `/O2 /Ot /Oi /std:c++17 /EHsc /link /INCREMENTAL:NO` | — |

---

## 3. Configuration & Search Settings

### 3.1 Track S: Janus Classical X18-S (Single-Threaded Track)
- **Threads:** 1
- **Hash Allocation:** 64 MB
- **Evaluation Engine:** E5 Combined Classical Positional Evaluation (Material, PSQT, Mobility, King Safety, Pawn Structure).
- **Move Ordering:** Staged Movegen, Hash move, Good captures (MVV/LVA), 2 Killer slots, History table, Bad captures, Quiet moves.
- **Selectivity:** PVS Negamax, Null Move Pruning ($R=3$), Reverse Futility Pruning ($120\text{ cp/ply}$), Aspiration Windows ($\pm 25\text{ cp}$), **History-Modulated LMR (L2)**, Pawn Endgame LMR Protection.
- **Pawn Hash / Dynamic Time / LMP:** Disabled (maintaining pure X7 foundation invariants).

### 3.2 Track P: Janus Classical X18-P (Four-Threaded Track)
- **Threads:** 4
- **Hash Allocation:** 256 MB (64B Packed Shared Lockless TT).
- **Evaluation Engine:** E10 Enhanced Classical Evaluation.
- **Move Ordering:** Countermove Heuristic (M2), 2 Killer slots, History + Continuation History (H3).
- **Selectivity:** PVS Negamax, Null Move Pruning ($R=3$), Reverse Futility Pruning ($90\text{ cp/ply}$), Safe Quadratic Late Move Pruning (LMP), **History-Modulated LMR (L2)**, Pawn Endgame LMR Protection.
- **Pawn Hash / Dynamic Time:** Enabled (64K entry pawn hash table, dynamic clock allocation).

**Candidate Freeze Status:** SEALED AND IMMUTABLE. No source or configuration modifications are permitted prior to competitive evaluation.

