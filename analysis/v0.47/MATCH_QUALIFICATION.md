# Controlled Match Qualification (v0.47 Phase H)

## 1. Experimental Methodology

Phase H tests Candidate L1 (Lazy Move Selection) directly against Baseline K0 in a head-to-head match:
- **Opening Corpus:** 25 standardized opening pairs (50 games total) from `analysis/v0.43/openings_v043_100.json`.
- **Colour Balance:** Each opening was played twice:
  - Game 1: Janus-K0 (White) vs Janus-L1 (Black)
  - Game 2: Janus-L1 (White) vs Janus-K0 (Black)
- **Time Control:** 1000 ms base + 50 ms Fischer increment per move.
- **Protocol:** Standard UCI protocol via `SupervisedEngineSession`.
- **Adjudication:** Strict draw claims (3-fold / 5-fold repetition, 50-move rule, 160-ply maximum cutoff).

## 2. Match Results & Score Summary

- **Total Games:** 50
- **Opening Pairs:** 25
- **Janus-K0:** 27.0 / 50 (54.0%) [+24 =6 -20]
- **Janus-L1:** 23.0 / 50 (46.0%) [+20 =6 -24]
- **Decisive Game Rate:** 44 / 50 (88.0%)
- **Draw Rate:** 6 / 50 (12.0%)
- **Engine Violations / Timeouts:** 0 (100% clock and protocol compliance)

## 3. Paired Statistical Attribution

- **Mean Paired Delta ($L1 - K0$):** -0.1600 points per opening pair
- **Standard Error:** 0.1376
- **Paired t-statistic:** -1.1628
- **Two-tailed p-value:** $0.2562$ (not statistically significant at $\alpha = 0.05$)
- **Pair-Bootstrap 95% Confidence Interval:** `[-0.4400, +0.0800]` points per pair
- **Implied Elo Delta:** -27.9 Elo

## 4. Engineering & Scientific Interpretation

1. **Safety and Robustness:** Candidate L1 functioned without a single infrastructure fault, crash, or illegal move across all 50 full-length games.
2. **Playing Strength Impact:** The 95% bootstrap confidence interval `[-0.4400, +0.0800]` includes 0. The performance difference between K0 and L1 is not statistically significant. However, Candidate L1 did not achieve positive playing-strength qualification (+46.0% score).
3. **Causal Attribution:** Under tight 1000ms+50ms time controls, the wall-clock speedup from lazy move selection (+25.7% NPS at fixed depth) is slightly offset by subtle move-order variations in subtrees when move 0 fails to cut off.
4. **Qualification Outcome:** Candidate L1 satisfies non-regression bounds but does not demonstrate a statistically significant playing strength increase.

