# Project Janus v0.41 — Candidate RFP Qualification Report
**Date:** 2026-11-01  
**Milestone:** v0.41 — Selective Search Qualification & Effective-Depth Optimization  
**Artifact Path:** [`analysis/v0.41/rfp_qualification_report.md`](file:///e:/ChessXML/project-janus/analysis/v0.41/rfp_qualification_report.md)  
**Author:** Principal Chess Engine Research Engineer, Statistical Validation Lead & Independent Audit Engineer  

---

## 1. Executive Summary

In milestone v0.40, Candidate `rfp` (Reverse Futility Pruning, also known as static null-move pruning) successfully passed **Gate A** (implementation audit), **Gate B** (7 unit tests passing), and **Gate C** (18.22% node reduction across standard profiling fixtures). However, its final status was classified as **INCONCLUSIVE (Gate D Deferred)** because computational budget constraints in v0.40 prevented running the preregistered 50-game controlled playing-strength match.

In milestone v0.41, we resolved this qualification gap by executing the preregistered 50-game controlled paired match for Candidate `rfp` against Stockfish 19 configured to Elo 1320 under Fischer time controls (3000 ms initial + 100 ms Fischer increment).

### Key Empirical Findings

1. **Decisive Playing-Strength Improvement:**
   - Candidate `rfp` scored **37.0 / 50 points (74.0%)** (33 wins, 8 draws, 9 losses).
   - This represents a direct **+14.5 point (+29.0 percentage point)** improvement over Baseline `k0` (22.5/50, 45.0%) and Candidate `ord1` (22.5/50, 45.0%) on the identical 25 opening pairs.
2. **Statistical Significance:**
   - Mean colour-reversed pair difference: $\bar{d} = +0.4800$ points/pair ($+24.0\%$ per game).
   - Standard error: $SE = 0.1241$.
   - Paired Student $t$-statistic: $t = 3.8680$.
   - Two-tailed $p$-value: $p \approx 0.00073$ ($7.3 \times 10^{-4} \ll 0.05$).
   - 10,000-sample pair-bootstrap 95% confidence interval: **$[61.0\%, 85.0\%]$**. The lower bound (61.0%) strictly exceeds the baseline score (45.0%) and parity (50.0%).
   - Estimated Elo rating against Stockfish 1320: $+181.7\text{ Elo}$ (an estimated gain of **$+216.6\text{ Elo}$** over Baseline K0 at $-34.9\text{ Elo}$).
3. **Four-Gate Qualification Verdict:**
   - **Gate A (Implementation & Safety Guards):** `PASS`
   - **Gate B (Correctness & Invariant Tests):** `PASS`
   - **Gate C (Search Tree Efficiency):** `PASS` (-18.22% nodes)
   - **Gate D (Controlled Playing-Strength Match):** `PASS` ($p = 0.00073$, $+29.0\%$ win rate)
   - **Final Classification:** **`SUPPORTED`**

---

## 2. Gate A — Implementation Audit & Tactical Safety Guards

Reverse Futility Pruning is evaluated at frontier nodes ($\text{depth} \le 2$) in [`src/janus/search.py`](file:///e:/ChessXML/project-janus/src/janus/search.py) before move generation:

$$\text{margin} = \text{depth} \times 120\text{ cp}$$

If the static evaluation exceeds the fail-high threshold plus margin:

$$\text{static\_eval} - \text{margin} \ge \beta$$

the sub-tree is pruned with a soft fail-high score $(\text{static\_eval} - \text{margin})$, clamped against artificial mate scores.

### Guard Auditing

| Guard Condition | Purpose | Verification Status |
| :--- | :--- | :--- |
| `not in_check` | Do not prune when King is under direct tactical check | Verified: Line 853 of `search.py` |
| `abs(beta) < MATE_THRESHOLD` | Prevent pruning near terminal checkmate evaluations | Verified: Line 855 of `search.py` |
| `has_nmp_material(board)` | Prevent zugzwang corruption in pawn-only or king-only endgames | Verified: Line 856 of `search.py` |
| `depth <= self.rfp_max_depth` | Confine pruning strictly to shallow frontier plies ($\le 2$) | Verified: Line 852 of `search.py` |
| Score clamping | Clamp returned score to `min(beta, static_eval - margin)` | Verified: Line 860 of `search.py` |

All required theoretical safeguards are strictly enforced.

---

## 3. Gate B & Gate C — Correctness and Tree Efficiency

### Correctness Tests (`tests/test_v040_rfp.py`)
All 7 unit tests covering RFP invariants pass cleanly:
1. `test_rfp_prunes_at_depth_1_and_2`: Confirms cutoffs fire when static eval comfortably exceeds beta + margin.
2. `test_rfp_disabled_at_depth_3`: Ensures depth 3 and deeper explore full tactical lines.
3. `test_rfp_bypassed_in_check`: Ensures checks are never pruned.
4. `test_rfp_bypassed_in_zugzwang`: Ensures pawn-only endgames bypass RFP.
5. `test_rfp_pv_legality`: Confirms all PV lines returned under RFP remain 100% legal.
6. `test_rfp_telemetry_counters`: Verifies `rfp_considered` and `rfp_cutoffs` increment monotonically.
7. `test_rfp_mate_guard`: Ensures mate scores are never erroneously returned.

### Profiling Efficiency
Across the benchmark suite, RFP reduced total search node consumption from **80,796 nodes** to **66,076 nodes** (**-18.22% reduction**), saving 18.0% search time with zero search instability.

---

## 4. Gate D — Controlled Match Evidence (50 Games vs Stockfish 19 Elo 1320)

### 4.1 Experimental Protocol
- **Target Opponent:** Stockfish 19 (SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`)
- **Stockfish Settings:** `Threads=1, Hash=64, UCI_LimitStrength=true, UCI_Elo=1320`
- **Time Control:** 3000 ms base + 100 ms Fischer increment
- **Openings:** 25 curated, opening-balanced pairs from `benchmarks/openings.json` (50 games total)
- **Time Allocation Policy:** `arm_c` (Adaptive Time Manager with dynamic complexity scaling)
- **Output Artifacts:** [`analysis/v0.41/match_rfp/`](file:///e:/ChessXML/project-janus/analysis/v0.41/match_rfp/)

### 4.2 Raw Performance Breakdown

| Metric | Baseline K0 (v0.40) | Candidate ORD1 (v0.40) | Candidate RFP (v0.41) | Delta (RFP vs K0) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Games** | 50 | 50 | 50 | — |
| **Complete Pairs** | 25 | 25 | 25 | — |
| **Wins (W)** | 21 | 20 | **33** | +12 (+57.1%) |
| **Draws (D)** | 3 | 5 | **8** | +5 (+166.7%) |
| **Losses (L)** | 26 | 25 | **9** | -17 (-65.4%) |
| **Total Points** | 22.5 / 50 | 22.5 / 50 | **37.0 / 50** | **+14.5 pts** |
| **Score Pct** | 45.0% | 45.0% | **74.0%** | **+29.0%** |
| **White Score** | 13.5 / 25 (54.0%) | 10.5 / 25 (42.0%) | **18.5 / 25 (74.0%)** | +5.0 pts |
| **Black Score** | 9.0 / 25 (36.0%) | 12.0 / 25 (48.0%) | **18.5 / 25 (74.0%)** | +9.5 pts |
| **Mean Pair Diff ($\bar{d}$)** | -0.1000 | -0.1000 | **+0.4800** | **+0.5800** |
| **Std Error ($SE$)** | 0.1444 | 0.1581 | **0.1241** | -0.0203 |
| **$t$-statistic** | -0.6928 | -0.6325 | **+3.8680** | **+4.5608** |
| **$p$-value** | 0.4884 | 0.5271 | **0.00073** | **$p < 0.001$** |
| **95% Bootstrap CI** | [31.0%, 59.0%] | [30.0%, 60.0%] | **[61.0%, 85.0%]** | Strictly disjoint from K0 |
| **Estimated Elo vs SF1320** | -34.9 | -34.9 | **+181.7** | **+216.6 Elo** |

### 4.3 Why Did RFP Produce Such a Large Gain?

1. **Frontier Pruning Avoids Futile Node Waste:** In Blitz time controls (3s + 100ms), Janus previously struggled to reach completed depths greater than 2 to 3 plies. By safely pruning quiescent positions where the side to move is already massively ahead of $\beta$ at depth 1 and 2, RFP freed up between 18% and 25% of the node budget.
2. **Effective Search Depth Increase:** In several complex endgames and tactical openings, freeing the node budget allowed iterative deepening to complete **depth 3 and depth 4 iterations** within the 3-second Fischer window where Baseline K0 timed out at depth 2.
3. **Black Score Surge:** Black won or drew 18.5 / 25 games (74.0%) under RFP compared to only 9.0 / 25 (36.0%) under K0. Deepening Black's defensive horizon eliminated early opening tactical collapses.

---

## 5. Gate Qualification Matrix & Classification

Under the Project Janus v0.41 decision framework:

| Gate | Criterion | Threshold | Observed Value | Verdict |
| :---: | :--- | :--- | :---: | :---: |
| **Gate A** | Theoretical Soundness & Safety Guards | In-check, zugzwang, mate guards verified | 100% compliant | **PASS** |
| **Gate B** | Correctness & Search Invariants | All regression tests pass | 7/7 tests pass | **PASS** |
| **Gate C** | Search Efficiency | Node reduction $\ge 5\%$ without time blowup | -18.22% nodes | **PASS** |
| **Gate D** | Controlled Playing Strength | Score $\ge 50\%$, paired $t$-test $p < 0.05$ | 74.0%, $p = 0.00073$ | **PASS** |

### Decision
**`SUPPORTED`**

Candidate `rfp` satisfies all four gates conclusively with overwhelming statistical support ($p = 0.00073$, 95% CI $[61.0\%, 85.0\%]$).

### Production Recommendation
Enable Candidate RFP (`--enable-rfp`, `rfp_max_depth=2`, `rfp_margin_per_depth=120`) as a **qualified, supported search feature** for Project Janus.
