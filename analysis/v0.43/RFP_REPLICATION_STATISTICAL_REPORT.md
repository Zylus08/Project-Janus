# Project Janus v0.43 — RFP Replication Statistical Report (Phase G)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Document Type:** Formal Statistical Analysis Report  
**Date:** 2026-11-03  
**Status:** COMPLETE & VERIFIED  

---

## 1. Primary Treatment Effect Analysis (Phase G1 & G2)

We evaluated the primary treatment effect across all $N = 100$ colour-reversed opening pairs (400 games total against Stockfish 19 Elo 1320).

For each pair $i \in [1, 100]$:
$$\Delta_i = S_{\text{RFP}, i} - S_{\text{K0}, i}$$

### Primary Parametric Statistical Summary

| Metric | Observed Value | Interpretation |
|:---|:---:|:---|
| **Sample Size ($N$)** | 100 opening pairs | 400 total games (200 K0, 200 RFP) |
| **K0 Total Points** | 123.0 / 200.0 (61.50%) | Baseline performance |
| **RFP Total Points** | 119.5 / 200.0 (59.75%) | Candidate performance |
| **Net Score Delta** | -3.5 points | RFP scored 3.5 points fewer than K0 |
| **Mean Paired Delta ($\bar{\Delta}$)** | **-0.0350 points / pair** | **-1.75% per game** |
| **Median Paired Delta** | **0.0000 points / pair** | Exact parity at the median |
| **Standard Deviation ($s$)** | 0.8884 | Spread of paired differences |
| **Standard Error ($\text{SE}$)** | **0.0888** | Precision of the sample mean |
| **Degrees of Freedom** | 99 | $N - 1$ |
| **Paired $t$-statistic** | **-0.3940** | $t = \bar{\Delta} / \text{SE}$ |
| **One-tailed $p$-value ($H_1: \mu_\Delta > 0$)** | **0.652763** | **FAILS TO REJECT $H_0$** ($p \gg 0.05$) |
| **Two-tailed $p$-value ($H_0: \mu_\Delta = 0$)** | **0.694474** | No statistically significant difference |

---

## 2. Bootstrap Confidence Interval (Phase G3)

A non-parametric bootstrap was performed using **10,000 resamples** of complete opening pairs:
- **Resampling Unit:** Complete opening pair $(\Delta_i)$, preserving intra-pair correlation.
- **RNG Seed:** 42 (deterministic).
- **Bootstrap Mean Delta:** $-0.0351$ points/pair.
- **95% Percentile Confidence Interval (points/pair):**
  $$\bar{\Delta} \in [-\mathbf{0.2050}, +\mathbf{0.1400}]\text{ points/pair}$$
- **95% Percentile Confidence Interval (% per game):**
  $$\Delta_{\text{score}} \in [-\mathbf{10.25\%}, +\mathbf{7.00\%}]\text{ per game}$$

### Scientific Interpretation
1. The 95% bootstrap confidence interval spans from $-10.25\%$ to $+7.00\%$, **broadly overlapping zero**.
2. The massive $+29.0\%$ gain reported in v0.42 ($[+9.0\%, +49.0\%]$) is **wholly rejected** by this 100-pair replication. The previous estimate was an artifact of a small 25-pair sample biased toward quiet positional positions.
3. Under an expanded 100-opening master distribution, RFP does not provide a statistically detectable strength improvement over Baseline K0 ($p = 0.6528$).

---

## 3. Pair-Level Outcome Distribution (Phase G4)

| Category | Pair Count | Percentage | Description |
|:---|:---:|:---:|:---|
| **RFP Outperformed K0 ($\Delta_i > 0$)** | 30 | 30.0% | RFP gained points over K0 |
| **Tied Pairs ($\Delta_i = 0$)** | 37 | 37.0% | Both engines achieved identical pair scores |
| **K0 Outperformed RFP ($\Delta_i < 0$)** | 33 | 33.0% | K0 gained points over RFP |
| **Total** | **100** | **100.0%** | Full replication cohort |

The distribution of pair outcomes is nearly symmetrical around zero, with K0 outperforming RFP in slightly more pairs (33 vs 30) and 37 pairs resulting in exact parity.

---

## 4. Colour and Positional Breakdown

### Performance by Colour

| Metric | Baseline K0 | Candidate RFP | Delta (RFP - K0) |
|:---|:---:|:---:|:---:|
| **White Games** | 100 | 100 | 0 |
| White Score | 64.5 / 100 (64.5%) | 64.5 / 100 (64.5%) | **0.0 pts (0.0%)** |
| **Black Games** | 100 | 100 | 0 |
| Black Score | 58.5 / 100 (58.5%) | 55.0 / 100 (55.0%) | **-3.5 pts (-3.5%)** |

### Opening Type Analysis
- **Quiet / Positional Openings (RFP Superior):**
  - Pair 15 (English Anglo-Indian): $+2.0$ points
  - Pair 42 (Catalan Opening): $+2.0$ points
  - Pair 43 (King's Indian Classical): $+1.5$ points
  - Pair 74 (Pirc Classical): $+1.5$ points
  - Pair 82 (Slav Exchange): $+1.5$ points
  In closed, slow maneuvering positions, RFP safely prunes quiescent nodes, achieving depth gains without tactical penalty.
- **Sharp / Tactical Gambits (K0 Superior):**
  - Pair 54 (Evans Gambit): $-2.0$ points (K0 swept 2.0, RFP scored 0.0)
  - Pair 3 (French Defense): $-2.0$ points
  - Pair 99 (Nimzo-Larsen Modern): $-2.0$ points
  - Pair 100 (English Mikenas-Flohr): $-2.0$ points
  - Pair 76 (Tarrasch Defense): $-1.5$ points
  In sharp, sacrificial gambits, shallow static evaluation fail-highs caused RFP to prune critical tactical lines prematurely, leading to decisive blunders.

---

## 5. Elo Rating Interpretation (Phase G5)

$$\text{Elo} = 400 \times \log_{10}\!\left(\frac{p}{1 - p}\right)$$

| Engine Arm | Win Rate vs SF 1320 | Estimated Elo vs SF 1320 | Standard Error ($\approx$) |
|:---|:---:|:---:|:---:|
| **Baseline K0** | 61.50% | **+81.4 Elo** | $\pm 35\text{ Elo}$ |
| **Candidate RFP** | 59.75% | **+68.6 Elo** | $\pm 35\text{ Elo}$ |
| **Empirical Delta** | **-1.75%** | **-12.7 Elo** | $\mathbf{\pm 49\text{ Elo}}$ |

The observed rating difference of $-12.7\text{ Elo}$ is well within standard sampling error ($\pm 49\text{ Elo}$) and cannot be distinguished from parity.

---

## 6. Phase G Conclusion

The preregistered null hypothesis ($H_0: \mu_\Delta \le 0$) **cannot be rejected** ($t = -0.3940$, $p = 0.6528$). 

Candidate RFP does **not** provide a reproducible playing strength gain over Baseline K0 in a 100-pair matched ablation.

