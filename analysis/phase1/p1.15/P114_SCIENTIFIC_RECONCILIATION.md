# Milestone P1.15: Phase 0 Evidence & Scientific Reconciliation Report
**Milestone:** P1.15  
**Auditor:** Principal Computer Chess Engine Architect & Independent Statistical Auditor  
**Date:** 2026-11-13  
**Status:** RECONCILED & AUDITED

---

## 1. Executive Summary & Audit Scope

Phase 0 performs an exhaustive, independent scientific reconciliation of all Milestone P1.14 empirical evidence prior to any engineering intervention in P1.15.

The reconciliation audited:
1. **Repository and Cryptographic Integrity:** Branch `phase1/classical-janus`, expected parent commit `bcfdecd`, working tree status, and exact SHA-256 binary checksums for X7, X12, and X19.
2. **Tournament Game Reconstruction:** Full parse and verification of all 410 tournament games across 7 PGN archives.
3. **Statistical Governance Review:** Correction of statistical claims regarding "statistically confirmed superiority", rectification of degenerate `[0%, 0%]` intervals on 0-score matches, and accurate historical context for external benchmark results.
4. **Fixed-Depth Benchmark Verification:** Raw verification of the claimed 90–94% node reductions at fixed depth 8 and audit of selective search minimax equivalence.

---

## 2. Cryptographic Checksums & Repository Verification

| Component | Path | SHA-256 Checksum | Verification Status |
|---|---|---|---|
| **Janus Classical X19 Binary** | `analysis/phase1/p1.14/control/janus_classical_x19.exe` | `CBB7785A47E5F9EC64C51C20B8387DE3EFE782F42BDFCEA38008F6450E534629` | **EXACT MATCH** |
| **Janus Classical X7 1T Baseline** | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B` | **EXACT MATCH** |
| **Janus Classical X12 4T Baseline** | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059` | **EXACT MATCH** |
| **Stockfish 4 Executable** | `E:\ChessXML\tools\stockfish_4\stockfish_4.exe` | `1128CAB83386063359947F04155A2210C966080E71176DD385D8BDC3B6C32674` | **EXACT MATCH** |
| **Stockfish 11 Executable** | `E:\ChessXML\tools\stockfish_11\stockfish_11.exe` | `B004C03BD71BB84E8BC1832C580E72A7E883F121E1834EA6DA2802D1575E8048` | **EXACT MATCH** |
| **Stockfish 19 Executable** | `E:\ChessXML\tools\stockfish\stockfish.exe` | `45BC8E4969147DB9C2EB533810637994619BFF0EACC81CCFD9854394901BCBD0` | **EXACT MATCH** |

The repository branch is `phase1/classical-janus` with a clean working tree. Parent commit `bcfdecd` is verified.

---

## 3. Independent Reconstruction of All 410 Tournament Games

All 7 tournament PGN files were independently parsed, verified for move legality, opening pair completeness, termination condition validity, and game score reconciliation:

| Match ID | Opponents & Configuration | Games (Pairs) | Time Control | W - D - L (Score %) | Wilson 95% CI | Paired 95% CI | Rigorous Boundary 95% CI | Pentanomial (WW / WD / DD / LD / LL) |
|---|---|---|---|---|---|---|---|---|
| **Match 1** | X19-S vs X7 Baseline (1T) | 100 (50) | 1.0s + 50ms | 36 - 39 - 25 (**55.50%**) | `[45.74%, 64.86%]` | `[47.92%, 63.08%]` | — | 6 / 14 / 19 / 7 / 4 |
| **Match 2** | X19-S vs X7 Baseline (1T Slow) | 50 (25) | 2.5s + 100ms | 12 - 19 - 19 (**43.00%**) | `[30.27%, 56.73%]` | `[32.60%, 53.40%]` | — | 1 / 5 / 8 / 8 / 3 |
| **Match 3** | X19-P vs X12 Baseline (4T) | 100 (50) | 1.0s + 50ms | 32 - 42 - 26 (**53.00%**) | `[43.29%, 62.49%]` | `[45.00%, 61.00%]` | — | 7 / 12 / 14 / 14 / 3 |
| **Match 4** | X19-S vs Stockfish 4 (1T) | 40 (20) | 1.5s + 50ms | 0 - 4 - 36 (**5.00%**) | `[1.38%, 16.50%]` | `[0.50%, 9.50%]` | — | 0 / 0 / 0 / 4 / 16 |
| **Match 5** | X19-S vs Stockfish 11 (1T) | 40 (20) | 1.5s + 50ms | 0 - 0 - 40 (**0.00%**) | `[0.00%, 8.76%]` | `[0.00%, 0.00%]`* | **`[0.00%, 8.81%]`** | 0 / 0 / 0 / 0 / 20 |
| **Match 6** | X19-S vs Stockfish 19 (1T) | 40 (20) | 1.5s + 50ms | 0 - 0 - 40 (**0.00%**) | `[0.00%, 8.76%]` | `[0.00%, 0.00%]`* | **`[0.00%, 8.81%]`** | 0 / 0 / 0 / 0 / 20 |
| **Match 7** | X19-P vs Stockfish 19 (4T) | 40 (20) | 1.5s + 50ms | 0 - 3 - 37 (**3.75%**) | `[0.87%, 14.73%]` | `[0.00%, 7.76%]` | — | 0 / 0 / 0 / 3 / 17 |

*Note: Denotes degenerate empirical interval; replaced with exact Clopper-Pearson boundary.

### Technical Integrity Audit:
- **Zero Crashes:** 0 process segmentation faults or abrupt terminations.
- **Zero Time Forfeits:** 0 clock expirations on `0000` moves.
- **Zero Illegal Moves:** All 32,840 plies played across 410 games conformed strictly to FIDE rules and legal bitboard move validation.

---

## 4. Scientific Corrections & Statistical Precision

### A. Non-Significance of Internal Baseline Matches
While Candidate X19 produced promising positive point estimates in Match 1 (55.50%, +38.4 Elo) and Match 3 (53.00%, +20.9 Elo), **neither match achieves statistically demonstrated superiority at the standard 95% confidence level**:
- Match 1 paired 95% confidence interval is `[47.92%, 63.08%]`. Because the lower bound is strictly below 50.0%, the null hypothesis of equal playing strength cannot be rejected ($p = 0.15 > 0.05$).
- Match 3 paired 95% confidence interval is `[45.00%, 61.00%]`. The lower bound is substantially below 50.0% ($p = 0.44 > 0.05$).
- Under Project Janus governance, positive sample point estimates must never be reported as "proven superiority" or "decisive victory" without statistical significance.

### B. Rectification of Degenerate [0%, 0%] Confidence Intervals
In Matches 5 and 6 (40 games against Stockfish 11 and Stockfish 19 1T, resulting in 0 points), the P1.14 report computed a paired CI using naive sample variance, outputting `[0.00%, 0.00%]`.
- A confidence interval of `[0%, 0%]` is a degenerate empirical artifact. It falsely implies absolute certainty that Candidate X19 has a 0.0000% probability of ever scoring against the opponent under any circumstance.
- The mathematically proper statistical formulation for zero successes in $n$ trials is the **Clopper-Pearson exact confidence bound** or the **Wilson score interval**.
- For $n = 40$, the 95% upper confidence bound on true playing strength is:
  $$\text{Upper Limit} = 1 - \left(\frac{\alpha}{2}\right)^{1/n} = 1 - (0.025)^{1/40} \approx 8.81\%$$
- The true underlying score parameter is properly bounded in **`[0.00%, 8.81%]`**.

### C. Contextualization of External Reference Results
- **Stockfish 4 (Match 4):** X19 scored 5.00% (4 draws in 40 games). While this exceeds X18's 2.50% (1 win in 40 games), the paired difference (+1 point across 40 games) is well within statistical noise and does not represent an established Elo gain.
- **Stockfish 19 4T (Match 7):** X19-P held 3 draws (3.75%). While defensively encouraging, X19 remains at an overwhelming -563.7 Elo deficit against unrestricted modern NNUE.

---

## 5. Verification of Fixed-Depth Benchmark Ablations

Raw records in `analysis/phase1/p1.14/raw/controlled_ablations_raw.json` were audited:

### 1T Ablation (B0_X7 vs B1_X19):
- **Total Nodes:** Dropped from 2,092,687 to 209,388 (**-89.99% reduction verified**).
- **Total Latency:** Dropped from 1.497s to 0.144s (**10.38× speedup verified**).
- **BF1 (First-Move Cutoff):** Increased from 77.40% to 93.59%.
- **Score Agreement:** Minimax scores matched identically across all 14 test positions.

### 4T Ablation (B0_X12 vs B1_X19):
- **Total Nodes:** Dropped from 1,884,080 to 105,940 (**-94.38% reduction verified**).
- **Total Latency:** Dropped from 1.444s to 0.070s (**20.65× speedup verified**).
- **Score Divergence:** **13 out of 14 positions had different minimax scores between B0_X12 and B1_X19 on 4T** (e.g. `tactical_1`: -35 vs -44 cp; `tactical_2`: 81 vs 45 cp; `queenless_2`: 220 vs 188 cp).

### Selective Search Minimax Equivalence Caution:
The 4T score divergence highlights a critical search theory principle: **in an engine utilizing selective search (LMR, Late Move Pruning, Quiescence SEE pruning, and asynchronous multithreaded TT updates), altering move ordering alters search depth and pruning eligibility.** 
Therefore, fixed-depth score agreement on 1T does not establish mathematical minimax equivalence in full selective tournament conditions. Move ordering changes can alter which tactical lines are explored and pruned.

---

## 6. Scientific Charter for Milestone P1.15

1. **MovePicker Legality & Completeness:** Must be verified through exhaustive legal-move set comparison across thousands of randomized positions before any candidate modifications.
2. **Investigation of Match 2 Slower-Time Regression:** Determine why X19 dropped to 43.0% at 2.5s + 100ms through causal counterfactual diagnostics.
3. **No Retrospective Parameter Fitting:** Thresholds (e.g. $-100 \le \text{SEE} < 0$) must be treated as falsifiable experimental hypotheses.
4. **Promotion Standard:** A successor (Janus Classical X20) will only be qualified if it demonstrates statistically supported superiority against X7/X12 and resolves the slow time control regression.

