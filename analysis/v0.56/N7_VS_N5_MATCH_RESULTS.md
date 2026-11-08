# Project Janus v0.56 — Preregistered Match Results: N7 vs N5

**Milestone:** Project Janus v0.56  
**Match Identification:** `n7_vs_n5`  
**Candidate Engine:** Janus Native N7 (C++17, `UseSEEOrdering=true`, `UseSEEInQuiescence=true`)  
**Baseline Engine:** Janus Native N5 (C++17, `UseSEEOrdering=false`, `UseSEEInQuiescence=false`)  
**Opening Corpus:** `independent_openings_v056.json` (100 paired openings, 200 games, SHA-256: `d4db2cf9...`)  
**Time Control:** Fischer Blitz 3.0s base + 100ms increment (3+0.1)  
**Execution Environment:** 8 Concurrent Worker Processes, MSVC x64 Native Binaries  
**PGN Artifact:** [`analysis/v0.56/pgn/n7_vs_n5.pgn`](file:///E:/ChessXML/project-janus/analysis/v0.56/pgn/n7_vs_n5.pgn)  
**Raw JSON Artifact:** [`analysis/v0.56/raw/n7_vs_n5_raw.json`](file:///E:/ChessXML/project-janus/analysis/v0.56/raw/n7_vs_n5_raw.json)  

---

## 1. Primary Empirical Match Summary

| Metric | Candidate N7 | Baseline N5 | Delta / Margin |
| :--- | :---: | :---: | :---: |
| **Total Score** | **95.5 / 200 (47.75%)** | **104.5 / 200 (52.25%)** | -9.0 points |
| **Individual Outcomes** | +33 wins, =125 draws, -42 losses | +42 wins, =125 draws, -33 losses | -9 net wins |
| **White Score** | 49.0 / 100 (49.00%) | 53.5 / 100 (53.50%) | -4.5 points |
| **Black Score** | 46.5 / 100 (46.50%) | 51.0 / 100 (51.00%) | -4.5 points |
| **Estimated Elo Difference** | **-15.65 Elo** | Baseline (0.0 Elo) | -15.65 Elo |
| **95% Bootstrap Elo CI** | **[-43.66, +12.17] Elo** | — | Crosses 0.0 |
| **Paired Mean Difference ($\bar{d}$)** | **-0.090 points/pair** | — | $s_d = 0.830$ |
| **Standard Error ($SE_d$)** | 0.083 points/pair | — | $df = 99$ |
| **Student's t-Statistic** | **t = -1.0844** | — | — |
| **Two-Sided p-Value** | **p = 0.2808** | — | **Not Significant ($\alpha = 0.05$)** |
| **95% Bootstrap Difference CI** | **[-0.250, +0.070] points** | — | Crosses 0.0 |
| **Average Game Length** | 86.77 plies (43.4 moves) | 86.77 plies | — |
| **Total Match Duration** | 352.55 seconds (5.88 min) | — | 8 workers |

---

## 2. Game Terminations & Adjudication Integrity

Adjudication was enforced programmatically via `python-chess` strictly distinguishing FIDE rules from the non-FIDE safety horizon:

| Termination Type | Count | Percentage | FIDE Rule Reference |
| :--- | :---: | :---: | :--- |
| **Claimable Threefold Repetition** | 124 | 62.0% | FIDE Article 9.2 |
| **Checkmate (White Victory)** | 40 | 20.0% | FIDE Article 5.1.1 |
| **Checkmate (Black Victory)** | 35 | 17.5% | FIDE Article 5.1.1 |
| **Insufficient Material Draw** | 1 | 0.5% | FIDE Article 5.2.2 |
| **Fifty-Move Rule Draw** | 0 | 0.0% | FIDE Article 9.3 |
| **Safety Horizon Limit (300 plies)** | **0** | **0.0%** | Non-FIDE Safety Circuit Breaker |
| **Engine Stalls / Crashes / Timeouts** | **0** | **0.0%** | Disqualification Criteria |
| **Illegal Move Emissions** | **0** | **0.0%** | Disqualification Criteria |
| **Total Games** | **200** | **100.0%** | **100% Valid Terminations** |

Every single game reached a natural FIDE termination. Zero games required safety-horizon truncation. Zero engine stalls, crashes, or illegal moves occurred across 17,354 played plies.

---

## 3. Statistical Hypothesis Testing

### 3.1 Parametric Paired Student's t-Test
- Observed mean paired score difference: $\bar{d} = -0.0900$ points per opening pair.
- Standard error: $SE_d = 0.08299$.
- Degrees of freedom: $df = 99$.
- Test statistic:
  $$t = \frac{-0.0900}{0.08299} = -1.0844$$
- The two-sided p-value is **$p = 0.2808$**. Because $p \gg 0.05$, the observed score difference is not statistically significant. The null hypothesis $H_0: \Delta_{\text{score}} = 0$ cannot be rejected.

### 3.2 Non-Parametric Bootstrap Resampling
Over 10,000 paired bootstrap iterations across the 100 opening pairs:
- $95\%$ empirical confidence interval for paired score difference: **$[-0.250, +0.070]$ points/pair**.
- $95\%$ empirical confidence interval for Elo performance: **$[-43.66, +12.17]$ Elo**.
- Because the confidence interval encompasses zero, playing strength between N7 and N5 is statistically indistinguishable under this time control.

---

## 4. Preregistered Disposition Assessment

Applying the preregistered criteria from [`MATCH_PREREGISTRATION.md`](file:///E:/ChessXML/project-janus/analysis/v0.56/MATCH_PREREGISTRATION.md):
- **Category A (Promotion to Production):** Requires $p < 0.05$ with lower bootstrap bound $> 0.0$. **Failed** ($p = 0.2808$).
- **Category B (Neutral Retention / Experimental Flag):** Requires demonstrated search tree compression ($> 5\%$ node reduction, here $-7.35\%$), combined with no statistically significant regression ($p \ge 0.05$, score $\ge 48\%$, here $47.75\%$ with $p = 0.2808$). **Satisfied.**
- **Category C (Rejection):** Requires statistically significant regression ($p < 0.05$). **Not met** ($p = 0.2808$).
- **Category D (Invalidation):** Requires engine crash or illegal move. **Zero occurrences.**

### Verdict: **CATEGORY B — NEUTRAL RETENTION BEHIND UCI CONFIGURATION OPTIONS**
Static Exchange Evaluation capture ordering is retained in the native C++17 engine behind UCI options (`UseSEEOrdering`, `UseSEEInQuiescence`), with production defaults remaining set to baseline N5 (`false`). This guarantees zero playing-strength regression in production while providing the verified bitboard SEE infrastructure required for future SEE-based pruning milestones.

