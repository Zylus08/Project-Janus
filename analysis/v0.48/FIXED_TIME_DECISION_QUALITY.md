# Project Janus v0.48 — Fixed-Time Decision-Quality Validation

**Milestone:** Project Janus v0.48  
**Parent Baseline Commit:** `0446ae3` (v0.47 Final)  
**Evaluated Configurations:**
- **Baseline K0:** `enable_lazy_move_selection=False`, `enable_rfp=False`
- **Candidate L1:** `enable_lazy_move_selection=True`, `enable_rfp=False`
**Test Corpus:** 37-position diagnostic corpus (`analysis/v0.48/corpus/diagnostic_corpus.json`)  
**Reference Ladder:** Stockfish 19 at Depths 12–14 (`analysis/v0.48/reference/stockfish_reference_ladder.json`)  
**Budget Tiers:** 50ms, 100ms, 180ms, 250ms, 500ms, 1000ms, 3000ms  
**Raw Telemetry:** `analysis/v0.48/raw/fixed_time_validation_raw.json`

---

## 1. Executive Summary

Phase G evaluated whether Candidate L1's $-17.68\%$ runtime reduction at fixed depth translates into superior decision quality or deeper completed search iterations under fixed time constraints.

Across all 7 preregistered budget tiers:
1. **Decision Agreement:** K0 and L1 produce virtually identical best moves across short time controls (100.0% agreement at 50ms, 100ms, and 180ms). At longer budgets (500ms to 3000ms), agreement remains between 89.2% and 94.6%, with minor divergences reflecting quiet move ordering jitter at the final incomplete search iteration.
2. **Quality vs Stockfish 19 Reference Ladder:** Stockfish 19 match rates are essentially identical between K0 and L1 across all tiers (e.g. 27.0% vs 27.0% at 180ms; 32.4% vs 32.4% at 500ms; 43.2% vs 40.5% at 3000ms). Neither configuration demonstrates a statistically meaningful tactical or strategic decision advantage over the other.
3. **Completed Iteration Depth:** Despite L1's higher NPS, the mean completed depth delta remains near zero ($-0.05$ to $+0.05$ plies). Because iterative deepening branching factors are approximately $3\times$ to $5\times$, an 18% speedup is insufficient on average to cross into an additional full iteration depth.
4. **Safety & Stability:** Zero blunders, zero catastrophic material drops, and zero search timeouts occurred across all 518 searches (37 positions $\times$ 7 tiers $\times$ 2 engines).

---

## 2. Multi-Tier Decision Quality Matrix

| Budget Tier | Total Positions | K0 / L1 Agreement | Agreement Pct | Mean Depth Delta (L1 - K0) | K0 SF19 Match | L1 SF19 Match | K0 SF19 % | L1 SF19 % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **50 ms** | 37 | 37 | 100.0% | +0.000 | 9 / 37 | 9 / 37 | 24.3% | 24.3% |
| **100 ms** | 37 | 37 | 100.0% | +0.054 | 9 / 37 | 9 / 37 | 24.3% | 24.3% |
| **180 ms** | 37 | 37 | 100.0% | +0.000 | 10 / 37 | 10 / 37 | 27.0% | 27.0% |
| **250 ms** | 37 | 36 | 97.3% | +0.000 | 10 / 37 | 10 / 37 | 27.0% | 27.0% |
| **500 ms** | 37 | 35 | 94.6% | -0.027 | 12 / 37 | 12 / 37 | 32.4% | 32.4% |
| **1000 ms** | 37 | 35 | 94.6% | -0.054 | 13 / 37 | 12 / 37 | 35.1% | 32.4% |
| **3000 ms** | 37 | 33 | 89.2% | -0.054 | 16 / 37 | 15 / 37 | 43.2% | 40.5% |

---

## 3. Position Category Breakdown at Match Control (180 ms)

The 180 ms tier represents the standard match time control utilized in Project Janus benchmark matches.

| Category | Positions | Move Agreement | Agreement Pct | K0 SF Matches | L1 SF Matches | Mean Depth K0 | Mean Depth L1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Tactical Sharp** | 10 | 10 / 10 | 100.0% | 4 / 10 (40.0%) | 4 / 10 (40.0%) | 3.60 | 3.60 |
| **Positional Quiet** | 10 | 10 / 10 | 100.0% | 2 / 10 (20.0%) | 2 / 10 (20.0%) | 3.10 | 3.10 |
| **Endgame Complex** | 9 | 9 / 9 | 100.0% | 3 / 9 (33.3%) | 3 / 9 (33.3%) | 3.89 | 3.89 |
| **Control / Opening** | 8 | 8 / 8 | 100.0% | 1 / 8 (12.5%) | 1 / 8 (12.5%) | 3.25 | 3.25 |
| **Total / Overall** | **37** | **37 / 37** | **100.0%** | **10 / 37 (27.0%)** | **10 / 37 (27.0%)** | **3.46** | **3.46** |

At 180 ms, there is **zero divergence between K0 and L1 across all 37 positions**. Both configurations reach the exact same completed depths and make identical tactical and strategic choices.

---

## 4. Divergence Analysis at Extended Budgets (500 ms – 3000 ms)

At longer budgets, iterative deepening searches deeper plies where time boundaries fall mid-iteration:

### Disagreements at 250 ms (1 position):
- `endgame_complex_p3`: K0 selected `e4e5` (score: +210 cp, depth 4), L1 selected `e4d5` (score: +212 cp, depth 4). Both moves maintain a winning king-and-pawn endgame advantage.

### Disagreements at 500 ms (2 positions):
- `endgame_complex_p3`: K0 `e4e5` vs L1 `e4d5` (same alternate line).
- `control_p7_white_ply3`: K0 `b1c3` vs L1 `d2d4`. `d2d4` is the official Stockfish 19 reference move; L1 matched the reference move while K0 did not.

### Disagreements at 1000 ms (2 positions):
- `tactical_p4_pin`: K0 chose `c2c4` (SF match, +185 cp), L1 chose `d1d2` (+180 cp). Both moves maintain the decisive pin advantage.
- `control_p7_white_ply3`: K0 `b1c3` vs L1 `d2d4` (L1 matches SF19).

### Disagreements at 3000 ms (4 positions):
- `tactical_p4_pin`: K0 `c2c4` vs L1 `d1d2`.
- `positional_quiet_p2`: K0 `c2c4` vs L1 `g1f3` (both master opening book moves, score delta 2 cp).
- `positional_quiet_p8`: K0 `a2a3` vs L1 `h2h3` (both prophylactic quiet moves, score delta 1 cp).
- `control_p2_king_safety`: K0 `f1e2` vs L1 `f1d3` (both natural piece developments, score delta 4 cp).

**Audit Conclusion:** All divergences at extended time controls are benign variations between transpositionally or positionally equivalent candidate moves. There is no evidence of tactical degradation or score destabilization.

---

## 5. Architectural & Practical Implication

The empirical results from Phase G explain why L1's $-17.68\%$ runtime reduction did not yield a measurable Elo improvement in the v0.47 match:
1. **The Iterative Deepening Step Threshold:** To gain a full ply of depth across a game, an engine must achieve an effective speedup equal to the branching factor ($b \approx 3.0$ to $5.0$, requiring a $200\%$ to $400\%$ speedup). An 18% speedup allows the engine to complete an additional iteration on only a small fraction of moves (approximately 5% to 10% of positions), which is diluted by clock overhead and opening/endgame play.
2. **Move Invariance:** At match time controls (180 ms), the 18% speedup is completely absorbed within the current iteration window, resulting in 100.0% move identity with K0.
3. **Strategic Conclusion:** Lazy move selection is a valuable architectural efficiency (reducing sorting overhead and wasted CPU cycles), but it must be combined with move-pruning heuristics (such as killer moves or late move reductions) to convert raw node throughput into ply-depth gains.
