# Reconciliation of v0.44 Opening Stratification — v0.45

**Milestone:** Project Janus v0.45  
**Date:** 2026-11-03  
**Status:** COMPLETE (Gate D Validated)

---

## 1. Executive Summary & Problem Formulation

In the v0.44 milestone report, the following three summary statements appeared:
1. Across all 65 non-Semi-Open opening pairs, RFP outscored K0 by **$+3.0$ points**.
2. When playing Black in Semi-Open openings, RFP underperformed K0 by **$-5.5$ points**.
3. Overall across the 100 opening pairs, RFP underperformed K0 by **$-3.5$ points**.

Summing $+3.0$ and $-5.5$ yields $-2.5$, leaving an apparent $1.0$-point arithmetic discrepancy relative to the observed overall delta of $-3.5$ points.

This audit independently reconstructed the exact game-level and pair-level data from [`analysis/v0.43/match_replication/match_results.json`](file:///E:/ChessXML/project-janus/analysis/v0.43/match_replication/match_results.json) to trace and reconcile this difference.

---

## 2. Mutually Exclusive & Collectively Exhaustive Taxonomy

All 100 opening pairs from the v0.43 replication were partitioned into four non-overlapping families:

| Opening Family | Pairs | White Delta (RFP - K0) | Black Delta (RFP - K0) | Total Family Delta (RFP - K0) |
|---|---:|---:|---:|---:|
| **Open Games & Gambits (1.e4 e5)** | 19 | $+0.5$ | $-1.0$ | $-0.5$ |
| **Semi-Open (Sicilian, French, Caro-Kann, etc.)** | 35 | $-1.0$ | $-5.5$ | **$-6.5$** |
| **Closed (1.d4 d5, QG, Slav, Tarrasch)** | 7 | $+1.0$ | $+1.5$ | $+2.5$ |
| **Flank & Indian (English, Reti, KID, Nimzo)** | 39 | $-0.5$ | $+1.5$ | $+1.0$ |
| **TOTAL (All 100 Pairs)** | **100** | **$+0.0$** | **$-3.5$** | **$-3.5$** |

---

## 3. Forensic Identification of the Discrepancy

When aggregating the non-Semi-Open openings (Open, Closed, and Flank/Indian):
$$\text{Delta}_{\text{Non-Semi-Open}} = (-0.5) + (+2.5) + (+1.0) = \mathbf{+3.0\text{ points}}$$
- Non-Semi-Open White Delta: $(+0.5) + (+1.0) + (-0.5) = +1.0\text{ pt}$
- Non-Semi-Open Black Delta: $(-1.0) + (+1.5) + (+1.5) = +2.0\text{ pts}$

When aggregating the Semi-Open openings (35 pairs):
- Semi-Open White Delta: **$-1.0\text{ pt}$**
- Semi-Open Black Delta: **$-5.5\text{ pts}$**
- **Total Semi-Open Delta:** $(-1.0) + (-5.5) = \mathbf{-6.5\text{ points}}$

Summing both partitions:
$$\text{Grand Total Delta} = \text{Delta}_{\text{Non-Semi-Open}} + \text{Delta}_{\text{Semi-Open}} = (+3.0) + (-6.5) = \mathbf{-3.5\text{ points}}$$

### Root Cause Classification: Narrative Reporting Ellipsis
The underlying raw dataset and the programmatic summary file [`analysis/v0.44/stratification_summary.json`](file:///E:/ChessXML/project-janus/analysis/v0.44/stratification_summary.json) are **100% mathematically consistent**.

The discrepancy arose in the narrative text of the v0.44 report, which singled out the **Black defensive deficit ($-5.5\text{ pts}$)** in Semi-Open openings as the primary failure mode, while omitting mention of the minor **White deficit ($-1.0\text{ pt}$)** in the same opening family. Because $-5.5$ was cited instead of the family's total delta of $-6.5$, a reader summing the numbers observed $-2.5$ instead of $-3.5$.

---

## 4. Gate D Sign-Off

- [x] Subgroup membership independently reconstructed across all 100 pairs and 400 games.
- [x] Arithmetic reconciled with zero residual error ($+3.0 - 6.5 = -3.5$).
- [x] Root cause classified as a narrative reporting omission of the Semi-Open White delta ($-1.0\text{ pt}$).
- [x] Full reconciliation dataset recorded in `analysis/v0.45/reports/stratification_audit.json`.

**Gate D Status:** **PASS** — Proceeding to Phase E (Controlled Fixed-Depth Experiments).

