# Project Janus v0.37 — Pre-Registration Protocol: Time-Management Ablation and Causal Contribution Study

## 1. Administrative and Meta-Information

- **Milestone:** v0.37
- **Project Title:** Time-Management Ablation and Causal Contribution Study under Fischer Increment
- **Principal Research Lead:** Senior Chess Engine Research Engineer, Statistical Validation Lead, and Independent Audit Engineer
- **Repository:** `E:\ChessXML\project-janus`
- **Branch:** `v0.3-benchmark-harness`
- **Baseline Engine Commit:** `42cb05a` (v0.36 report and audit)
- **Pre-Registration Timestamp:** 2026-10-30T10:00:00Z
- **Experiment Manifest File:** `analysis/v0.37/experiment_manifest.json`

---

## 2. Scientific Motivation and Research Questions

In Project Janus v0.36, the adaptive time manager demonstrated a statistically significant playing-strength improvement over the uncalibrated reference policy ($65.0\%$, $+107.5$ Elo, $p = 1.05 \times 10^{-5}$) under $3000\text{ ms} + 100\text{ ms}$ Fischer increment time controls. However, as noted in the v0.36 report, the adaptive policy and the reference policy differed in multiple parameters simultaneously:
1. Increment weight ($0.85$ vs $0.00$)
2. Safety reserve ($50\text{ ms}$ vs $0\text{ ms}$)
3. Default moves-to-go estimate ($30$ vs $40$)

Therefore, v0.36 established the playing strength of the *combined configuration*, but could not isolate the causal contribution of increment weight alone.

### Primary Research Question
> Under identical search, evaluation, opening, and Fischer increment ($3000\text{ ms} + 100\text{ ms}$) conditions, does incorporating the Fischer increment into move-time allocation ($W_{\text{inc}} = 0.85$ vs $W_{\text{inc}} = 0.00$) produce a statistically significant playing-strength improvement when the safety reserve ($50\text{ ms}$) and moves-to-go estimate ($30$) are held strictly constant?

### Secondary Research Questions
1. **Secondary Comparison (Reserve & Horizon Combined):** How much playing strength is associated with changing the safety reserve ($0\text{ ms} \to 50\text{ ms}$) and moves-to-go estimate ($40 \to 30$) when increment weight is held at $0.00$?
2. **Contextual Comparison (Combined Policy Reproduction):** Does the full combined configuration advantage observed in v0.36 replicate cleanly in a fresh 100-game match on the same opening suite?
3. **Search Effort & Time Diagnostics:** Does increment-aware allocation increase node volume and search depth, and does it preserve clock safety without emergency allocations or deadline overshoots?

---

## 3. Experimental Arms and Invariant Definitions

Three experimental arms are evaluated:

| Parameter | Arm A (Original Reference) | Arm B (Matched Reference) | Arm C (Adaptive Candidate) |
| :--- | :--- | :--- | :--- |
| **Increment Weight ($W_{\text{inc}}$)** | `0.00` | `0.00` | `0.85` |
| **Safety Reserve ($R_{\text{ms}}$)** | `0 ms` | `50 ms` | `50 ms` |
| **Default Moves-to-Go ($M$)** | `40` | `30` | `30` |
| **Minimum Allocation** | `10 ms` | `10 ms` | `10 ms` |
| **Maximum Allocation Ratio** | `0.20` | `0.20` | `0.20` |
| **Engine Core** | Janus v0.34 | Janus v0.34 | Janus v0.34 |
| **Evaluation Configuration** | `CONFIG_V034_TAPERED` | `CONFIG_V034_TAPERED` | `CONFIG_V034_TAPERED` |
| **Evaluation Options** | `--eval-all` | `--eval-all` | `--eval-all` |

### Invariant Checks
- **Primary Comparison (Arm B vs Arm C):** Differ **only** in `increment_weight` ($0.00$ vs $0.85$). Reserve, horizon, minimum allocation, max allocation ratio, engine core, search, and evaluation settings are strictly identical.
- **Secondary Comparison (Arm A vs Arm B):** Differ in reserve ($0\text{ ms} \to 50\text{ ms}$) and moves-to-go ($40 \to 30$) while increment weight is held at $0.00$.
- **Contextual Comparison (Arm A vs Arm C):** Replicates the original v0.36 comparison.

---

## 4. Time Control and Match Design

- **Time Control:** $3000\text{ ms}$ base clock $+ 100\text{ ms}$ Fischer increment per move.
- **Opening Suite:** `benchmarks/openings.json` (50 standardized positions, SHA-256 `e883cd4908b73df70b4c1363b00b581caec249494aa1a7720d184c68aaf53af3`).
- **Pairing Design:** 50 opening pairs (100 valid games) per comparison, total 300 valid games across the three planned comparisons:
  - Game 1 of pair: Candidate plays White, Baseline plays Black.
  - Game 2 of pair: Candidate plays Black, Baseline plays White.
- **Supervision & Process Lifecycle:** Fresh supervised engine processes spawned for each game using `SupervisedEngineSession`. Communication verified through standard UCI protocols.

---

## 5. Statistical Inference Protocol

### Primary Endpoint
The paired mean score difference $\bar{\Delta}$ for the primary comparison (Arm B vs Arm C):
$$P_i = \frac{S_{i,1} + S_{i,2}}{2}, \quad \Delta_i = P_i - 0.5, \quad \bar{\Delta} = \frac{1}{M}\sum_{i=1}^{M}\Delta_i$$
where $M = 50$ complete pairs.

### Primary Hypothesis
- $H_0: \bar{\Delta}_{B \to C} = 0.0$ ($S = 0.50$, parity)
- $H_1: \bar{\Delta}_{B \to C} \neq 0.0$ (two-sided, $\alpha = 0.05$)

### Statistical Tests
1. **Paired Student's $t$-test:** $t = \frac{\bar{\Delta}}{SE}$, with $df = 49$. Exact two-sided $p$-value from Student-t CDF.
2. **Paired 95% Confidence Interval:** $[\bar{\Delta} \pm t_{0.975, 49} \cdot SE]$ mapped non-linearly to Elo difference: $E = -400 \log_{10}(1/S - 1)$.
3. **10,000-Resample Opening-Pair Bootstrap:** Non-parametric resampling of complete pairs with fixed random seed $42$.
4. **Paired Non-Parametric Sign Test:** Exact binomial test on decisive pairs ($P_i \neq 0.5$) with ties explicitly accounted for.
5. **Multiple-Comparison Correction:** Holm-Bonferroni step-down procedure across the three comparisons ($H_1: \text{B vs C}$, $H_2: \text{A vs B}$, $H_3: \text{A vs C}$) with family-wise error rate $\alpha = 0.05$.

---

## 6. Infrastructure Reliability, Exclusions, and Stopping Rules

- **Stopping Rule:** Exactly 100 valid games (50 complete pairs) per comparison. No early stopping.
- **Infrastructure Failure Rule:** Any process crash, timeout, or protocol failure triggers an automatic retry (up to 3 attempts per slot) with identical opening position and colour assignment. Infrastructure failures are never counted as chess losses.
- **Adjudication:** Strict checkmate, stalemate, 3-fold repetition, 50-move rule, or 200-ply adjudication draw.

---

## 7. Frozen Hashes

- `benchmarks/openings.json`: `e883cd4908b73df70b4c1363b00b581caec249494aa1a7720d184c68aaf53af3`
- `src/janus/time_manager.py`: `7ab6de9760472812a279b039938c4a5e26c81bea6e80f95e76505ee3d5e17983`
- `src/janus/search.py`: `6c00cc841fb417ebed39895cfe2d19a9f87fbd16fad355b17350842de824b7c9`
- `src/janus/uci.py`: `e003bbe83acd0fd85b8256c5072281900a902764cf195bd2b688589ea8df17ca`
- `src/janus/engine_session.py`: `bfad2fa36cc031e951e24504752088b511ed818d9658fc405f1b680910d9612b`
- `src/janus/evaluation.py`: `957f80b6456ea4fe7a554f8ca7878080740ae4a5d8ab04e91352cebd0f7eb576`
