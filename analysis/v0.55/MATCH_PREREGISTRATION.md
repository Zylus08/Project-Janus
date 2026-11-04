# Project Janus v0.55 — Preregistered Playing-Strength Match Protocol

**Milestone:** v0.55  
**Date:** 2026-11-05  
**Auditor / Experimental Design Lead:** Principal Chess Engine Research Architect & Experimental Statistician  
**Repository:** `E:\ChessXML\project-janus`  
**Branch:** `v0.3-benchmark-harness`  
**Binary Executable:** `analysis/v0.55/native/janus_native_engine.exe` (SHA256: `f3a54517c2704cfc73c1d8e3b9b50c634f52e1cead2604b13cc942ceff708998`)  
**Opening Suite:** `analysis/v0.55/corpus/independent_openings_v055.json` (SHA256: `8c98c1f07aac802acdc3883b031c16a4b1bad8b0c2edd4f68d4117acd60c40a3`)  

---

## 1. Experimental Protocols Overview

Two independent, preregistered head-to-head matches are formulated:

$$\begin{array}{|l|l|l|l|l|}
\hline
\textbf{Match ID} & \textbf{Experiment Type} & \textbf{Candidate Configuration} & \textbf{Baseline Configuration} & \textbf{Independent Variable} \\
\hline
\mathbf{Exp \ A} & \text{Primary PVS Promotion} & F_{11} \text{ (N6: K=1, H=1, PVS=1)} & F_{10} \text{ (N5: K=1, H=1, PVS=0)} & \text{PVS Activation} \\
\mathbf{Exp \ B} & \text{Independent Replication} & F_{10} \text{ (N5: K=1, H=1, PVS=0)} & F_{00} \text{ (N3: K=0, H=0, PVS=0)} & \text{Killer + History Move Ordering} \\
\hline
\end{array}$$

---

## 2. Invariant Match Controls (Both Experiments)

- **Total Pair Count ($N$):** Exactly 100 opening pairs (200 total games per match).
- **Opening Corpus:** `independent_openings_v055.json`, guaranteed 0% overlap with historical suites.
- **Color Reversal Scheme:**
  - Game 1 of Pair $i$: Candidate plays White, Baseline plays Black.
  - Game 2 of Pair $i$: Candidate plays Black, Baseline plays White.
- **Time Control:** Fischer 3.0s base time + 100ms increment per move (equal for White and Black).
- **Transposition Table:** 16 MB per engine instance, cleared completely before every game via `ucinewgame`.
- **Worker Concurrency:** 8 independent parallel worker processes pinned to isolated UCI instances.
- **Adjudication Standard:** FIDE-compliant referee enforcement via `python-chess`:
  - Checkmate (Article 1.2)
  - Stalemate (Article 5.2.1)
  - Threefold Repetition Claim (Article 9.2)
  - Fivefold Repetition Automatic Draw (Article 9.6.1)
  - 50-Move Rule Claim (Article 9.3)
  - 75-Move Rule Automatic Draw (Article 9.6.2)
  - Insufficient Material (Article 5.2.2)
- **Safety Limit Horizon:** 300 plies (150 full moves). If triggered, explicitly recorded as `safety_limit_300_plies` and never mislabeled as a FIDE draw.
- **Crash & Timeout Policy:**
  - Engine process crash = immediate game forfeiture for crashing engine.
  - Clock timeout with non-zero allocation = game forfeiture on time.

---

## 3. Statistical Analysis & Decision Rules

### 3.1 Primary Unit of Analysis
The fundamental sampling unit is the **opening pair** ($i \in [1, 100]$):
$$d_i = \text{score}_{\text{cand}, i} - \text{score}_{\text{base}, i} \in \{-1.0, -0.5, 0.0, +0.5, +1.0\}$$
where $\text{score}_i \in [0.0, 2.0]$.

### 3.2 Hypothesis Testing & Confidence Intervals
- **Paired Student’s t-Test:**
  $$\bar{d} = \frac{1}{N}\sum_{i=1}^N d_i, \quad s_d = \sqrt{\frac{1}{N-1}\sum_{i=1}^N (d_i - \bar{d})^2}, \quad t = \frac{\bar{d}}{s_d / \sqrt{N}}, \quad df = 99$$
  Two-sided $p$-value computed via the regularized incomplete beta function.
- **Non-Parametric Bootstrap:** 10,000 resamples with replacement of opening pairs. Report 2.5th and 97.5th percentiles of $\bar{d}^*$ and empirical Elo delta:
  $$\text{Elo}_\Delta = -400 \log_{10}\left(\frac{1 - S}{S}\right), \quad S = \frac{\bar{d} + 2.0}{4.0}$$
- **Fixed Sample Size Policy:** Exactly 100 pairs (200 games). No interim looks, no early stopping, no selective exclusions, no post-hoc extensions.

### 3.3 Acceptance Criteria

#### Experiment A (Primary PVS Promotion: N6 vs N5)
To authorize Category A promotion of N6 (`UsePVS=true`):
1. Candidate $F_{11}$ must achieve $\text{score} > 100.0$ points ($>50.0\%$).
2. Two-sided paired Student-t $p < 0.05$.
3. Bootstrap 95% confidence interval for Elo strictly bounded above zero ($\text{CI}_{\text{lower}} > 0$).
4. Zero tactical regressions and zero engine crashes.
*If these conditions are not satisfied, Category B (or C/D) will be declared.*

#### Experiment B (Independent Replication: N5 vs N3)
To establish replication of the v0.54 playing-strength claim:
1. $F_{10}$ must demonstrate a positive net score margin over $F_{00}$ on the fresh opening corpus.
2. Report point estimate, paired $p$-value, and 95% bootstrap interval.
3. Compare against the historical $+29.6$ Elo estimate.
*Experiment B results are reported independently and do not alter Experiment A's preregistered stopping rule or promotion criteria.*

