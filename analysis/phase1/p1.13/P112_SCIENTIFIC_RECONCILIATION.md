# P1.12 Forensic Reconciliation & Scientific Correction Audit
**Project Janus — Phase 1, Milestone P1.13**
**Author:** Principal Computer Chess Engine Architect & Independent Statistical Auditor
**Repository:** `E:\ChessXML\project-janus-phase1`
**Parent Commit:** `5b44c3f`
**Date:** November 13, 2026

---

## 1. Executive Summary & Forensic Findings

Milestone P1.13 begins with a strict forensic audit of the experimental records and conclusions established in Milestone P1.12 (`5b44c3f`). The audit investigated two distinct areas:
1. **Dataset Integrity & Game Count Discrepancy:** The discrepancy between the 370 games reported in the abbreviated prompt summary and the 410 games reported in `docs/phase1/p1.12_report.md`.
2. **Scientific & Statistical Overclaims:** The identification and formal correction of unsubstantiated assertions made in earlier milestone reports regarding equivalence proofs, zero-score Elo calculations, arbitrary neural/classical gap splits, and move disagreement classifications.

### 1.1 Resolution of the 370 vs. 410 Game Count Mystery
A complete cryptographic and header audit of all PGN archives stored on disk under `analysis/phase1/p1.12/pgn/` was executed using python-chess. The results are summarized below:

| Match ID | PGN Archive Name | Pairing | Hardware Config | Time Control | Audited Games | Recorded Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Match 1** | `x17_1t_vs_x7_1t.pgn` | X17 vs X7 | 1 Thread, 64 MB | 1.0s + 50ms | **100** | +33 =37 -30 (51.5%) |
| **Match 2** | `x17_1t_vs_x7_1t_slow.pgn` | X17 vs X7 | 1 Thread, 64 MB | 2.5s + 100ms | **50** | +15 =20 -15 (50.0%) |
| **Match 3** | `x17_4t_vs_x12_4t.pgn` | X17 vs X12 | 4 Threads, 256 MB | 1.0s + 50ms | **100** | +33 =34 -33 (50.0%) |
| **Match 4** | `x17_1t_vs_sf11_1t.pgn` | X17 vs SF 11 | 1 Thread, 64 MB | 1.0s + 50ms | **40** | +0 =0 -40 (0.0%) |
| **Match 5** | `x17_4t_vs_sf11_4t.pgn` | X17 vs SF 11 | 4 Threads, 256 MB | 1.0s + 50ms | **40** | +0 =0 -40 (0.0%) |
| **Match 6** | `x17_1t_vs_sf19_1t.pgn` | X17 vs SF 19 | 1 Thread, 64 MB | 1.0s + 50ms | **40** | +0 =4 -36 (5.0%) |
| **Match 7** | `x17_4t_vs_sf19_4t.pgn` | X17 vs SF 19 | 4 Threads, 256 MB | 1.0s + 50ms | **40** | +0 =0 -40 (0.0%) |
| **TOTAL** | **7 Archives** | — | — | — | **410** | **+81 =95 -234 (31.3%)** |

**Forensic Conclusion:**
- The report `docs/phase1/p1.12_report.md` correctly recorded **410 games** across **7 tournaments** (250 internal games + 160 external games: 80 vs Stockfish 11 and 80 vs Stockfish 19).
- The summary prompt listed:
  - Internal: 100 + 50 + 100 = 250
  - External: SF11 = 0/80 (sum of Matches 4 & 5)
  - External: SF19 = 2/40 (Match 6 alone)
  - Sum: $250 + 80 + 40 = 370$ games.
- The summary line in the prompt inadvertently omitted **Match 7** (`x17_4t_vs_sf19_4t.pgn`, 40 games, 0/40). When Match 7 is included ($370 + 40$), the total reaches exactly **410 games**.
- No PGN archive is missing, corrupted, or duplicated. All 410 games are fully intact, syntactically verified, and cryptographically accounted for.

---

## 2. Mandatory Scientific Corrections

In accordance with Phase 0 governing requirements, the following five methodological and theoretical claims from P1.12 are explicitly retracted and corrected:

### 2.1 Refutation of "Proven Equivalence"
- **P1.12 Claim:** Because Match 1 ($51.5\%$, $p = 0.76$) and Match 3 ($50.0\%$, $p = 1.00$) failed to achieve statistical significance against $H_0$, X17 was claimed to be "proven equivalent" to X7 and X12.
- **Scientific Correction:** In statistical testing, failure to reject the null hypothesis ($p > 0.05$) does **not** prove the null hypothesis. Equivalence can only be asserted if a Two One-Sided Tests (TOST) procedure is conducted with a preregistered equivalence margin $[-\Delta, +\Delta]$.
- **Quantitative Audit:**
  - In Match 1 ($N=100$), the 95% Wilson confidence interval is $[41.83\%, 61.06\%]$, corresponding to an Elo interval of $[-57.3, +78.1]\text{ Elo}$.
  - In Match 2 ($N=50$), the 95% Wilson confidence interval is $[36.64\%, 63.36\%]$, corresponding to $[-95.1, +95.1]\text{ Elo}$.
  - An uncertainty span of over $135\text{ Elo}$ cannot prove equivalence under any rigorous engineering standard. We formally record: *X17 exhibited no statistically significant performance difference compared to X7 or X12 within the resolution of the sample.*

### 2.2 Mathematical Treatment of Zero Scores
- **P1.12 Claim:** Stockfish 11's 80-0 victory over X17 established a "classical headroom ceiling of $\sim 500\text{--}550\text{ Elo}$."
- **Scientific Correction:** When an engine scores $0$ points in $N$ trials ($k=0$), the Maximum Likelihood Estimate (MLE) of the scoring probability is $\hat{p} = 0$, for which the standard logistic Elo difference is $-\infty$:
  $$\Delta\text{Elo} = -400 \log_{10}\left(\frac{1}{\hat{p}} - 1\right) = -\infty$$
  Assigning a finite point estimate of $500\text{--}550\text{ Elo}$ from a zero score is mathematically invalid.
- **Correct Formulation:** A zero score establishes a **one-sided confidence upper bound** on the true underlying scoring probability $p$. Using the exact Clopper-Pearson formulation at $1 - \alpha = 0.95$:
  $$p_{\text{upper}} = 1 - \alpha^{1/N} = 1 - (0.05)^{1/80} \approx 0.0368 \quad (3.68\%)$$
  This translates to a 95% confidence upper bound on Elo:
  $$\Delta\text{Elo} < -400 \log_{10}\left(\frac{1}{0.0368} - 1\right) \approx -567\text{ Elo}$$
  We state strictly: *At 95% confidence, Janus Classical's true scoring probability against Stockfish 11 is less than $3.68\%$ ($\Delta\text{Elo} < -567\text{ Elo}$); no finite point estimate is supported.*

### 2.3 Retraction of Speculative 70/30 Classical vs. Neural Decomposition
- **P1.12 Claim:** "70% of Janus's deficit against Stockfish 19 stems from classical search architecture, while 30% stems from NNUE evaluation."
- **Scientific Correction:** This split was speculative extrapolation. Stockfish 11 (classical) and Stockfish 19 (NNUE) differ across thousands of commits spanning search pruning, history tables, move picking, singular extensions, multi-cut, and evaluation. No controlled toggle isolating search vs. NNUE was run in P1.12. The claim is completely retracted.

### 2.4 Removal of "NNUE Sole Cause" Attribution for Search Differences
- **P1.12 Claim:** Stockfish 19's higher node efficiency and depth progression relative to Janus were attributed solely to NNUE evaluation guide-rails.
- **Scientific Correction:** Stockfish's classical search in Stockfish 11 already displayed deep tactical pruning, multi-history tracking, countermove heuristics, and singular extensions. Search differences cannot be attributed solely to NNUE.

### 2.5 Heuristic Status of Stockfish Depth-14 Ground Truth
- **P1.12 Claim:** Disputed moves were audited against "Stockfish 19 depth 14 ground truth."
- **Scientific Correction:** Stockfish at depth 14 is a heuristic search relying on bounded alpha-beta exploration and evaluation approximations. It is a useful reference engine, not an infallible oracle or mathematical ground truth.

### 2.6 Reclassification of LMR Disagreements
- **P1.12 Claim:** The $38 / 39$ move disagreements caused by LMR where the evaluation difference was $\le 15\text{ cp}$ were classified as "benign".
- **Scientific Correction:** Small score variations in alpha-beta search frequently conceal tactical horizons, king-safety compromises, or zugzwang vulnerabilities. They are formally reclassified as **"reference-supported small-score disagreements"**.

---

## 3. Audited Tournament Data & Pentanomial Breakdown

| Match Description | $N$ | $+ / = / -$ | Score Pct | Wilson 95% CI | Pentanomial $[WW, WD, DD/WL, LD, LL]$ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Match 1 (X17 1T vs X7 1T)** | 100 | +33 =37 -30 | 51.50% | [41.83%, 61.06%] | $[2, 18, 15, 11, 4]$ |
| **Match 2 (X17 1T vs X7 1T Slow)** | 50 | +15 =20 -15 | 50.00% | [36.64%, 63.36%] | $[3, 6, 6, 8, 2]$ |
| **Match 3 (X17 4T vs X12 4T)** | 100 | +33 =34 -33 | 50.00% | [40.38%, 59.62%] | $[5, 10, 18, 14, 3]$ |
| **Match 4 (X17 1T vs SF11 1T)** | 40 | +0 =0 -40 | 0.00% | [0.00%, 8.76%] | $[0, 0, 0, 0, 20]$ |
| **Match 5 (X17 4T vs SF11 4T)** | 40 | +0 =0 -40 | 0.00% | [0.00%, 8.76%] | $[0, 0, 0, 0, 20]$ |
| **Match 6 (X17 1T vs SF19 1T)** | 40 | +0 =4 -36 | 5.00% | [1.38%, 16.50%] | $[0, 0, 0, 4, 16]$ |
| **Match 7 (X17 4T vs SF19 4T)** | 40 | +0 =0 -40 | 0.00% | [0.00%, 8.76%] | $[0, 0, 0, 0, 20]$ |

Forensic reconciliation is complete, verified, and sealed.

