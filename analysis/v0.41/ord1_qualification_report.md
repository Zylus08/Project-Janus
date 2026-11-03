# Project Janus v0.41 — Candidate ORD1 Independent Qualification Report

**Milestone:** v0.41 Selective Search Qualification & Effective-Depth Optimization  
**Component:** Candidate ORD1 (Countermove Heuristic + Quadratic History Malus)  
**Evaluator:** Senior Chess Engine Research Engineer & Statistical Validation Lead  
**Engine Reference:** Commit `8424f1d` (CLI: `--enable-ord1`, `--enable-countermove`, `--enable-history-penalty`)  

---

## 1. Implementation Audit & Move Ordering Semantics

Candidate ORD1 modifies quiet move ordering in `JanusSearch` through two complementary mechanisms:

### 1.1 Countermove Heuristic
- **Table Topology:** $64 \times 64$ array `countermoves: list[list[Optional[chess.Move]]]` storing the refutation move indexed by `[prev_move.from_square][prev_move.to_square]`.
- **Preceding Move Derivation:** Evaluated via `board.peek()` whenever `board.move_stack` is non-empty and `board.peek() != chess.Move.null()`. This avoids signature modifications to `_negamax`, maintaining 100% backward compatibility with mocks and test suites.
- **Priority Tier:** Scored at `550,000`, strictly positioned between Killer Move 2 (`600,000`) and general history ($\le 500,000$).
- **Update Rule:** When a quiet move causes a beta cutoff at depth $d$:
  ```python
  if self.enable_countermoves and prev_move is not None:
      if move == self.countermoves[prev_move.from_square][prev_move.to_square]:
          self.countermove_cutoffs += 1
      self.countermoves[prev_move.from_square][prev_move.to_square] = move
  ```

### 1.2 Quadratic History Malus
- **Deficiency in Baseline:** The legacy history heuristic applied bonuses ($+ d^2$) to quiet cutoff moves, but quiet moves that were searched and failed to cause cutoffs suffered zero penalty. As a result, suboptimal quiet moves were repeatedly re-ordered at equal priority across iterations.
- **Malus Mechanism:** At each node, quiet moves searched prior to a beta cutoff are collected in `searched_quiets: list[chess.Move]`.
- **Deduction Rule:** When a quiet cutoff occurs at depth $d$, preceding failed quiet moves receive a quadratic malus:
  ```python
  if self.enable_history_malus:
      bonus = depth * depth
      for bad_move in searched_quiets:
          bf, bt = bad_move.from_square, bad_move.to_square
          self.history[bf][bt] = max(-MAX_HISTORY_SCORE, self.history[bf][bt] - bonus)
  ```
- **Bounds & Determinism:** Bounded within $[-\text{MAX\_HISTORY\_SCORE}, +\text{MAX\_HISTORY\_SCORE}]$ ($[-500,000, +500,000]$). Fully deterministic across identical search instances.

---

## 2. Controlled Four-Way Performance Profiling

Evaluated on the 8 representative benchmark positions at Depth 4:

| Configuration | History Malus | Countermoves | Total Nodes | Node $\Delta\%$ | Time (ms) | Time $\Delta\%$ | Pooled NPS | Beta Cutoffs | CM Cutoffs |
|:---|:---:|:---:|---:|---:|---:|---:|---:|---:|---:|
| **Baseline (K0)** | Off | Off | 80,796 | 0.00% | 2,759.2 | 0.00% | 29,282.6 | 4,856 | 0 |
| **`ord_malus`** | **On** | Off | 76,671 | **-5.11%** | 2,594.9 | **-5.95%** | 29,546.9 | 4,536 | 0 |
| **`ord_cm`** | Off | **On** | 80,840 | +0.05% | 2,757.8 | -0.05% | 29,313.2 | 4,856 | 723 |
| **Candidate ORD1** | **On** | **On** | 76,404 | **-5.44%** | 2,592.9 | **-6.03%** | 29,466.5 | 4,536 | 712 |

### Profiling Insights:
1. **Isolated Contributions:**
   - History malus drives almost the entire tree reduction (-5.11% nodes, -5.95% time), successfully penalizing non-viable quiet candidate moves.
   - Countermove alone is node-neutral on shallow depth 4 (+0.05%), but produces 723 cutoffs with high confidence.
2. **Combined Synergy:** Candidate ORD1 achieves the lowest node count (76,404 nodes, -5.44%) and search time (2,592.9 ms, -6.03%), while pooled NPS is slightly higher (+0.6%) due to fewer deep branch expansions.

---

## 3. Controlled 50-Game Playing Strength Audit

Evaluated against Stockfish 19 Elo 1320 (3000 ms + 100 ms Fischer increment, 25 colour-reversed pairs):

| Metric | Baseline Reference (K0) | Candidate ORD1 | Direct Delta (ORD1 - K0) |
|:---|:---:|:---:|:---:|
| **Valid Games** | 50 | 50 | 0 |
| **Wins / Draws / Losses** | 21W / 3D / 26L | 20W / 5D / 25L | -1W / +2D / -1L |
| **Total Score** | 22.5 / 50.0 (45.0%) | 22.5 / 50.0 (45.0%) | **+0.0 pts (0.0%)** |
| **Score as White** | 13.5 / 25.0 (54.0%) | 10.5 / 25.0 (42.0%) | -3.0 pts |
| **Score as Black** | 9.0 / 25.0 (36.0%) | 12.0 / 25.0 (48.0%) | +3.0 pts |
| **Paired Delta ($\bar{\delta}$)** | - | - | **0.0000** |
| **Paired t-statistic** | - | - | **$t = 0.0000$ ($p = 1.0000$)** |
| **10k Bootstrap 95% CI on $\Delta$** | - | - | **$[-36.0\%, +34.0\%]$** |
| **Estimated Elo vs SF 1320** | -34.9 Elo | -34.9 Elo | 0.0 Elo |

---

## 4. Scientific Verdict & Default-Policy Decision

1. **Correctness:** **VERIFIED**. Passes all 6 dedicated unit tests in `tests/test_v040_move_ordering.py`, preserves move legality, determinism, and forced mate detection.
2. **Performance:** **MEASURED**. Achieves a verified **-5.44% reduction in nodes** and **-6.03% in search time** across 8 standard positions.
3. **Playing Strength:** **INCONCLUSIVE AT $N=50$**. Score is identical to baseline (45.0% vs 45.0%, $t=0.0000, p=1.0000$). The wide 95% bootstrap confidence interval ($[-36\%, +34\%]$) indicates that 50 games lack sufficient statistical power to detect subtle rating differentials ($\le 25\text{ Elo}$).
4. **Final Decision:** **RETAIN AS EXPERIMENTAL COMPONENT — KEEP DISABLED BY DEFAULT**.
   - Governed by Section 11 of the v0.41 specification: *"ORD1 must remain disabled unless the evidence supports enabling it under the project's criteria."*
   - Enabled via `--enable-ord1` for testing and evaluation. Default engine leaves it `False`.

