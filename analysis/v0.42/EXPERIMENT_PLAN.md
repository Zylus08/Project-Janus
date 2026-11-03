# Project Janus v0.42 — Experiment Plan (Phase A)

**Milestone:** v0.42 — RFP Replication, Rule-Accurate Draw Semantics & Strength Attribution  
**Document Type:** Preregistered Experiment Plan  
**Date:** 2026-11-02  
**Status:** FROZEN — do not modify after Phase F match commencement

---

## 1. Primary Research Question

> Does enabling Reverse Futility Pruning (RFP) cause a measurable playing-strength gain in a **direct, paired, ablation** experiment comparing K0 (RFP off) versus RFP (RFP on) — controlling for all other search and evaluation parameters?

The v0.41 qualification match compared RFP against Stockfish 19 Elo 1320 in isolation. It did not directly compare K0 and RFP head-to-head on the same set of opening pairs in the same session. The v0.42 ablation provides that direct causal attribution.

---

## 2. Null Hypothesis

**H₀:** The mean paired-score difference between the RFP configuration and the K0 configuration (Δ = score_RFP − score_K0 per opening pair) is zero.

$$H_0: \mu_\Delta = 0$$

**H₁:** The mean paired-score difference is positive (RFP is stronger).

$$H_1: \mu_\Delta > 0$$

**Test type:** One-tailed paired t-test (directional).  
**Significance threshold:** α = 0.05.

---

## 3. Experimental Design

### 3.1 Configurations

| Parameter | K0 (Control) | RFP (Treatment) |
|:---|:---|:---|
| `enable_rfp` | False | True |
| `rfp_max_depth` | — | 2 |
| `rfp_margin_per_depth` | — | 120 |
| `enable_pvs` | True | True |
| `enable_aspiration` | True | True |
| `enable_lmr` | True | True |
| `enable_nmp` | True | True |
| `enable_history` | True | True |
| `enable_killers` | True | True |
| `eval_all` | True | True |
| `time_policy` | arm_c | arm_c |
| `Stockfish Elo` | 1320 | 1320 |
| `Threads` | 1 | 1 |
| `Hash` | 64 | 64 |

Both configurations are identical except for `enable_rfp`.

### 3.2 Opening Selection

- **Source:** `benchmarks/openings.json` (50 positions, SHA-256 recorded at experiment start)
- **Seed:** 42 (deterministic, matches v0.41 seed)
- **Pairs:** 25 opening pairs (50 games per configuration = 100 games total)
- **Colour balance:** Janus plays White and Black in each pair

The 25 opening pairs used for K0 **must be identical** to the 25 pairs used for RFP (same seed, same harness).

### 3.3 Time Control

- Base: 3000 ms  
- Increment: 100 ms (Fischer)  
- Policy: arm_c (adaptive, complexity-scaling)

### 3.4 Primary Outcome Measure

For each opening pair i (i = 1…25):

$$\Delta_i = \text{score\_RFP}_{i,W} + \text{score\_RFP}_{i,B} - \text{score\_K0}_{i,W} - \text{score\_K0}_{i,B}$$

where each score ∈ {0, 0.5, 1.0}.

**This requires K0 and RFP to play the SAME 25 opening pairs**, which is guaranteed by using `seed=42` in both calls to `load_openings(count=25)`.

---

## 4. Statistical Analysis Plan

### 4.1 Primary Analysis

- **Test:** One-tailed paired Student's t-test on Δ_i (n=25 pairs)
- **Effect measure:** Mean pair score difference $\bar\Delta$
- **Estimate of variance:** Sample standard deviation of Δ_i
- **SE:** $SE = s / \sqrt{n}$
- **Reject H₀ if:** t > t_{24, 0.05} = 1.711 (one-tailed)

### 4.2 Secondary Analysis

- 10,000-sample bootstrap 95% CI on mean Δ (resampling pairs, not individual games)
- Independent W/D/L, score %, and Elo estimate for each configuration separately (against Stockfish 1320)

### 4.3 Elo Formula

$$\text{Elo estimate (vs SF 1320)} = 400 \cdot \log_{10}\!\left(\frac{p}{1-p}\right)$$

where p is the score percentage against Stockfish 1320. This is an independent estimate, not a direct comparison.

---

## 5. Infrastructure

- **Match harness:** `scripts/match_v040_experiments.py`
- **K0 output:** `analysis/v0.42/match_k0/`
- **RFP output:** `analysis/v0.42/match_rfp/`
- **Games per config:** 50 (25 pairs × 2 games/pair)
- **Stockfish binary:** `E:\ChessXML\tools\stockfish\stockfish.exe`  
  SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`

---

## 6. Acceptance Gates for Phase F

| Gate | Criterion | Threshold |
|:---|:---|:---|
| F1 | All 50 K0 games completed | 50/50 |
| F2 | All 50 RFP games completed | 50/50 |
| F3 | Same 25 opening pairs used (seed=42 verified) | Deterministic |
| F4 | Zero illegal moves in either match PGN | 0 illegal |
| F5 | Zero negative clock readings | 0 negative |
| F6 | One-tailed p-value for Δ | < 0.05 (or INCONCLUSIVE if ≥ 0.05) |

---

## 7. Openings Manifest (Frozen at Plan Registration)

- **File:** `benchmarks/openings.json`
- **Count:** 50 positions
- **SHA-256:** (computed at experiment start and recorded in Phase F preregistration)
- **Seed:** 42 → 25 pairs selected deterministically

---

## 8. Decision Framework

| Outcome | Decision |
|:---|:---|
| H₀ rejected (p < 0.05, Δ > 0) | Promote RFP to default (`enable_rfp=True`) |
| H₀ not rejected (p ≥ 0.05) | Keep RFP as optional (`enable_rfp=False` default); report INCONCLUSIVE |
| Δ < 0 (negative) | Investigate regression; defer decision |

---

## 9. Repository State at Plan Registration

- **Branch:** v0.3-benchmark-harness  
- **HEAD commit:** 1d509d0  
- **Working tree:** Clean  
- **Test suite:** 444 tests passing  

