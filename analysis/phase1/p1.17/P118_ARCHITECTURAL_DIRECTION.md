# Milestone P1.17 — Architectural Direction & Roadmap for Milestone P1.18

**Author:** Principal Computer Chess Architect & Performance Systems Engineer  
**Date:** November 14, 2026  
**Reference Engine Baseline:** Janus Classical X22 (`35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C`)  
**Frozen Baselines to Overcome:** Janus Classical X7 (`b34e342`, 1T), Janus Classical X12 (`78ca3d5`, 4T)  

---

## 1. Context & Architectural State at the Close of P1.17

Milestone P1.17 successfully stabilized the foundational search and tactical evaluation of Project Janus:
1. **Quiescence Search Legality:** Q1 stand-pat evasions are now permanent, eliminating leaf checkmate blindness without causing tactical search explosions.
2. **Evaluation Infrastructure:** A 64K thread-local pawn hash table is active, operating with 86.2% hit rates and zero concurrency overhead.
3. **Positional Stabilization:** True outposts with enemy pawn immunity recovered practical playing strength, reaching 50.0% vs X7 (55.0% at slow TC) and defeating X21 by +70.4 Elo.

However, X22 does not yet possess the statistical margin ($CI_{low} > 50.0\%, p < 0.05$) required to supplant X7 and X12 as the official baselines. Detailed profiling of the 118 losses against Stockfish and the 31 losses against X7 points to three dominant remaining bottlenecks:
- **Pawn Structure Evaluation Deficits:** The pawn hash table currently caches only rudimentary isolated pawn penalties.
- **King Safety Blind Spots:** Attack unit calculations lack dynamic pawn shelter evaluation and semi-open file penetration penalties.
- **Search Pruning Recalibration:** LMR and RFP thresholds are still calibrated around legacy (buggy) Q0 evaluations.

---

## 2. Priority Architectural Targets for Milestone P1.18

### Priority 1: Advanced Classical Pawn Structure Evaluation (Cached in Pawn Hash)
*Objective:* Leverage the 64K pawn hash table to compute sophisticated pawn structure terms without incurring per-node CPU penalties.
- **Candidate Passed Pawns & Protected Passed Pawns:**
  - Award progressive bonuses for passed pawns based on rank (ranks 4–7), distance to promotion, and whether they are supported by friendly pawns or blocked by enemy pieces.
- **Backward & Doubled Pawns:**
  - Implement formal backward pawn detection (pawns behind adjacent friendly pawns on half-open files).
  - Scale doubled pawn penalties based on file openness.
- **Pawn Islands & Phalanxes:**
  - Implement connected pawn bonuses (phalanxes on ranks 4–6) to guide central pawn pushes.

### Priority 2: Asymmetric King Safety & King Attack Zone Heuristics
*Objective:* Prevent the kingside collapses observed in Match 5 and Match 6 against Stockfish.
- **King Pawn Shield Deficits:**
  - Penalize missing g- and h-pawns after castling kingside.
  - Penalize open and semi-open files directed at the friendly king square.
- **Attacking Zone Geometry:**
  - Implement a 3x3 virtual attack zone surrounding the enemy king.
  - Count the number of attacking piece trajectories intersecting this zone, applying an exponential scale (e.g. 2 attackers = small pressure, 4+ attackers = severe danger).

### Priority 3: Classical Search Pruning Recalibration
*Objective:* Recover search depth lost to quiescence evasions without increasing tactical blunder rates.
- **History-Adjusted Pruning:**
  - Condition late-move reductions (LMR) on quiet history scores. Moves with high positive continuation history should receive reduced LMR, while moves with negative history receive aggressive pruning.
- **Futility Pruning Margin Alignment:**
  - Align pre-quiescence futility pruning margins with the truthful bounds provided by Q1.

---

## 3. Strict Experimental Methodology for P1.18

1. **Immutable Baseline Protocol:** All qualification tests must run against frozen baselines X7 (`b34e342`) and X12 (`78ca3d5`) using identical opening corpora and time controls.
2. **Harness Integrity Assertion:** The validated P1.17 tournament harness (with absolute White-perspective score conversion and immediate checkmate checks) must remain mandatory.
3. **Zero ML Charter:** Texel tuning, SPSA, NNUE, and learned parameters remain strictly prohibited. Every evaluation parameter must be handcrafted, physically intuitive, and mathematically verified for mirror symmetry.
