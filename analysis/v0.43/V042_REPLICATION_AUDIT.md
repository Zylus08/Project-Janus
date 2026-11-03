# Project Janus v0.43 — Audit of v0.42 Preregistration and Sample Size (Phase B)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Auditor:** Statistical Validation Lead  
**Date:** 2026-11-03  
**Status:** COMPLETE & AUDITED  

---

## 1. Audit of Original Preregistration (Phase B1)

We inspected the v0.42 preregistration document:
[`analysis/v0.42/RFP_DIRECT_ABLATION_PREREGISTRATION.md`](file:///e:/ChessXML/project-janus/analysis/v0.42/RFP_DIRECT_ABLATION_PREREGISTRATION.md)

### Preregistered Specifications
- **Target Comparison:** Baseline K0 vs Candidate RFP (`rfp_max_depth=2`, `rfp_margin_per_depth=120`).
- **Primary Hypothesis:**
  $$H_0: \mu_\Delta \le 0 \quad \text{vs} \quad H_1: \mu_\Delta > 0$$
- **Primary Statistical Test:** One-tailed paired Student's $t$-test on $\Delta_i = \text{score}_{\text{RFP}, i} - \text{score}_{\text{K0}, i}$ across colour-reversed opening pairs.
- **Significance Level:** $\alpha = 0.05$.
- **Planned Confidence Interval:** 10,000-resample pair-level bootstrap 95% CI on mean paired delta $\bar{\Delta}$.
- **Exclusion Policy:** Objective protocol/pgn failures only; zero exclusions permitted for unfavorable gameplay.
- **Interim Analysis:** None permitted.

---

## 2. Sample-Size Deviation Assessment (Phase B2)

The execution guidelines for v0.42 had suggested a 100-pair (200-game) design. However, the recorded v0.42 experiment executed 25 pairs (50 games per engine, 100 games total).

### Classification of Deviation
**`PREPLANNED and RESOURCE-LIMITED`**

### Evidence & Rationale
1. **Preregistration Timing:** In Section 2 of `analysis/v0.42/RFP_DIRECT_ABLATION_PREREGISTRATION.md`, the sample size of 25 pairs was documented *prior* to match verification.
2. **Opening Suite Boundary:** The benchmark file `benchmarks/openings.json` contains exactly 50 opening positions. A balanced colour-reversed pair requires 1 opening position (played as White and as Black). Hence, exactly $50 / 2 = 25$ unique pairs exist without reusing openings.
3. **Absence of Post-Hoc Peeking:** The experiment was not stopped early due to sequential p-value monitoring. The sample size was constrained by the available un-reused opening pool.
4. **Statistical Implications:** While $N=25$ pairs provided adequate power to reject $H_0$ ($t = 2.7682, p = 0.0053$), the confidence interval remained relatively wide ($[+9.0\%, +49.0\%]$ per game). A larger 100-pair replication is necessary to narrow the estimate and confirm reproducibility across an expanded opening distribution.

---

## 3. Independent Re-computation of v0.42 Results (Phase B3)

We independently recomputed all statistical metrics directly from raw game records:
- Baseline K0: `analysis/v0.39/match_q0_k0/match_results.json`
- Candidate RFP: `analysis/v0.41/match_rfp/match_results.json`

### Raw Pair-by-Pair Scores and Deltas

| Pair | Opening ID | K0 Score | RFP Score | Delta ($\Delta_i$) |
|:---:|:---|:---:|:---:|:---:|
| 1 | `scotch_game` | 1.0 | 1.5 | +0.5 |
| 2 | `italian_two_knights` | 0.5 | 2.0 | +1.5 |
| 3 | `b3_e5_nimzo_larsen` | 1.0 | 0.5 | -0.5 |
| 4 | `ruy_lopez_berlin` | 0.5 | 2.0 | +1.5 |
| 5 | `queen_pawn_d5` | 1.0 | 2.0 | +1.0 |
| 6 | `sicilian_dragon` | 2.0 | 2.0 | 0.0 |
| 7 | `french_winawer` | 2.0 | 1.5 | -0.5 |
| 8 | `caro_kann_advance` | 2.0 | 2.0 | 0.0 |
| 9 | `english_four_knights` | 1.0 | 1.5 | +0.5 |
| 10 | `modern_defense` | 1.0 | 1.5 | +0.5 |
| 11 | `qgd_orthodox` | 1.0 | 1.0 | 0.0 |
| 12 | `sicilian_najdorf` | 2.0 | 0.5 | -1.5 |
| 13 | `king_indian_classical` | 1.0 | 1.0 | 0.0 |
| 14 | `nimzo_indian_rubinstein`| 1.5 | 0.0 | -1.5 |
| 15 | `catalan_open` | 0.0 | 2.0 | +2.0 |
| 16 | `grunfeld_exchange` | 1.0 | 2.0 | +1.0 |
| 17 | `slav_defense_main` | 0.0 | 0.5 | +0.5 |
| 18 | `benoni_modern` | 0.0 | 1.0 | +1.0 |
| 19 | `vienna_game` | 2.0 | 1.5 | -0.5 |
| 20 | `alekhine_four_pawns` | 0.0 | 2.0 | +2.0 |
| 21 | `dutch_leningrad` | 0.0 | 2.0 | +2.0 |
| 22 | `scandinavian_main` | 1.0 | 1.0 | 0.0 |
| 23 | `pirc_austrian` | 0.0 | 2.0 | +2.0 |
| 24 | `bird_opening` | 1.0 | 2.0 | +1.0 |
| 25 | `reti_opening` | 0.0 | 2.0 | +2.0 |

### Statistical Metrics Verification

| Metric | v0.42 Stated Value | Recomputed Raw Value | Status |
|:---|:---:|:---:|:---:|
| K0 Total Score | 22.5 / 50.0 (45.0%) | 22.5 / 50.0 (45.0%) | ✓ Exact |
| RFP Total Score | 37.0 / 50.0 (74.0%) | 37.0 / 50.0 (74.0%) | ✓ Exact |
| Mean Paired Delta ($\bar{\Delta}$) | +0.5800 | +0.5800 | ✓ Exact |
| Standard Error ($\text{SE}$) | 0.2095 | 0.2095 | ✓ Exact |
| $t$-statistic (df = 24) | 2.7682 | 2.7682 | ✓ Exact |
| One-tailed $p$-value | 0.005345 | 0.005345 | ✓ Exact |
| Two-tailed $p$-value | 0.010690 | 0.010690 | ✓ Exact |
| 10,000-resample Bootstrap 95% CI | [+0.1800, +0.9800] pts/pair | [+0.1800, +0.9800] pts/pair | ✓ Exact |

### Narrative Reporting Discrepancy Discovered
Our forensic audit detected a narrative categorization error in Section 3 of `analysis/v0.42/RFP_DIRECT_ABLATION_RESULTS.md`:
- **Documented in v0.42 Narrative:** 17 pairs RFP > K0, 7 pairs tied, 1 pair K0 > RFP.
- **Actual Raw Pair Distribution:**
  - Pairs where RFP strictly outperformed K0 ($\Delta_i > 0$): **15 pairs** (60.0%)
  - Pairs where scores were identical ($\Delta_i = 0$): **5 pairs** (20.0%)
  - Pairs where K0 strictly outperformed RFP ($\Delta_i < 0$): **5 pairs** (20.0%) (Pairs 3, 7, 12, 14, 19)

**Significance of Finding:** The raw mathematical metrics ($\bar{\Delta} = +0.58$, $t = 2.7682$, $p = 0.0053$) are 100% verified and unchanged. However, recognizing that K0 outperformed RFP in 5 pairs (not 1) highlights that RFP does entail selective pruning risk in specific sharp openings (`b3_e5`, `french_winawer`, `sicilian_najdorf`, `nimzo_indian_rubinstein`, `vienna_game`). This finding strengthens the justification for an independent replication.

