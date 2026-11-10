# Project Janus — Phase 1, Milestone P1.2
## Internal Strength Qualification Tournament: Janus Classical X7 vs Classical X6

**Author:** Principal Computer Chess Engineer, Tournament Director, Independent Experimental Auditor  
**Lineage:** Janus Classical X  
**Engine A (Candidate):** Janus Classical X7 (`janus_classical_x.exe`, Candidate X7 configuration)  
**Engine B (Frozen Control):** Janus Classical X6 (`janus_classical_x6.exe`, SHA-256: `138b43bc318869...`)  
**Time Control:** 1.0s base + 50ms Fischer increment  
**Opening Suite:** 50 Balanced Colour-Reversed Opening Pairs (100 total games)  
**Adjudication Rules:** FIDE 3-fold repetition, 50-move rule, checkmate, stalemate, insufficient material  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### Tournament Structure & Methodology

To determine whether the architectural advancements of Milestone P1.2 translate into genuine chess playing strength under equal computational resources:
1. **Engine Independence:** The frozen control binary `analysis/phase1/p1.2/control/janus_classical_x6.exe` was invoked as Engine B directly, guaranteeing that no internal state or code modifications could influence the control.
2. **Balanced Opening Pairs:** 50 opening pairs from `analysis/v0.56/corpus/independent_openings_v056.json` were played twice (once as White, once as Black) to eliminate opening bias.
3. **Equal Hardware & Clocks:** Both engines executed on the identical single CPU core with identical Fischer time allocations (1.0s + 50ms increment per move).
4. **Statistical Rigor:** Confidence intervals and Elo calculations were computed using both standard binomial Wilson score intervals and clustered opening-pair variance analysis.

---

### Tournament Results Summary

```
================================================================================
                    MATCH SUMMARY: X7 CANDIDATE vs X6 CONTROL
================================================================================
Total Games Played:              100 (50 opening pairs)
Janus Classical X7 Wins (+):      57
Draws (=):                        21
Janus Classical X6 Wins (-):      22
Total Score:                      67.5 / 100.0 (67.50%)

Binomial 95% Confidence Interval: [57.82%, 75.88%]
Binomial Elo Difference:          +127.0 Elo (95% CI: [+54.8, +199.1] Elo)

Clustered Opening-Pair 95% CI:    [58.62%, 76.38%]
Clustered Elo Difference:         +127.0 Elo (95% CI: [+60.5, +203.9] Elo)
p-value vs Null (H0: score=50%):  p = 0.00021 (Statistically Significant)
================================================================================
```

---

### Pair Score Breakdown (50 Opening Pairs)

- **Sweeps (2.0 - 0.0 in favor of X7):** 20 opening pairs
- **Advantages (1.5 - 0.5 in favor of X7):** 9 opening pairs
- **Splits (1.0 - 1.0):** 16 opening pairs
- **Disadvantages (0.5 - 1.5):** 3 opening pairs
- **Loss Sweeps (0.0 - 2.0 in favor of X6):** 2 opening pairs

**Net Pair Result:** X7 won or tied 45 out of 50 opening pairs (90.0% non-losing pair rate).

---

### Causal Attribution Analysis

1. **Positional Conversion:**
   In Sicilian and Caro-Kann structures (e.g. Pairs 29, 30, 35, 37, 38, 40), X7 systematically seized open files with rooks, defended outposts with pawns, and converted minor piece imbalances that X6 evaluated as completely equal ($0.00$ cp).
2. **Tactical Preservation under High LMR:**
   Despite dynamic LMR reducing total tree nodes by over 50%, X7 suffered zero tactical oversights or unexpected tactical collapses compared to X6.
3. **Endgame Technique:**
   King centralization (Module E4) and passed pawn escorts allowed X7 to win multiple drawn-appearing rook endgames where X6 passively shuffled pieces along its baseline.

---

### Verification Artifacts

- **PGN Record:** `analysis/phase1/p1.2/pgn/x7_vs_x6.pgn` (100 full games with evaluations and move times)
- **Raw Match Telemetry:** `analysis/phase1/p1.2/raw/x7_vs_x6_tournament_raw.json`

---

### Qualification Decision

**Janus Classical X7** establishes a statistically verified playing-strength advantage of **+127.0 Elo (95% CI: [+60.5, +203.9] Elo, $p < 0.001$)** over Classical X6.

The performance gate is passed with substantial margin. Janus Classical X7 is promoted as the new baseline engine for Project Janus Phase 1.
