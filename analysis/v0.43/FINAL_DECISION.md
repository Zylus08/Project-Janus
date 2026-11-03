# Project Janus v0.43 — Final Production Decision (Phase J)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Date:** 2026-11-03  
**Status:** FINAL & APPROVED  

---

## 1. Primary Decision

### **DECISION B — RFP PROMISING, NOT CONFIRMED**

### Recommendation:
**Retain Reverse Futility Pruning (RFP) strictly as an optional experimental search feature (`--enable-rfp`). DO NOT promote RFP to the default search configuration. Baseline K0 (`enable_rfp = False`) remains the frozen production engine default.**

---

## 2. Decision Rationale & Empirical Justification

1. **Failure to Replicate Strength Improvement:**
   - In v0.42, a 25-pair experiment reported $\bar{\Delta} = +0.58\text{ pts/pair}$ ($+29.0\%$, $p = 0.0053$).
   - In this independent, preregistered 100-pair (400-game) replication, Candidate RFP scored **119.5 / 200 (59.75%)**, while Baseline K0 scored **123.0 / 200 (61.50%)**.
   - **Mean Paired Delta:** $\bar{\Delta} = -0.0350\text{ points/pair}$ ($\mathbf{-1.75\%\text{ per game}}$).
   - **Student's $t$-statistic:** $t = -0.3940$ (df = 99).
   - **One-tailed $p$-value ($H_1: \mu_\Delta > 0$):** $p = 0.6528$ (Completely fails to reject $H_0$).
   - **Bootstrap 95% Confidence Interval:** $[-10.25\%, +7.00\%]$ per game, broadly encompassing zero.

2. **Inconsistency with v0.42 Claims:**
   - The large $+29.0\%$ gain reported in v0.42 failed to replicate when tested across an expanded, representative suite of 100 master openings.
   - The earlier result was an artifact of small-sample variance ($N=25$) on quiet, non-tactical opening lines.

3. **Absence of Correctness Regressions:**
   - RFP did not cause engine crashes, protocol timeouts, or illegal moves (0 illegal moves across 32,826 plies).
   - All 451 automated regression tests pass cleanly.
   - Search tree efficiency was confirmed (-6.25% node reduction across 8,100 moves).
   - Because the implementation is technically sound and achieves selective tree pruning without instability, it does not warrant complete deprecation (Decision C), but rather classification as an optional experimental tool (Decision B).

4. **Defensive Vulnerability Identified:**
   - While RFP matched K0 as White (64.5% vs 64.5%), it suffered a $-3.5\%$ deficit as Black (55.0% vs 58.5%).
   - In sharp gambits (e.g. Evans Gambit, King's Gambit), shallow static evaluations triggered premature cutoffs that pruned critical defensive tactical variations.

---

## 3. Production Deployment Policy

| Parameter | Production Default | Optional Experimental Switch |
|:---|:---:|:---:|
| `enable_rfp` | **False** (K0 Baseline) | `--enable-rfp` |
| `rfp_max_depth` | 2 | `--rfp-max-depth 2` |
| `rfp_margin_per_depth` | 120 | `--rfp-margin 120` |

- The programmatic default in `JanusSearch` and `src/janus/uci.py` remains `enable_rfp = False`.
- RFP remains accessible via `--enable-rfp` for experimental evaluation and parameter tuning.
