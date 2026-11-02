# Project Janus v0.42 — RFP Direct Ablation Preregistration (Phase F)

**Milestone:** v0.42  
**Document Type:** Preregistered Experimental Protocol  
**Date:** 2026-11-03  
**Status:** PREREGISTERED & FROZEN  

---

## 1. Research Question & Causal Attribution Hypothesis

Does enabling Reverse Futility Pruning (RFP) cause a statistically significant and reproducible playing-strength gain when compared directly in a paired, colour-balanced ablation against Baseline K0 under identical evaluation, time-allocation, and opponent conditions?

### Hypotheses
- **Null Hypothesis ($H_0$):** The mean paired score difference between Candidate RFP and Baseline K0 on identical colour-reversed opening pairs is zero or negative:
  $$H_0: \mu_\Delta \le 0$$
- **Alternative Hypothesis ($H_1$):** Candidate RFP outperforms Baseline K0:
  $$H_1: \mu_\Delta > 0$$

- **Significance Level:** $\alpha = 0.05$ (one-tailed directional t-test).

---

## 2. Sample Size Specification & Opening Constraints

### Opening Suite Geometry
- **Suite:** `benchmarks/openings.json`
- **Total Openings:** 50 opening positions.
- **Maximum Unique Pairs Without Re-use:** 25 pairs ($25 \times 2 = 50$ games).
- **Design Adaptation:** A nominal 200-game experiment would necessitate cycling the same 50 positions 4 times, violating opening independence and introducing autocorrelation across cycles.
- **Preregistered Sample Size:** $N = 50$ games (25 unique, balanced colour-reversed pairs), directly matching the benchmarked protocols of v0.39, v0.40, and v0.41.

---

## 3. Experimental Controls & Invariant Parameters

| Parameter | Baseline (K0) | Candidate (RFP) |
|:---|:---|:---|
| Engine Binary / Module | `janus.uci` | `janus.uci` |
| Evaluation Configuration | Full tapered eval (`--eval-all`) | Full tapered eval (`--eval-all`) |
| Uncastled King Safety | Enabled (K0 baseline) | Enabled (K0 baseline) |
| Move Ordering Heuristics | MVV/LVA, Killers, History | MVV/LVA, Killers, History |
| Search Enhancements | PVS, Aspiration, LMR, NMP | PVS, Aspiration, LMR, NMP |
| **Reverse Futility Pruning** | **Disabled (`--enable-rfp` absent)** | **Enabled (`--enable-rfp`)** |
| RFP Max Depth | N/A | 2 plies |
| RFP Margin | N/A | 120 cp / ply |
| Time Management | `arm_c` (adaptive Fischer) | `arm_c` (adaptive Fischer) |
| Time Control | 3000 ms initial + 100 ms Fischer increment | 3000 ms initial + 100 ms Fischer increment |
| Opponent | Stockfish 19 (`UCI_Elo=1320`, 1 thread, 64MB) | Stockfish 19 (`UCI_Elo=1320`, 1 thread, 64MB) |
| Opening Selection Seed | Seed 42 | Seed 42 |

---

## 4. Primary and Secondary Endpoints

### 4.1 Primary Endpoint
The mean paired-score difference per opening pair:
$$\Delta_i = \text{score}_{\text{RFP}, i} - \text{score}_{\text{K0}, i}$$
where $\text{score}_i \in \{0.0, 0.5, 1.0, 1.5, 2.0\}$ is the total points scored across the White and Black game of opening pair $i \in [1, 25]$.

### 4.2 Statistical Tests
1. **Paired Student's t-test:** $t = \frac{\bar{\Delta}}{\text{SE}(\Delta)}$, with df = 24. Rejection threshold: $t > 1.711$ ($p < 0.05$).
2. **Pair-Resampling Bootstrap:** 10,000 bootstrap resamples on the pair delta vector $\vec{\Delta}$. Success criterion: 95% CI lower bound strictly greater than 0.

### 4.3 Secondary Endpoints
- Individual win rate and Elo estimation against Stockfish 19 Elo 1320:
  $$\text{Elo} = 400 \times \log_{10}\!\left(\frac{p}{1-p}\right)$$
- Search telemetry: Node reduction %, average depth reached, timeout frequency.

---

## 5. Frozen Provenance
- Repository: `E:\ChessXML\project-janus`
- Git Branch: `v0.3-benchmark-harness`
- Starting Commit: `1d509d0`
- Openings Hash (SHA-256): Frozen in `analysis/v0.42/v041_reference_manifest.json`
