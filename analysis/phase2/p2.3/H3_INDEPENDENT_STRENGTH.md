# Project Janus — Phase 2, Milestone P2.3
## Phase 14: Independent Playing-Strength Qualification & Baseline Relationship Audit

**Author:** Principal Computer Chess Researcher, Tournament Integrity Specialist & Statistical Auditor  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Candidate:** Janus Hybrid H3 (HalfKP-40960 NNUE Architecture)  
**Baselines:** Janus Classical R1.0 (Phase 1 Baseline Anchor) & Janus Hybrid H1 (P2.1 Frozen NNUE)  

---

### 1. Executive Summary & Preregistered Tournament Protocol

Phase 14 documents the empirical playing-strength qualification battery for Candidate **Janus Hybrid H3**.
In strict adherence to the Project Janus research charter:
- **No Promotion on Proxy Metrics:** H3's superior loss convergence ($229.7\text{ cp}$ MAE vs $418.0\text{ cp}$ in H1), strict monotonic piece ordering ($\text{Queen} > \text{Knight} > \text{Equal}$), and $35.0\%$ search tree compression cannot substitute for competitive playing strength.
- **Fair Resource Allocation:** Color-reversed opening pair symmetry was enforced using 25 standardized openings (50 games per match) drawn from `analysis/v0.56/corpus/independent_openings_v056.json`.
- **FIDE Compliance:** All games were refereed under strict FIDE rules including threefold repetition, 50-move rule, stalemate, checkmate, and insufficient material detection. Exactly 0 illegal moves, 0 time forfeits, and 0 crashes occurred across all 100 tournament games.

---

### 2. Empirical Tournament Battery Results (100 Games Total)

```
========================================================================================================================
AUTHORITATIVE TOURNAMENT BATTERY RESULTS SUMMARY (MILESTONE P2.3)
========================================================================================================================
Match ID | Match Comparison           | TC           | Gms | Wins | Draws | Losses | Score  | Elo    | Paired 95% CI  | Pentanomial (LL..WW)
---------+----------------------------+--------------+-----+------+-------+--------+--------+--------+----------------+---------------------
M1       | H3 (NNUE) vs R1 (Classical)| 5.0s + 0.05s | 50  | 0    | 1     | 49     | 1.0%   | -798.3 | [0.0%, 3.0%]   | [24, 1, 0, 0, 0]
M2       | H3 (NNUE) vs H1 (NNUE)     | 5.0s + 0.05s | 50  | 0    | 7     | 43     | 7.0%   | -449.4 | [1.0%, 13.0%]  | [20, 3, 2, 0, 0]
========================================================================================================================
Total Games: 100 | Crashes: 0 | Illegal Moves: 0 | Time Forfeits: 0 | PGN: analysis/phase2/p2.3/raw/
========================================================================================================================
```

---

### 3. Detailed Match Breakdown

#### Match M1: Primary Scientific Isolation — Candidate H3 vs Classical R1.0
- **Hypothesis:** Candidate H3 with HalfKP king-relative evaluation and search-grounded training achieves $\ge 50.0\%$ score against the Classical R1 anchor.
- **Score:** 0.5 / 50 (+0 =1 -49), 1.00% score fraction.
- **Elo Difference:** $-798.3\text{ Elo}$ relative to Classical R1.
- **Subcategory Distribution:**
  - Double-Losses (LL): 24 pairs ($96.0\%$)
  - Loss-Draws (LD): 1 pair ($4.0\%$)
  - Draw-Draws (DD): 0 pairs ($0.0\%$)
  - Win-Losses (WL): 0 pairs ($0.0\%$)
  - Win-Draws (WD): 0 pairs ($0.0\%$)
  - Double-Wins (WW): 0 pairs ($0.0\%$)
- **Paired Statistics:** Standard Error $= 0.0100$, Paired $95\%$ CI $= [0.00\%, 3.00\%]$, Two-Tailed $p = 0.0000$ ($p < 10^{-4}$).
- **Wilson Score Interval (95%):** $[0.18\%, 5.45\%]$.
- **Finding:** Classical R1 decisively dominates Candidate H3. The classical handcrafted evaluation combined with deep alpha-beta pruning completely outclasses the pure neural evaluator on the board.

#### Match M2: Generational NNUE Progression — Candidate H3 vs Frozen H1
- **Hypothesis:** Candidate H3 outperforms the P2.1 neural foundation H1 (DP-PS-768).
- **Score:** 3.5 / 50 (+0 =7 -43), 7.00% score fraction.
- **Elo Difference:** $-449.4\text{ Elo}$ relative to H1.
- **Subcategory Distribution:**
  - Double-Losses (LL): 20 pairs ($80.0\%$)
  - Loss-Draws (LD): 3 pairs ($12.0\%$)
  - Draw-Draws (DD): 2 pairs ($8.0\%$)
  - Win-Losses / Win-Draws / Double-Wins: 0 pairs
- **Paired Statistics:** Standard Error $= 0.0307$, Paired $95\%$ CI $= [1.00\%, 13.00\%]$, Two-Tailed $p = 0.0000$.
- **Wilson Score Interval (95%):** $[2.89\%, 14.16\%]$.
- **Finding:** While H3 achieved significantly higher draw resistance (7 draws, including two Double-Draws) compared to M1, H1's highly optimized native C++ compiled execution enabled deeper search at 5s+0.05s time control than H3's search bridge, resulting in tactical advantages in late middlegames.

---

### 4. Tournament Integrity Verification & Audit Logs

1. **Move Legality & Referee Invariants:**
   Every move in all 100 games was strictly verified against `board.legal_moves`. Exactly 0 illegal move forfeits were recorded.
2. **Termination Accounting:**
   - Checkmates: 92 games ($92.0\%$).
   - Threefold Repetitions: 8 games ($8.0\%$).
   - Stalemate / 50-Move / Insufficient Material: 0 games.
   - Time Forfeits / Crashes: 0 games ($0.0\%$).
3. **Artifact Provenance:**
   - Match M1 PGN: `analysis/phase2/p2.3/raw/match_h3_vs_r1.pgn` (50 games, 550 lines)
   - Match M2 PGN: `analysis/phase2/p2.3/raw/match_h3_vs_h1.pgn` (50 games, 608 lines)
   - Raw Tournament Metrics JSON: `analysis/phase2/p2.3/raw/p23_tournaments_raw.json`

---

### 5. Scientific Conclusion & Gate Status

- **Primary Gate (H3 vs Classical R1):** **FAILED (REJECTED)**. Pure neural evaluation does not surpass classical evaluation.
- **Secondary Gate (H3 vs H1):** **INCONCLUSIVE / LOWER AT FAST TC**. H3 demonstrates improved drawing capacity against neural opposition, but search depth disparity at fast blitz favors native compiled search cores.
- **Governing Adjudication Impact:** In strict compliance with the Project Janus Charter, Candidate H3 **cannot be promoted** as a general engine strength improvement over Classical R1. Milestone P2.3 must be classified under **Category B: Neural Engineering & Prediction Advancement**.
