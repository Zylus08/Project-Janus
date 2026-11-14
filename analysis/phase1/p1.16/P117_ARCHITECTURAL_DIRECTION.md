# Milestone P1.16 Phase 14: Strategic Architectural Direction for Milestone P1.17

**Date:** November 14, 2026  
**Status:** Approved Architectural Roadmap  
**Branch:** `phase1/classical-janus`  
**Foundation Candidate:** Janus Classical X21 (`2226c0c`)  
**Frozen Baselines to Overcome:** Janus Classical X7 (1T, `b34e342`) and Janus Classical X12 (4T, `78ca3d5`)  

---

## 1. Executive Scientific Synthesis of Milestone P1.16

Milestone P1.16 achieved the most comprehensive, rigorous forensic overhaul of Janus's search and evaluation architecture to date:

1. **Quiescence Search Integrity Restored (100% Correctness):** Eliminated illegal stand-pat beta-cutoffs in check, checkmate blindness, and negative-SEE evasion omissions. Verified across 40/40 positions spanning seven tactical categories.
2. **Evaluation Efficiency Breakthrough (+52.1% NPS):** Implemented a 64K-entry direct-mapped pawn hash table, elevating single-thread search throughput from 1.26M NPS to 1.92M NPS with zero symmetry drift.
3. **Competitive Reality Established (Category B):** Definitively demonstrated that quiescence correctness, while necessary to eliminate catastrophic blunders (enabling 29 wins across Stockfish 4, 11, and 19), cannot overcome qualified baselines X7 and X12 without expanding classical evaluation terms and recalibrating search pruning.

```
       [ Legacy Janus X7 / X12 ]                [ Janus Classical X21 ]
          - Flawed QSearch                         + 100% Correct QSearch
          - Mate blindness under check             + True Mate / Stalemate logic
          - High raw NPS via pruning leaks         + 64K Pawn Hash (+52.1% NPS)
          - Shallow tactical evaluation            - Basic E5 Evaluation (Material + PST)
                     \                                   /
                      \                                 /
                   =========================================
                   PROJECT JANUS P1.17 ARCHITECTURAL TARGET
                   - Preserve X21 Correctness & Pawn Hash
                   - Introduce 4 Target Classical Eval Terms
                   - Recalibrate Classical Main-Tree Pruning
                   - Defeat X7 (1T) & X12 (4T) with Lower CI > 50%
                   =========================================
```

---

## 2. The Core Deficiency: The Classical Evaluation Ceiling

The 420 tournament games in P1.16 conclusively revealed why X21 scored 45.5% at 1.0s and 39.0% at 2.5s against X7. 

At deeper plies (depth 10–13), tactical oversights become rare for both engines. The outcome of games is determined by **static evaluation quality in quiet endgames and king-pressure positions**. Janus currently relies on the minimalistic E5 evaluation function:
- Material counting with basic phase weights.
- Static Piece-Square Tables (PST).
- Primitive pawn structure terms (isolated, doubled, passed).
- Basic piece mobility counting.

When reaching king-and-pawn endgames or complex middlegames, Janus evaluates positions with vastly inferior precision compared to mature classical engines:
- **Blindness to Outposts:** A knight on `d5` defended by a pawn (`c4` or `e4`) is evaluated almost identically to a knight on `d5` undefended and easily kicked by `...c6`.
- **Blindness to Open Files:** Rooks on closed files receive virtually the same evaluation as rooks dominating the open `e`-file or occupying the 7th rank.
- **Blindness to King Danger:** King safety is evaluated solely by counting adjacent friendly pawns. An opponent queen and bishop aiming directly at an uncastled or weakened king receives no attacking bonus.

---

## 3. Milestone P1.17 Architectural Program: Three Foundational Pillars

Milestone P1.17 must execute three targeted, strictly classical engineering interventions:

### Pillar 1: Authoritative Classical Evaluation Terms (HCE Expansion)
Implement four mathematically rigorous, non-ML classical evaluation terms:
1. **Pawn Outposts with Pawn Immunity:**
   - Detect knights and bishops on ranks 4–6 that cannot be attacked by enemy pawns.
   - Grant bonuses for outposts supported by friendly pawns ($+25$ to $+40$ cp).
2. **Rook Activity on Open & Semi-Open Files:**
   - Detect rooks with no friendly pawns on the file ($+20$ cp for open, $+10$ cp for semi-open).
   - Grant major positional bonuses for rooks occupying the 7th rank ($+35$ cp) when attacking enemy pawns or cutting off the enemy king.
3. **Connected & Candidate Passed Pawn Dynamics:**
   - Upgrade passed pawn evaluation to scale non-linearly by rank ($20, 35, 60, 110, 180$ cp).
   - Implement Tarrasch rule: bonus for friendly rooks behind passed pawns ($+25$ cp).
4. **Classical Quadratic King Danger Tables:**
   - Implement an attacking piece counter (king ring danger zones: 8 surrounding squares + 3 facing squares).
   - Weight attackers: Knight = 2 units, Bishop = 2 units, Rook = 3 units, Queen = 5 units.
   - Apply quadratic penalty: $\text{Penalty} = \frac{\text{Units}^2 \times 8}{\text{King Defenses}}$.

### Pillar 2: Calibrated Classical Search Pruning
Because X21's quiescence search properly explores legal evasions under check, the leaf search is more thorough. To match or exceed X7's main-tree depth, search pruning must be rebalanced:
1. **Calibrated Late Move Reductions (LMR):** Adjust reduction formulas for quiet moves at depth $\ge 3$ based on history score and check status.
2. **Futility & Reverse Futility Pruning:** Safely prune non-tactical moves near leaf nodes when static evaluation exceeds beta by margins exceeding piece values.
3. **Adaptive Null-Move Verification:** Maintain strict zugzwang verification while allowing $R=3$ null-move cutoffs in non-pawn endgames.

### Pillar 3: Multi-Thread SMP Performance Scaling
1. **Thread-Local Pawn Caches:** Scale X21's 64K pawn hash table into thread-local structures to eliminate thread contention in 4T SMP search.
2. **Maintain Throughput Target:** Ensure candidate search throughput exceeds 1.8M NPS on 1T and 5.5M NPS on 4T.

---

## 4. Gating & Verification Plan for Milestone P1.17

1. **Phase 1: Feature Implementation & Unit Testing:** Implement the 4 evaluation terms in `janus_classical_x.cpp`. Verify 100% color symmetry on mirrored FENs.
2. **Phase 2: Correctness Suite:** Re-verify perft (Startpos D1–D4, KiwiPete D1–D3), legality, determinism, and thread-safety.
3. **Phase 3: Tactical & Positional Benchmark:** Re-test 30-position tactical suite and 40-position quiescence suite. Ensure 0 regressions.
4. **Phase 4: Independent Tournament Promotion:**
   - Match 1: Candidate X22-S vs Janus Classical X7 (100 games @ 1.0s+50ms). **Gating:** Paired CI lower bound $> 50.0\%$ ($p < 0.05$).
   - Match 2: Candidate X22-S vs Janus Classical X7 (50 games @ 2.5s+100ms). **Gating:** Score $\ge 50.0\%$.
   - Match 3: Candidate X22-P vs Janus Classical X12 (100 games @ 1.0s+50ms, 4T SMP). **Gating:** Paired CI lower bound $> 50.0\%$ ($p < 0.05$).

**Charter Reaffirmation:** Under no circumstances will automated parameter fitting, SPSA, Texel tuning, or neural networks be permitted. Milestone P1.17 will achieve promotion through rigorous, pure classical computer chess engineering.
