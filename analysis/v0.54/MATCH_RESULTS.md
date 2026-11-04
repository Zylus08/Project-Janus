# Project Janus v0.54 — Primary Match Results: C3 (Candidate N5) vs C0 (Baseline N3)

**Milestone:** v0.54  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N5 (C3: `UseKillerOrdering=true`, `UseHistoryOrdering=true`)  
**Baseline Engine:** Janus Native N3 (C0: `UseKillerOrdering=false`, `UseHistoryOrdering=false`)  
**Match Classification:** Primary Preregistered Playing-Strength Evaluation  
**Execution Script:** `analysis/v0.54/tests/run_preregistered_match.py`  
**Raw Data:** `analysis/v0.54/raw/c3_vs_c0_primary_raw.json`  
**PGN Archive:** `analysis/v0.54/pgn/c3_vs_c0_primary.pgn`  

---

## 1. Experimental Conditions & Tournament Integrity

All 200 games were conducted strictly according to the preregistered protocol (`analysis/v0.54/MATCH_PREREGISTRATION.md`):
- **Pairing Scheme:** 100 opening pairs with exact color reversal (Candidate plays White in Game 1, Black in Game 2).
- **Opening Suite:** 100 diverse balance-curated openings drawn from standard competitive corpora (ECO A00–E99).
- **Time Control:** Equal Fischer 3.0s base + 100ms increment per move.
- **Hardware Concurrency:** 8 independent parallel worker processes pinned to isolated UCI instances.
- **Transposition Table:** 16 MB per engine instance, cleared completely before every game via `ucinewgame`.
- **Search Invariants:** LMR enabled in both engines (`UseLMR=true`), PVS disabled (`UsePVS=false`).
- **Adjudication Standard:** FIDE-compliant referee enforcement via `python-chess` (checkmate, stalemate, 50-move rule, threefold repetition, insufficient material) plus a mandatory 300-ply non-FIDE safety horizon.

---

## 2. Head-to-Head Playing-Strength Summary

```
========================================================================================
Project Janus v0.54 — Primary Tournament Head-to-Head Summary (200 Games)
========================================================================================
Candidate (C3: Killer+History) : 108.5 / 200 (54.25%)  [+45 =127 -28]
Baseline  (C0: Control)        :  91.5 / 200 (45.75%)  [+28 =127 -45]
----------------------------------------------------------------------------------------
Candidate Net Score Advantage  : +17.0 points (+8.50%)
Candidate Score by Color       : White: 54.5 / 100 (54.50%) | Black: 54.0 / 100 (54.00%)
Baseline Score by Color        : White: 46.0 / 100 (46.00%) | Black: 45.5 / 100 (45.50%)
Estimated Elo Difference       : +29.60 Elo
Parametric 95% Confidence Int  : [+1.70, +57.51] Elo
Bootstrap 95% Confidence Int   : [+1.74, +57.86] Elo (10,000 resamples)
----------------------------------------------------------------------------------------
Paired Difference Analysis (100 Opening Pairs):
  Mean Paired Difference (d_bar) : +0.0850 points / pair
  Standard Deviation (s_d)      :  0.4086 points / pair
  Standard Error (SE)           :  0.0409 points / pair
  Student's t-statistic         :  t = 2.0803 (df = 99)
  Two-Sided p-value             :  p = 0.04008  (Statistically Significant at alpha = 0.05)
  Bootstrap 95% CI on d_bar     : [+0.0050, +0.1650] points / pair
========================================================================================
```

---

## 3. Statistical Significance and Hypothesis Testing

### 3.1 Null and Alternative Hypotheses
- **$H_0$ (Null Hypothesis):** Native killer and history move ordering confers no playing-strength advantage over the baseline quiet-move ordering ($\mu_d = 0$, $\text{Elo}_\Delta \le 0$).
- **$H_1$ (Alternative Hypothesis):** Native killer and history move ordering confers a statistically significant playing-strength improvement ($\mu_d > 0$, $\text{Elo}_\Delta > 0$).

### 3.2 Paired Student's t-Test
Because games were conducted in opening pairs with reversed colors, paired differences $d_i = \text{score}_{\text{cand}, i} - \text{score}_{\text{base}, i}$ were computed for each pair $i \in [1, 100]$:
$$d_i \in \{-1.0, -0.5, 0.0, +0.5, +1.0\}$$
- Pairs won by Candidate (2–0 or 1.5–0.5): 20 pairs
- Pairs drawn (1–1): 67 pairs
- Pairs lost by Candidate (0–2 or 0.5–1.5): 13 pairs
- Mean difference:
  $$\bar{d} = \frac{20 \times (+0.5 \text{ to } +1.0) - 13 \times (+0.5 \text{ to } +1.0)}{100} = +0.0850$$
- Sample standard deviation: $s_d = 0.4086$
- Standard error of the mean:
  $$SE = \frac{s_d}{\sqrt{N}} = \frac{0.4086}{10} = 0.04086$$
- Test statistic:
  $$t = \frac{\bar{d} - 0}{SE} = \frac{0.0850}{0.04086} = 2.0803$$
- Degrees of freedom: $df = 99$
- Two-sided $p$-value: **$p = 0.04008$** ($p < 0.05$).

### 3.3 Non-Parametric Bootstrap Verification
To guarantee robustness against any departures from normality in paired difference scores, 10,000 bootstrap resamples with replacement of the 100 opening pairs were performed:
- 2.5th percentile of $\bar{d}^*$: **$+0.0050$ points/pair**
- 97.5th percentile of $\bar{d}^*$: **$+0.1650$ points/pair**
- Bootstrap 95% Confidence Interval for Elo: **$[+1.74, +57.86]$ Elo**

Crucially, **the 95% confidence interval strictly excludes zero** on both the parametric and non-parametric evaluations.

---

## 4. Game Terminations & Operational Reliability

```
Total Games Played          : 200
Total Plies Elapsed         : 19,489
Average Game Length         : 97.45 plies (48.7 full moves)
Shortest Game               : 29 plies (checkmate)
Longest Game                : 218 plies (threefold repetition)

Terminations Breakdown:
  - Checkmate by White       : 37 (18.5%)
  - Checkmate by Black       : 36 (18.0%)
  - Threefold Repetition     : 126 (63.0%)
  - Insufficient Material    : 1 (0.5%)
  - Fifty-Move Rule          : 0 (0.0%)
  - Stalemate                : 0 (0.0%)
  - 300-Ply Safety Horizon   : 0 (0.0%)
  - Engine Crashes / Forfeits: 0 (0.0%)
  - Time Forfeits            : 0 (0.0%)
```

### Referee Adjudication Audit
- Every single threefold repetition claim was independently validated against the complete move history on a strict `chess.Board` instance. All 126 claims satisfied FIDE Article 9.2 (same position occurring 3 times with identical active player, castling rights, and en passant availability).
- Zero games triggered the emergency non-FIDE 300-ply horizon, verifying that neither engine entered non-progress wander loops.
- Time management operated flawlessly across all 200 games with 0 time forfeits.

---

## 5. Color and Side Symmetry Analysis

```
Candidate as White : +22 =65 -13  => 54.5 / 100 (54.50%)
Candidate as Black : +23 =62 -15  => 54.0 / 100 (54.00%)
Baseline as White  : +15 =62 -23  => 46.0 / 100 (46.00%)
Baseline as Black  : +13 =65 -22  => 45.5 / 100 (45.50%)
```

The candidate displayed nearly identical performance as White (+54.5%) and Black (+54.0%), demonstrating that the move ordering heuristics are color-agnostic and robust across both sides of the board.

---

## 6. Conclusion and Milestone Assessment

The primary 200-game match delivers clear empirical proof:
1. **Playing Strength Advantage:** Candidate C3 achieved **+29.60 Elo** over Baseline C0.
2. **Statistical Significance:** With $p = 0.04008 < 0.05$ and a 95% bootstrap CI of $[+1.74, +57.86]$ Elo strictly excluding zero, the result meets the preregistered acceptance criterion for **Category A promotion**.
3. **Flawless Tournament Integrity:** Zero crashes, zero forfeits, 100% verified legal FIDE adjudications, and zero safety-horizon terminations.
