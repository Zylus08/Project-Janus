# Project Janus v0.41 — King-Safety K1 Statistical Audit & Equivalence Reassessment

**Milestone:** v0.41 Selective Search Qualification & Effective-Depth Optimization  
**Component:** Candidate K1 (Uncastled King Safety Ablation)  
**Evaluator:** Statistical Validation Lead & Senior Research Engineer  
**Reference Matches:** `analysis/v0.39/match_q0_k0/` vs `analysis/v0.40/match_k1/`  

---

## 1. Audit of Historical Comparison and Reconstructed Metrics

The historical match data between **Candidate K0** (baseline with uncastled king safety) and **Candidate K1** (ablation with uncastled king safety terms disabled) was forensically audited directly from raw PGNs and attempt logs.

### Reconstructed Match Records (50 Games Each vs Stockfish 19 Elo 1320):
| Parameter / Metric | Baseline Reference (K0) | Ablation Candidate (K1) | Observed Delta (K1 - K0) |
|:---|:---:|:---:|:---:|
| **Sample Size ($N$)** | 50 valid games | 50 valid games | 0 |
| **Colour-Reversed Pairs** | 25 complete pairs | 25 complete pairs | 0 |
| **Opening Suite** | `benchmarks/openings.json` | `benchmarks/openings.json` | Identical (Seed 42) |
| **Wins / Draws / Losses** | 21W / 3D / 26L | 22W / 2D / 26L | +1W / -1D / 0L |
| **Total Points** | 22.5 / 50.0 (45.0%) | 23.0 / 50.0 (46.0%) | **+0.5 pts (+1.0%)** |
| **Score as White** | 13.5 / 25.0 (54.0%) | 10.0 / 25.0 (40.0%) | -3.5 pts |
| **Score as Black** | 9.0 / 25.0 (36.0%) | 13.0 / 25.0 (52.0%) | +4.0 pts |
| **Mean Paired Difference ($\bar{\delta}$)** | - | - | **$+0.0200$** |
| **Standard Error ($\text{SE}$)** | - | - | $0.2071$ |
| **Null-Hypothesis t-statistic ($H_0: \delta = 0$)** | - | - | **$t = +0.0966$** |
| **p-value ($H_0: \delta = 0$)** | - | - | **$p = 0.9231$** |

---

## 2. Forensic Critique of the "Statistical Equivalence" Claim

In the v0.40 report, Candidate K1 was classified under the heading *"Statistical Equivalence"* based on the conventional two-tailed p-value of $0.9231$.

### Methodological Deficiencies:
1. **Absence of Evidence is Not Evidence of Absence:** In classical Null-Hypothesis Significance Testing (NHST), a failure to reject $H_0: \delta = 0$ ($p = 0.9231 > 0.05$) simply means the observed sample contains insufficient evidence to declare that K0 and K1 differ. It does **not** establish that their true playing strength is identical.
2. **Confidence Interval Width:** The 10,000-resample paired bootstrap 95% confidence interval on the score delta spans:
   $$\Delta_{\text{score}} \in [-19.0\%, +21.0\%]$$
   Translated to Elo, this confidence interval encompasses an uncertainty band of **$\approx \pm 140\text{ Elo}$**. A confidence band spanning 280 Elo cannot logically support a claim of "equivalence."
3. **Formal Equivalence Testing (TOST Framework):**
   To test for true statistical equivalence, an acceptable equivalence boundary $\Delta_{\text{eq}}$ must be preregistered. Defining a practical equivalence boundary of $\pm 10\%$ score ($\pm 0.20$ points per pair):
   - One-sided test 1 ($H_{01}: \delta \le -0.20$): $t_1 = \frac{+0.0200 - (-0.2000)}{0.2071} = 1.0622$ ($p \approx 0.15$).
   - One-sided test 2 ($H_{02}: \delta \ge +0.20$): $t_2 = \frac{+0.0200 - (+0.2000)}{0.2071} = -0.8690$ ($p \approx 0.20$).
   - **TOST Verdict:** Neither one-sided null hypothesis is rejected at $\alpha = 0.05$. Therefore, **equivalence is mathematically unproven** at $N=50$.

---

## 3. Corrected Terminology and Scientific Classification

- **Historical Phrasing (Retracted):** *"STATISTICAL EQUIVALENCE"*
- **Corrected Terminology:** **STATISTICALLY INCONCLUSIVE / NO DETECTABLE DIFFERENCE AT $N=50$**

---

## 4. Engineering Assessment & Default Policy

1. **Theoretical Calibration:** Uncastled king safety penalizes kings stranded on open central files ($d, e$) in the opening and middlegame while fading gracefully in the endgame (`phase` scaling).
2. **Empirical Status:** The empirical difference of 0.5 points over 50 games ($p = 0.92$) is well within standard sampling noise. Disabling uncastled king safety did not produce an empirical rating gain.
3. **Decision Rule:** In accordance with Section 11 of the v0.41 specification (*"K1 king safety: No default change without justified evidence and an explicit compatibility review"*), the baseline behavior (**K0: uncastled king safety enabled**) is **RETAINED** as the engine default. Candidate K1 remains available via `--disable-uncastled-king-safety` for specialized evaluation.

