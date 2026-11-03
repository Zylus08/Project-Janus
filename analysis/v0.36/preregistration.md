# Project Janus v0.36 — Pre-Registration Experiment Protocol

**Protocol Identifier:** `analysis/v0.36/preregistration.md`  
**Milestone:** Janus v0.36  
**Lead Investigator:** Statistical Validation Lead & Experimental Design Specialist  
**Status:** FROZEN PRIOR TO EXPERIMENT EXECUTION  
**Date:** October 2026  
**Git Baseline Commit:** `02828fb`  

---

## 1. Research Question and Objectives

### 1.1 Research Question
> Under identical engine, search, evaluation, opening, and Fischer increment time-control conditions, does the v0.35 adaptive time-management policy achieve a statistically significant higher match score than the reference time-management policy?

### 1.2 Prior Context
In Janus v0.35, a preliminary 20-game trial under $3000\text{ ms} + 100\text{ ms}$ increment observed:
- Adaptive: 12.0 / 20.0 (60.0%)
- Reference: 8.0 / 20.0 (40.0%)
- Estimated Elo diff: $+70.4$
- 95% Confidence Interval: `[-85.0, +225.8]` Elo
- Paired sign-test $p$-value: $0.4531$

Because the 95% confidence interval crosses zero and the sample size ($N=20$) is small, the v0.35 result was scientifically inconclusive. This v0.36 experiment is designed to substantially reduce statistical uncertainty through a pre-registered 100-game match ($M=50$ opening pairs).

---

## 2. Experimental Hypotheses and Endpoints

### 2.1 Hypotheses
- **Null Hypothesis ($H_0$):** The adaptive policy has parity with the reference policy under the tested Fischer increment control ($\mu_{\Delta} = 0$, equivalent to expected score $S = 0.50$).
- **Alternative Hypothesis ($H_1$):** The adaptive policy has a different playing strength from the reference policy ($\mu_{\Delta} \ne 0$, two-sided test at $\alpha = 0.05$).

### 2.2 Primary Endpoint
The primary endpoint is the match score percentage achieved by the adaptive candidate:
$$S = \frac{W + 0.5D}{N}$$
where $W$ is candidate wins, $D$ is draws, and $N$ is total valid games ($N = 100$).

The statistical test of the primary endpoint uses the opening pair as the primary independent sampling unit:
$$P_i = \frac{S_{i,1} + S_{i,2}}{2}$$
$$\Delta_i = P_i - 0.5$$
$$\bar{\Delta} = \frac{1}{M}\sum_{i=1}^{M}\Delta_i$$
with $M = 50$ opening pairs.

### 2.3 Secondary Endpoints
1. **Paired t-test:** $t = \frac{\bar{\Delta}}{s_{\Delta} / \sqrt{M}}$ with $df = 49$, reporting two-sided $p$-value and 95% confidence interval.
2. **Paired Bootstrap Confidence Interval:** Non-parametric bootstrap resampling of opening pairs with 10,000 resamples and fixed RNG seed ($42$).
3. **Paired Sign Test:** Exact binomial test on decisive opening pairs ($P_i \ne 0.5$), with tied pairs documented explicitly.
4. **Elo Point Estimate and Uncertainty Interval:**
   $$E = -400 \log_{10}\left(\frac{1}{S} - 1\right)$$
   Propagated using both paired standard error and bootstrap percentile transformation.
5. **Colour Performance:** Scores separated by White and Black.
6. **Time Diagnostics:**
   - Move duration distributions (median, 25th, 75th, 95th, 99th percentiles).
   - Remaining clock distributions and maximum clock drawdown.
   - Target allocation vs actual duration ratios.
   - Frequency of emergency allocations ($T_{\text{rem}} \le R_{\text{safe}}$).
   - Frequency of deadline stops and legal fallback moves.
   - Maximum observed deadline overshoot.
   - Phase-dependent timing behaviour (opening, middlegame, endgame).
7. **Infrastructure Reliability:** Count of engine crashes, timeouts, and retries.

---

## 3. Experimental Controls and Scope Boundary

### 3.1 Policy Configurations
Both policies use identical evaluation (`CONFIG_V034_TAPERED`, `--eval-all`) and identical search heuristics (PVS, TT with 50,000 entries, LMR, NMP, Killer/History).

#### Candidate: Adaptive Policy (`--time-policy adaptive`)
- `safety_reserve_ms`: $50\text{ ms}$
- `default_moves_to_go`: $30$
- `increment_weight`: $0.85$
- `min_allocation_ms`: $10\text{ ms}$
- `max_allocation_ratio`: $0.20$

#### Reference: Uncalibrated Baseline Policy (`--time-policy reference`)
- `safety_reserve_ms`: $0\text{ ms}$
- `default_moves_to_go`: $40$
- `increment_weight`: $0.00$
- `min_allocation_ms`: $10\text{ ms}$
- `max_allocation_ratio`: $0.50$

### 3.2 Interpretive Boundary
Because the adaptive policy differs from the reference policy in safety reserve ($50\text{ ms}$ vs $0\text{ ms}$) and horizon ($30$ vs $40$ moves) in addition to increment weight ($0.85$ vs $0.0$), this experiment evaluates the **combined policy configuration** against the defined project control. It does not isolate the causal effect of the increment weight in isolation.

---

## 4. Match Design and Execution Protocol

### 4.1 Sample Size and Stopping Rule
- **Planned Games:** Exactly 100 valid games ($M = 50$ opening pairs).
- **Stopping Rule:** No early stopping, peeking, or post-hoc sample expansion. If the confidence interval includes zero after 100 games, the result will be reported honestly as inconclusive.

### 4.2 Time Control
- **Format:** Fischer increment.
- **Initial Clock:** $3000\text{ ms}$ per side ($3.0\text{ seconds}$).
- **Increment:** $100\text{ ms}$ per move ($0.1\text{ seconds}$).

### 4.3 Opening Suite and Colour Balance
- 50 opening positions deterministically selected from `benchmarks/openings.json` using seed $42$.
- Pair $i$ ($i = 1 \dots 50$):
  - Game $2i - 1$: Candidate plays White, Reference plays Black.
  - Game $2i$: Reference plays White, Candidate plays Black.

### 4.4 Process Supervision and Failure Handling
- Each game runs in an isolated, supervised subprocess (`SupervisedEngineSession`).
- Any infrastructure failure (process crash, pipe failure, startup hang) triggers immediate termination and process cleanup.
- Infrastructure failures are strictly excluded from chess results and retried up to 3 times per game slot with the identical opening position and colour assignment.

---

## 5. Frozen File Hashes (SHA-256)

| Component | Path | SHA-256 Hash |
| :--- | :--- | :--- |
| Opening Suite | `benchmarks/openings.json` | `e883cd4908b73df70b4c1363b00b581caec249494aa1a7720d184c68aaf53af3` |
| Time Manager | `src/janus/time_manager.py` | `10dc5ab356eb3d26fdc2c6f17c8460c239b3790476f76b6cce1947df6381c835` |
| Search Subsystem | `src/janus/search.py` | `6c00cc841fb417ebed39895cfe2d19a9f87fbd16fad355b17350842de824b7c9` |
| UCI Interface | `src/janus/uci.py` | `ee8c5ef0b689e2e134877c96b7230dea02527fbfbe4bcb71fbc908398901be6a` |
| Engine Session | `src/janus/engine_session.py` | `bfad2fa36cc031e951e24504752088b511ed818d9658fc405f1b680910d9612b` |
| Evaluation Subsystem | `src/janus/evaluation.py` | `957f80b6456ea4fe7a554f8ca7878080740ae4a5d8ab04e91352cebd0f7eb576` |

---

## 6. Pre-Registration Statement
This protocol is recorded and frozen prior to running the v0.36 experimental qualification and match execution.
