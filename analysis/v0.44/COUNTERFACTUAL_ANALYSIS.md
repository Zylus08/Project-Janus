# Counterfactual Search Analysis Report — v0.44

**Milestone:** Project Janus v0.44  
**Date:** 2026-11-03  
**Status:** PASS (Gate E Validated)

---

## 1. Executive Summary

To determine whether Reverse Futility Pruning (RFP) causes false cutoffs or tactical blunders, we executed controlled paired counterfactual search experiments on all 37 positions in the diagnostic corpus (31 divergence positions and 6 controls).

Each position was searched under strictly identical search parameters:
- **Baseline K0:** `enable_rfp=False`, nominal depth 4.
- **Candidate RFP:** `enable_rfp=True`, `rfp_max_depth=2`, `rfp_margin_per_depth=120`, telemetry active, nominal depth 4.
- **Ground-Truth Evaluation Oracle:** Stockfish 19 (depth 10) evaluating the board before and after the move choices to quantify move quality ($\Delta_{\text{eval}} = E(m_{\text{K0}}) - E(m_{\text{RFP}})$).

---

## 2. Quantitative Classification Results

All 37 positions were categorized into the five preregistered categories:

| Category | Description | Count | Percentage |
|---|---|---|---|
| **Category 1** | No material search difference (same move, $\le 2\%$ node diff) | 8 | 21.6% |
| **Category 2** | Efficiency benefit (same move, $> 2\%$ node reduction, up to 42.8%) | 29 | 78.4% |
| **Category 3** | Disagreement without established harm ($\Delta_{\text{eval}} < 30\text{ cp}$) | 0 | 0.0% |
| **Category 4** | Potential false cutoff ($30 \le \Delta_{\text{eval}} < 100\text{ cp}$) | 0 | 0.0% |
| **Category 5** | Confirmed tactical regression ($\Delta_{\text{eval}} \ge 100\text{ cp}$) | 0 | 0.0% |

### Key Findings:
1. **Zero False Cutoffs at Identical Depth:** In 100% of tested positions (37/37), under identical nominal search depth (depth 4), K0 and RFP chose the **exact same best move** ($k0\_move == rfp\_move$).
2. **Substantial Search Efficiency:** In 78.4% of positions (Category 2), RFP delivered significant node reductions:
   - Pair 76 (Black ply 2): $10,604 \to 6,070$ nodes (**42.8% reduction**)
   - Pair 78 (White ply 9): $12,391 \to 8,468$ nodes (**31.7% reduction**)
   - Pair 73 (Black ply 5): $10,849 \to 7,771$ nodes (**28.4% reduction**)
   - Pair 76 (White ply 9): $13,935 \to 10,083$ nodes (**27.6% reduction**)
   - Pair 99 (White ply 5): $8,889 \to 6,523$ nodes (**26.6% reduction**)
   - Pair 54 (White ply 6): $12,669 \to 9,913$ nodes (**21.8% reduction**)
   - Mean aggregate node reduction across the corpus was **10.2%**.
3. **No Blunder Attribution:** Not a single position exhibited a Category 4 or Category 5 tactical regression.

---

## 3. Dissecting the Origin of Match Divergences

Because RFP does not alter move selection at identical nominal depth, why did K0 and RFP play different moves during the v0.43 match?

Forensic inspection of [`analysis/v0.44/check_depth_moves.py`](file:///E:/ChessXML/project-janus/analysis/v0.44/check_depth_moves.py) and [`analysis/v0.43/match_replication/match_moves.csv`](file:///E:/ChessXML/project-janus/analysis/v0.43/match_replication/match_moves.csv) revealed the causal mechanism:
- Under the $3.0\text{s} + 0.1\text{s}$ time control, Janus is allocated approximately $180\text{ ms}$ per move.
- In this narrow computational window, Janus operates directly on the frontier between completing depth 2 and completing depth 3:
  - At depth 2, moves are heavily dominated by static evaluation and shallow tactics.
  - At depth 3, iterative deepening refines or completely changes the move choice (e.g. in Pair 1: depth 2 chose `d4e5`, depth 3 chose `g1f3`; in Pair 2: depth 2 chose `d2d4`, depth 3 chose `a2a4`; in Pair 20: depth 2 chose `c1d2`, depth 3 chose `c2c3`).
- Because RFP prunes frontier nodes, it alters the search iteration timing. In some plies, RFP's faster search allowed it to complete depth 3 when K0 timed out at depth 2; in other plies, small host latency fluctuations or branch complexity variations shifted the search boundary, resulting in different completed iteration depths at the timeout deadline.
- When an iteration is aborted by `SearchTimeout`, Janus discards the partial iteration and plays the `best_move` from the last fully completed depth. This depth-boundary disparity—not tactical blindness in RFP—caused the move divergences.

---

## 4. Gate E Sign-Off

- [x] Paired counterfactual searches executed on all 37 diagnostic positions.
- [x] Move quality independently scored against Stockfish 19 reference oracle.
- [x] All positions classified into Categories 1 to 5.
- [x] Full telemetry and results recorded in `analysis/v0.44/counterfactual_results.json`.

**Gate E Status:** **PASS** — Proceeding to Phase F (Search Efficiency & Timing Distribution Investigation).

