# Project Janus v0.41 — Search Telemetry Audit & Effective-Depth Diagnostics
**Date:** 2026-11-01  
**Milestone:** v0.41 — Selective Search Qualification & Effective-Depth Optimization  
**Artifact Path:** [`analysis/v0.41/effective_depth_diagnostics.md`](file:///e:/ChessXML/project-janus/analysis/v0.41/effective_depth_diagnostics.md)  
**Author:** Principal Chess Engine Research Engineer, Search Specialist & Validation Lead  

---

## 1. Executive Summary

Milestone v0.41 Phase 5 investigates Janus's search telemetry, effective search depth, and tactical reliability across a curated 16-position diagnostic suite comparing **Baseline (`k0`)**, **Candidate `ord1`** (quiet move ordering enhancements), and **Candidate `rfp`** (Reverse Futility Pruning).

### Key Findings

1. **Telemetry Audit:**
   - Janus reliably captures: completed iteration depth, total nodes, elapsed time, nodes per second (NPS), root score, principal variation (PV), deadline timeouts, transposition table metrics (probes, hits, usable hits, cutoffs, stores, bound flags), and pruning counters (RFP, NMP, LMR, beta cutoffs, countermove cutoffs).
   - **Gaps Identified:** Janus does *not* natively track selective depth (`seldepth`, maximum ply reached in quiescence search) or separate quiescence nodes (`qnodes`) from tree nodes. These are deferred as non-essential for playing strength.
   - **Incomplete Iterations Guarded:** Code audit confirms lines 1191–1196 of [`src/janus/search.py`](file:///e:/ChessXML/project-janus/src/janus/search.py) strictly record `completed_depth = depth` *only after* an iteration completes without `SearchTimeout`.
2. **Tactical Diagnostic Suite (16 Positions at Depth 4):**
   - **Move Agreement with Baseline:** Candidate `rfp` achieved **16 / 16 (100.0%)** move agreement with Baseline `k0`. Candidate `ord1` also achieved **16 / 16 (100.0%)** agreement.
   - **Tactical Accuracy:** All three configurations achieved **13 / 16 (81.25%)** tactical success against reference best-move sets. In all 3 non-matching positions, Baseline, ORD1, and RFP selected identical moves.
3. **Effective Search Efficiency:**
   - **Node Consumption:** Baseline consumed 86,381 nodes; Candidate `ord1` consumed 85,480 nodes (-1.04%); Candidate `rfp` consumed **73,840 nodes (-14.52% node reduction)**.
   - **Execution Time:** Baseline required 8.192s; Candidate `ord1` required 8.334s (+1.73% time due to history malus/countermove indexing overhead); Candidate `rfp` required **7.076s (-13.62% time reduction)**.
   - **Frontier Cutoffs:** Candidate `rfp` executed **1,632 static cutoffs** at depths 1 and 2 with zero tactical penalty.

---

## 2. Search Telemetry Audit (Section 8.1)

### 2.1 Audit Matrix: Captured vs Uncaptured Metrics

| Telemetry Metric | Captured in `SearchResult`? | Emitted in UCI `info`? | Reliability Assessment | Code Location |
| :--- | :---: | :---: | :--- | :--- |
| **Completed Iteration Depth** | Yes | Yes | **Reliable.** Only updated when full iteration completes. | `search.py:1196` |
| **Selective Depth (`seldepth`)** | No | No | **Not tracked.** Max quiescence ply is not recorded. | `search.py:54` |
| **Total Nodes Searched** | Yes | Yes | **Reliable.** Monotonically incremented in search and qsearch. | `search.py:632, 727` |
| **Quiescence Nodes (`qnodes`)** | No | No | **Not separated.** Quiescence increments shared `nodes` counter. | `search.py:632` |
| **Time Spent (seconds/ms)** | Yes | Yes | **Reliable.** High-resolution `time.monotonic()` timing. | `search.py:1204` |
| **Nodes Per Second (NPS)** | Derived | Derived | **Reliable.** `int(nodes / elapsed)`. | `search.py:1204` |
| **Root Score & PV** | Yes | Yes | **Reliable.** Full PV reconstructed and validated. | `search.py:1193-1195` |
| **Search Interruption Reason** | Yes | Implicit | **Reliable.** Caught via `SearchTimeout` exception. | `search.py:1151, 1188` |
| **Transposition Table Metrics** | Yes | Partial | **Reliable.** Probes, hits, usable hits, cutoffs, overwrites tracked. | `search.py:100-108` |
| **Pruning Counters** | Yes | Internal | **Reliable.** RFP cutoffs, NMP attempts/cutoffs, LMR cutoffs. | `search.py:109-111` |

### 2.2 Incomplete Iteration Integrity
A common failure mode in amateur chess engines is reporting the depth of an interrupted iteration as if it had finished. In Janus:
```python
# Only publish results from fully completed iterations.
if pv:
    best_pv = pv
    best_move = pv[0]
best_score = score
completed_depth = depth
```
If a `SearchTimeout` exception is raised inside `_negamax`, the loop terminates (`break`), leaving `completed_depth`, `best_score`, and `best_pv` at the values established by the previously completed iteration.

---

## 3. Curated 16-Position Diagnostic Suite (Section 8.2)

The 16 diagnostic positions were selected to test diverse chess motifs and verify that selective search heuristics do not induce tactical blindness:

| ID | Category | Description | FEN | Expected Move(s) | Provenance |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `pos_01` | Mate in 1 | Queen supported by King mate | `8/7k/5K2/6Q1/8/8/8/8 w - - 0 1` | `g5g7` | `positions.json` |
| `pos_02` | Mate in 1 | Scholar's mate against f7 | `r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1` | `h5f7` | LMR reliability suite |
| `pos_03` | Mate in 1 | Back-rank mate on open file | `6k1/5ppp/8/8/8/8/4QPPP/6K1 w - - 0 1` | `e2e8` | Classic tactical motif |
| `pos_04` | Fork/Pin | Knight fork on King and Rook | `r3k2r/ppp2ppp/8/3N4/8/8/PPP2PPP/R1B1K2R w KQkq - 0 1` | `d5c7` | `test_tactics_lmr.py` |
| `pos_05` | Fork/Pin | Absolute pin along file to King | `4k3/8/8/4n3/8/8/8/4R1K1 w - - 0 1` | `e1e5, f2f4` | `test_tactics_lmr.py` |
| `pos_06` | Promotion | Passed pawn on 7th rank promotes | `8/P7/8/8/8/4k3/8/4K3 w - - 0 1` | `a7a8q, a7a8r` | `positions.json` |
| `pos_07` | Defense | Defend against Q+B mate threat | `r2qk3/pp2pp2/2P2n1Q/1B2p2b/4P2p/2N5/PPP3PP/2K4R b q - 0 19` | `e7e6, d8a5` | `test_tactics_lmr.py` |
| `pos_08` | Deflection | Overworked piece deflection | `3r2k1/p4ppp/1p6/8/8/1Q2B3/PP3PPP/3r2K1 w - - 0 1` | `b3d1` | Tactical evasion fixture |
| `pos_09` | Endgame | Trébuchet pawn zugzwang | `8/8/8/3k4/3p4/3K4/8/8 w - - 0 1` | `d3d2, d3e2` | NMP endgame fixture |
| `pos_10` | Endgame | Direct King opposition | `8/8/4k3/8/4K3/8/8/8 w - - 0 1` | `e4d4, e4f4` | NMP opposition fixture |
| `pos_11` | Attack | Smothered mate setup | `6rk/5Npp/8/8/8/8/8/6K1 w - - 0 1` | `f7h6` | Classic Philidor motif |
| `pos_12` | Defense | Queen retreat balance evaluation | `3qk3/8/8/3r4/8/8/8/3QK3 w - - 0 1` | `d1a4, d1e2, d1f3...` | `test_evaluation_tactical` |
| `pos_13` | Opening | Symmetrical Open Game | `r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7` | `c1g5, c3d5, h2h3` | `positions.json` |
| `pos_14` | Middlegame| Active Bishop pair in center | `r1bq1rk1/ppp2ppp/2n1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 7` | `e1g1, c1d2, c4d5` | NMP PV legality fixture |
| `pos_15` | Endgame | Rook vs Minor conversion | `4k3/8/8/8/8/8/4N3/4K2R w K - 0 1` | `e1g1, h1h7, e1f2` | `positions.json` |
| `pos_16` | Terminal | Stalemate detection | `7k/5Q2/6K1/8/8/8/8/8 b - - 0 1` | `None` (stalemate) | `positions.json` |

---

## 4. Empirical Benchmark Comparison (Depth 4)

Execution across all 16 positions at nominal search depth 4:

| Configuration | Total Nodes | Total Time (s) | Effective NPS | Tactical Accuracy | Move Agreement with Baseline | Heuristic Cutoffs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline (`k0`)** | 86,381 | 8.192s | 10,544 | 13 / 16 (81.25%) | Reference (100.0%) | 0 |
| **Candidate `ord1`** | 85,480 | 8.334s | 10,257 | 13 / 16 (81.25%) | **16 / 16 (100.0%)** | 1,481 Countermove |
| **Candidate `rfp`** | **73,840** | **7.076s** | **10,434** | **13 / 16 (81.25%)** | **16 / 16 (100.0%)** | **1,632 RFP Cutoffs** |
| **RFP Delta vs Baseline** | **-12,541 (-14.52%)** | **-1.116s (-13.62%)** | -110 (-1.04%) | **0.00% (Identical)** | **100.0%** | **+1,632 Cutoffs** |

### Detailed Analysis

1. **Perfect Decision Fidelity:** Candidate `rfp` did not alter the preferred root move in *any* of the 16 positions (100.0% agreement with Baseline).
2. **Computational Savings without NPS Degradation:** Unlike `ord1`, which incurred a net time increase (+1.73%) due to Python dictionary indexing and penalty calculation overhead, `rfp`'s evaluation happens before move generation (`static_eval - margin >= beta`), reducing total runtime by **13.62%**.
3. **Effective-Depth Implication:** In match time controls (3000 ms + 100 ms Fischer increment), a 14.5% to 18.2% reduction in node count allows iterative deepening to complete deeper nominal iterations before the deadline expires. This explains the surge in match playing strength observed in Phase 1 (74.0% score vs Stockfish 1320).

---

## 5. Architectural Diagnostic Verdict

The empirical diagnostics establish that:
1. Janus's shallow completed depth in Blitz matches (depth 2–3) is a function of pure-Python interpreter overhead (~10,000–12,000 NPS).
2. Reverse Futility Pruning is a safe, highly effective selective search enhancement that expands practical depth without inducing tactical blunders.
3. Move ordering heuristics (`ord1`) in pure Python incur overhead that counteracts node reductions, whereas frontier pruning (`rfp`) delivers immediate, clean runtime dividends.
