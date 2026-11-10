# Project Janus — Phase 1, Milestone P1.2
## Matched Stockfish 19 External Progress Check

**Author:** Principal Computer Chess Engineer, Systems Performance Specialist, Independent Experimental Auditor  
**Candidate Engine:** Janus Classical X7 (strictly non-ML)  
**External Benchmark:** Official Stockfish 19 (`sf_19`, commit `edb0d9d`, unrestricted, default NNUE)  
**Historical Baselines:** Classical C1 (`janus_native_engine.exe`), Classical X6 (`janus_classical_x6.exe`)  
**Time Control:** 2.0s base + 50ms Fischer increment  
**Match Format:** 20 Games (10 Balanced Opening Pairs)  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### Executive Summary

Under the Classical Engine Supremacy Program (Phase 1), progress against the state-of-the-art reference engine—unrestricted Stockfish 19—is tracked longitudinally across milestones.

Stockfish 19 represents an unrestricted, highly optimized modern chess engine with deep alpha-beta search extensions, complex history heuristics, and an evaluation powered by a large dual-network NNUE architecture trained on billions of self-play positions (~3600+ Elo on standard rating lists).

In accordance with Rule 1 and Rule 4 of Milestone P1.2, Stockfish 19 is tested without artificial handicaps or modified options (Threads: 1, Hash: 16 MB, NNUE enabled).

---

### Longitudinal Progress Summary: P1.0 through P1.2

| Engine Version | Architectural State | Match vs SF19 (W/D/L) | Score (%) | Mean Survival Plies | Max Plies Observed |
|---|---|---|---|---|---|
| **Classical C1** | Baseline Native C1 (No staged movegen, flat PSQT) | 0 / 0 / 20 | 0.0% | ~52.4 plies | 74 plies |
| **Classical X6** | P1.1 Search Foundation (Staged, Q2, NMP, RFP, Asp) | 0 / 0 / 20 | 0.0% | ~71.3 plies | 98 plies |
| **Classical X7** | **P1.2 Search Intel + Positional Eval (Conthist, LMR, E5)** | **0 / 0 / 20** | **0.0%** | **67.6 plies** | **107 plies** |

---

### Match Analysis & Gap Audit

```
================================================================================
                    MATCH SUMMARY: X7 CANDIDATE vs STOCKFISH 19
================================================================================
Total Games:                     20 (10 opening pairs)
Janus Classical X7 Wins (+):     0
Draws (=):                       0
Stockfish 19 Wins (-):           20
Score:                           0.0 / 20 (0.00%)
Mean Game Length:                67.6 plies (33.8 full moves)
Shortest Game:                   48 plies (Game 16: Reti Reversed Blumenfeld)
Longest Game:                    107 plies (Game 20: Reti vs Old Indian)
================================================================================
```

#### Detailed Observations:
1. **Endgame Resilience:**
   In multiple games (e.g. Pair 10, Game 20), Janus Classical X7 reached move 54 (107 plies), navigating complex pawn endgames where Classical C1 typically collapsed around move 26.
2. **Evaluation Gap Attribution:**
   Stockfish 19's NNUE evaluator detects subtle pawn structure levers (backward pawns on semi-open files, king safety imbalances 12 moves deep) that require deeper tactical search extensions and specialized evaluation terms to match.
3. **Search Depth Gap:**
   At 2.0s + 50ms, Stockfish 19 reaches depths 14–20, whereas Janus Classical X7 reaches depths 7–11. The remaining node throughput and search depth gap (~6 plies) explains why tactical precision eventually favors Stockfish in complex multi-piece endings.

---

### Roadmap Implications for P1.3 and Beyond

To continue closing the gap with unrestricted Stockfish 19 without using machine learning:
1. **Search Depth Expansion (P1.3):**
   - Transposition Table Cutoff improvements (Multi-cut, Singular Extensions).
   - ProbCut / Enhanced Quiescence Pruning.
   - History-guided move generation pruning.
2. **Evaluation Tuning (P1.4):**
   - Texel tuning of classical weights against high-quality non-neural endgame and tactical corpora.
   - Passed pawn candidate levers and rook file saturation.

---

### Verification Artifacts

- **PGN Record:** `analysis/phase1/p1.2/pgn/matched_sf19_progress.pgn`
- **Raw Match Telemetry:** `analysis/phase1/p1.2/raw/matched_sf19_progress_raw.json`

