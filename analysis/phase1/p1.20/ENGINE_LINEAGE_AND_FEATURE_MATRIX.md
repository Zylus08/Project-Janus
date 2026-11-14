# Classical Engine Lineage & Architectural Feature Matrix

## 1. Executive Summary

Milestone P1.20 establishes a definitive architectural lineage and feature matrix across all foundational classical engines in Project Janus: from the qualified immutable strength baselines (**X7** and **X12**) through the research reference lineage (**X19**, **X20**, **X21**, **X22**) to the rejected experimental candidates (**X23** and **X24**).

### Governing Epistemological Invariant:
> **Critical Requirement:** Never attribute an empirical strength difference to evaluation knowledge when the compared binaries also differ in search algorithms, move-ordering staging, pruning thresholds, or runtime settings without strictly controlling for those differences.

---

## 2. Comprehensive Architectural Lineage Matrix

| Feature / Subsystem | Janus Classical X7 (P1.3) | Janus Classical X12 (P1.7) | Janus Classical X19 (P1.14) | Janus Classical X20 (P1.15) | Janus Classical X21 (P1.16) | Janus Classical X22 (P1.17) | Janus Classical X23 (P1.18) | Janus Classical X24 (P1.19) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Milestone / Commit** | P1.3 / `b34e342` | P1.7 / `78ca3d5` | P1.14 / `bcfdecd` | P1.15 / `563f1db` | P1.16 / `abd99c5` | P1.17 / `e33f292` | P1.18 / `bb87254` | P1.19 / `bcf8f4c` |
| **Architectural Role** | Qualified 1T Strength Baseline | Qualified 4T SMP Strength Baseline | Move-Ordering Reference | Adaptive Capture Reference | Pawn-Hash Candidate | Certified Research Reference | Rejected Combined Eval Candidate | Rejected Isolated Track A Candidate |
| **Executable SHA-256** | `86392A2F...` | `00B4F5FE...` | `CBB7785A...` | `AF126A4D...` | `AD1E1F05...` | `35D095CF...` | `39E87584...` | `FBEAF907...` |
| **Compiler & Flags** | MSVC x64 `/O2 /Oi /Ot /std:c++17` | MSVC x64 `/O2 /Oi /Ot /std:c++17` | MSVC x64 `/O2 /Oi /Ot /std:c++17` | MSVC x64 `/O2 /Oi /Ot /std:c++17` | MSVC x64 `/O2 /Oi /Ot /std:c++17` | MSVC x64 `/O2 /Oi /Ot /std:c++17` | MSVC x64 `/O2 /Oi /Ot /std:c++17` | MSVC x64 `/O2 /Oi /Ot /std:c++17` |
| **Default Threads** | 1 Thread | 4 Threads (SMP) | 1 Thread | 1 Thread | 1 Thread | 1 Thread | 1 Thread | 1 Thread |
| **Transposition Table**| 64 MB Direct XOR | 64 MB Lockless XOR | 64 MB Direct XOR | 64 MB Direct XOR | 64 MB Direct XOR | 64 MB Direct XOR | 64 MB Direct XOR | 64 MB Direct XOR |
| **Pawn Hash Table** | Disabled | Disabled | Disabled (1T) / 64K (4T) | Disabled (1T) / 64K (4T) | 64K Direct Mapped | 64K Direct Mapped (+13.6% NPS) | 64K Direct Mapped | 64K Direct Mapped (+13.6% NPS) |
| **Evaluation Scheme** | E0 (Base Material + PST + Mobility) | E0 (Base Material + PST + Mobility) | E5 Combined Classical | E5 Combined Classical | E5 Combined Classical | E5 + True Outposts (Ray-immune) | E5 + Track A (BP) + Track B (KFE) | E5 + Track A (BP only, KFE excised) |
| **Quiescence Search** | Q0 (Standard Stand-Pat) | Q0 (Standard Stand-Pat) | Q0 (Standard Stand-Pat) | Q0 (Standard Stand-Pat) | Q1 (Initial Evasion Fix) | Q1 Certified (Full In-Check Evasions) | Q1 Certified (Full In-Check Evasions) | Q1 Certified (Full In-Check Evasions) |
| **MovePicker Staging** | M0 (Captures $\to$ Quiets) | M0 (Captures $\to$ Quiets) | M2 (Good Caps $\to$ Killers $\to$ CM $\to$ Quiets $\to$ Bad Caps) | M2 + C1 (Adaptive Near-Even Captures) | M2 + C1 | M2 + C1 | M2 + C1 | M2 + C1 |
| **LMR Configuration** | Fixed ($R=1$) | Fixed ($R=1$) | L3 Calibrated (Pawn Endgame Protected) | L3 Calibrated | L3 Calibrated | L3 Calibrated | L3 Calibrated | L3 Calibrated |
| **Null Move Pruning** | $R=3$, non-pawn guard | $R=3$, non-pawn guard | $R=3$, non-pawn guard | $R=3$, non-pawn guard | $R=3$, non-pawn guard | $R=3$, non-pawn guard | $R=3$, non-pawn guard | $R=3$, non-pawn guard |
| **Reverse Futility** | Margin 120 cp/ply | Margin 90 cp/ply | Margin 120 cp/ply | Margin 120 cp/ply | Margin 120 cp/ply | Margin 120 cp/ply | Margin 120 cp/ply | Margin 120 cp/ply |
| **Aspiration Windows** | $\pm 25$ cp | $\pm 25$ cp | $\pm 25$ cp | $\pm 25$ cp | $\pm 25$ cp | $\pm 25$ cp | $\pm 25$ cp | $\pm 25$ cp |
| **Time Management** | Standard Fischer Clock | SMP Workload Dynamic | Standard Fischer Clock | Standard Fischer Clock | Standard Fischer Clock | Standard Fischer Clock | Standard Fischer Clock | Standard Fischer Clock |

---

## 3. Microscopic Delta Analysis: Reference X22 vs Candidate X24

A bit-for-bit code audit between `janus_classical_x22.cpp` and `janus_classical_x24.cpp` confirms that:

1. **Search Parity:**
   - Alpha-beta root loop, PVS implementation, move generation staging (M2), killer move ordering, countermove heuristic, history heuristic, and continuation history (H3) are **100% identical**.
   - Pruning algorithms (Null Move Pruning $R=3$, Reverse Futility Pruning, Late Move Reductions L3, Aspiration Windows $\pm 25\text{ cp}$) are **100% identical**.
   - Transposition table size (64 MB), bucket layout, and collision replacement policies are **100% identical**.
2. **Quiescence Search Parity:**
   - Both engines use certified Q1: legal check evasions generated when in check, stand-pat suppressed when in check, negative-SEE captures pruned unless escaping or delivering check.
3. **Pawn-Hash Architecture:**
   - Both engines feature the 64K-entry direct-mapped pawn hash table.
4. **The Sole Independent Variable:**
   - In X22: `g_use_backward_pawns = 0`. Backward pawns are not penalized.
   - In X24: `g_use_backward_pawns = 1`. Backward pawns on half-open/closed files unable to advance safely or receive friendly pawn support are penalized $-10\text{ mg} / -15\text{ eg}$.
   - King-file exposure is permanently zero in both engines (`g_use_king_file_exposure = 0`).

### Empirical Verification of Zero Unintended Churn:
When Candidate X24 is launched with `setoption name UCI_BackwardPawns value false`:
- Over 100 positions, X24 produces **identical best moves, identical nodes, and identical evaluations** to Reference X22.
- Therefore, any strength or depth difference observed between X22 and X24 is **strictly and exclusively caused by the backward-pawn term and its search interactions**.

---

## 4. Architectural Observations across the Full Lineage

1. **Why X7 and X12 Remain Formidable:**
   - Baseline X7 uses a primitive evaluation function ($E0$) that evaluates only material, piece-square tables, and basic mobility. It executes with almost zero branching drag and has no structural terms that trigger aspiration failures or search instability.
   - Baseline X12 possesses an exceptionally clean multithreaded lockless TT implementation with a lower RFP margin (90 cp/ply) that aggressively prunes dead subtrees.
2. **The "Feature Accumulation" Hazard:**
   - From X19 to X23, each milestone added evaluation features (bishop pair, rook open file, true outposts, backward pawns, king file exposure).
   - Although each term is logically valid according to human chess theory, accumulating static terms without calibrating pruning thresholds (RFP, NMP, LMR) alters the effective score distribution, frequently triggering search re-searches and shallowing effective search depth.
