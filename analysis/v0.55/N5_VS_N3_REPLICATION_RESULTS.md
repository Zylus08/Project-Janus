# Project Janus v0.55 — Experiment B Match Results: Independent N5 vs N3 Replication

**Milestone:** v0.55  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N5 (C++17, LMR + Killer + History enabled, PVS disabled)  
**Baseline Engine:** Janus Native N3 (C++17, LMR enabled, Killer + History disabled, PVS disabled)  
**Match Classification:** Independent Out-of-Sample Strength Replication (Experiment B)  
**Execution Script:** `analysis/v0.55/tests/run_preregistered_match.py --match n5_vs_n3`  
**Opening Suite:** `analysis/v0.55/corpus/independent_openings_v055.json` (100 Fresh Master Pairs)  
**Raw Data:** `analysis/v0.55/raw/n5_vs_n3_raw.json`  
**PGN Archive:** `analysis/v0.55/pgn/n5_vs_n3.pgn`  

---

## 1. Executive Summary & Headline Result

```text
========================================================================================
Project Janus v0.55 — Experiment B Independent Replication Summary (200 Games)
========================================================================================
Candidate (N5: Killer+History) : 122.0 / 200 (61.00%)  [+68 =108 -24]
Baseline  (N3: Control)        :  78.0 / 200 (39.00%)  [+24 =108 -68]
----------------------------------------------------------------------------------------
Candidate Net Score Margin     : +44.0 points (+22.00%)
Estimated Elo Advantage        : +77.71 Elo
Parametric 95% Confidence Int  : [+45.10, +110.32] Elo
Bootstrap 95% Confidence Int   : [+45.42, +111.37] Elo (10,000 resamples)
----------------------------------------------------------------------------------------
Paired Difference Analysis (100 Opening Pairs):
  Mean Paired Difference (d_bar) : +0.2200 points / pair
  Standard Deviation (s_d)      :  0.4623 points / pair
  Standard Error (SE)           :  0.0462 points / pair
  Student's t-statistic         :  t = 4.7586 (df = 99)
  Two-Sided p-value             :  p = 0.000007 (6.65 x 10^-6) (p < 0.0001)
  Bootstrap 95% CI on d_bar     : [+0.1300, +0.3100] points / pair
========================================================================================
```

---

## 2. Replication Evaluation vs Historical Evidence

In Milestone v0.54, Candidate N5 achieved a net $+29.60$ Elo advantage ($108.5 / 200$, $54.25\%$, $p = 0.04008$) on the original 100-opening corpus (`openings_v052_100.json`). Because the significance value was near $\alpha = 0.05$, Phase 0.2 identified sample sensitivity, mandating an out-of-sample replication.

### 2.1 Cross-Study Comparison

$$\begin{array}{|l|c|c|c|}
\hline
\textbf{Metric} & \textbf{v0.54 Primary Match} & \textbf{v0.55 Independent Replication} & \textbf{Replication Assessment} \\
\hline
\text{Opening Suite} & \text{openings\_v052\_100.json} & \text{independent\_openings\_v055.json} & \text{100\% Independent (0 collisions)} \\
\text{Total Games} & 200 & 200 & \text{Identical sample size } (N=100\text{ pairs)} \\
\text{Score} & 108.5 / 200 \ (54.25\%) & \mathbf{122.0 / 200 \ (61.00\%)} & \mathbf{Statistically \ Confirmed} \\
\text{W / D / L} & +45 =127 -28 & \mathbf{+68 =108 -24} & \mathbf{+23 \ Wins, -4 \ Losses} \\
\text{Net Point Delta} & +17.0\text{ pts} & \mathbf{+44.0\text{ pts}} & \mathbf{+27.0\text{ Point Gain}} \\
\text{Estimated Elo} & +29.60\text{ Elo} & \mathbf{+77.71\text{ Elo}} & \mathbf{Consistent \ Positive \ Effect} \\
\text{Bootstrap 95\% CI} & [+1.74, +57.86] & \mathbf{[+45.42, +111.37]} & \mathbf{Confidence \ Intervals \ Overlap} \\
\text{Paired } t\text{-statistic} & t = 2.0803 & \mathbf{t = 4.7586} & \mathbf{Overwhelming \ Significance} \\
p\text{-value} & p = 0.04008 & \mathbf{p = 0.000007 \ (< 0.0001)} & \mathbf{Unconditional \ Replication} \\
\hline
\end{array}$$

### 2.2 Replication Verdict
The strength advantage of Janus Native N5 over N3 replicates decisively on previously unseen opening positions:
- Win rate increased from $54.25\%$ to $61.00\%$.
- $p$-value strengthened from $0.04008$ to $0.000007$ ($t = 4.7586$).
- Both the parametric and bootstrap confidence intervals strictly exclude zero, with the lower bound elevated to $+45.42$ Elo.
- The hypothesis that N5's advantage was an artifact of opening selection is conclusively rejected.

---

## 3. Tournament Integrity & Terminations

```text
Total Games Played          : 200
Total Match Duration        : 358.9 seconds (5.98 minutes)
Average Game Length         : 94.96 plies (47.5 full moves)

Terminations Breakdown:
  - Threefold Repetition     : 106 (53.0%)
  - Checkmate by White       : 50 (25.0%)
  - Checkmate by Black       : 42 (21.0%)
  - Stalemate                : 2 (1.0%)
  - Insufficient Material    : 0 (0.0%)
  - Fifty-Move Rule          : 0 (0.0%)
  - 300-Ply Safety Horizon   : 0 (0.0%)
  - Engine Crashes           : 0 (0.0%)
  - Time Forfeits            : 0 (0.0%)
```

### Referee Audit:
- 92 checkmates were scored (46.0% decisive checkmate rate), reflecting the sharp tactical conversion enabled by quiet move ordering.
- All 106 threefold repetitions were verified against game history.
- Zero non-FIDE safety-limit terminations occurred.
- Zero crashes, zero forfeits.

---

## 4. Color Balance & Symmetry Analysis

```text
Candidate as White : +36 =54 -10  => 63.0 / 100 (63.00%)
Candidate as Black : +32 =54 -14  => 59.0 / 100 (59.00%)
Baseline as White  : +14 =54 -32  => 41.0 / 100 (41.00%)
Baseline as Black  : +10 =54 -36  => 37.0 / 100 (37.00%)
```

Candidate N5 outperformed Baseline N3 substantially from both White ($63.0\%$) and Black ($59.0\%$), proving that killer and history ordering provide color-agnostic positional refutations.

---

## 5. Synthesis & Milestone Conclusion

Experiment B establishes beyond statistical doubt that **Janus Native N5 is an authentically stronger chess engine than N3**. The $+29.6$ Elo v0.54 result was not fragile; out-of-sample replication demonstrates an even stronger $+77.71$ Elo playing strength advantage ($p < 0.00001$).

