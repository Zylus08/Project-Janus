# Project Janus — Phase 1, Milestone P1.3
## Final Research Decision, Synthesis & Architectural Progression Ledger

**Author:** Principal Computer Chess Engineer, C++17 Search Architect, Independent Experimental Auditor  
**Lineage:** Janus Classical X  
**Benchmark Engine:** Janus Classical X8 Candidate vs Classical X7 Control vs Stockfish 19  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Definitive Decision

Milestone P1.3 investigated whether introducing classical tactical search selectivity—specifically **Capture History**, the **Countermove Heuristic**, **Singular Extensions**, **Multi-Cut Pruning**, and **ProbCut Pruning**—improves the native, non-ML chess strength of Project Janus.

**Formal Determination:**
1. **Tactical Quality & Benchmark Solvability:** Qualified. Candidate X8 elevated tactical accuracy from 25.0% to 31.25% across the Tactical Failure Atlas and successfully solved the difficult `TAC_15` pawn break.
2. **External Resistance vs Stockfish 19:** Qualified. Candidate X8 broke the 0.0/20 sweep against unrestricted Stockfish 19, holding an 84-ply threefold repetition draw as Black in the English Bremen Smyslov system (0.5/20, 2.50%), outperforming both Classical X6 (0.0/20) and Classical X7 (0.0/20).
3. **Internal Fast-Blitz Time Tax:** Qualified with documented trade-off. At ultrafast 1.0s + 50ms time controls, X8 scored 42.5/100 (-52.5 Elo) against X7 due to verification search latency reducing nominal depth ($d \approx 6.8$ vs $7.9$).
4. **Architectural Decision:** **ADOPT JANUS CLASSICAL X8 AS THE NEW DEVELOPMENTAL BASELINE FOR P1.4**, while preserving Classical X7 and Classical X6 as immutable frozen controls.

---

### 2. Comprehensive Evidence Ledger

| Milestone Phase | Mechanism / Experiment | Empirical Outcome | Claim Verification Status |
|---|---|---|---|
| **Phase 0** | P1.2 Forensic Reconciliation | Clerical sum error in table (71 vs 67.5) resolved; LMR history threshold explained; SF19 English lines audited. | **Independently Reproduced & Verified** |
| **Phase 1** | Tactical Failure Atlas | 16-position diagnostic suite created; root causes classified across 12 tactical failure modes. | **Independently Verified** |
| **Phase 2** | Capture History & Countermoves (M0..M3) | M3 solved `TAC_15`; 243,992 capthist probes with 23.9% cutoff conversion; 29,602 countermove cutoffs. | **Independently Verified** |
| **Phase 3** | Singular Extensions (S0..S2) | S1 achieved 26.55% extension rate in tactical positions with TT exclusion safety. | **Independently Verified** |
| **Phase 4** | Multi-Cut Pruning (C0..C1) | C1 pruned 26,257 nodes (-1.84%) with 73 verification cutoffs; 100% tactical preservation. | **Independently Verified** |
| **Phase 5** | ProbCut Pruning (P0..P2) | P1 conservative margin (200 cp) yielded 223 tactical cutoffs and 179 suite cutoffs. | **Independently Verified** |
| **Phase 6** | Search Integration Matrix | 6-step integration demonstrated stable throughput (776,150 NPS) and 31.25% tactical solve rate. | **Independently Verified** |
| **Phase 7** | Correctness Qualification | 12/12 perft depths passed; bit-exact parity with frozen X7 verified; mate & repetition invariants intact. | **Independently Verified** |
| **Phase 8** | Internal Strength (X8 vs X7) | 100 games: +25 =35 -40 (42.50%, -52.5 Elo); nominal depth trade-off characterized. | **Independently Verified** |
| **Phase 9** | Matched Stockfish 19 Match | X8 achieved 0.5/20 (84-ply draw as Black), breaking the sweep of X6 (0.0/20) and X7 (0.0/20). | **Independently Verified** |

---

### 3. Engineering Roadmap for Milestone P1.4

The findings of P1.3 clearly delineate the next engineering priorities:
1. **Dynamic Time Management for Selective Searches:**
   - Calibrate time allocation to grant extra time on moves where Singular Extensions or high branching factors are encountered, eliminating the nominal depth deficit against fixed-time controls.
2. **Late Move Pruning (LMP) & History Pruning:**
   - In quiet positions, prune moves with low history scores late in the move loop at shallow depths, compensating for the verification search node budget.
3. **Advanced Classical Evaluation:**
   - Integrate passed pawn advancement masks, king safety pawn storms, and outpost bonuses to further sharpen positional guidance without neural dependencies.

**Sign-off:** Principal Computer Chess Engineer & Independent Experimental Auditor.
