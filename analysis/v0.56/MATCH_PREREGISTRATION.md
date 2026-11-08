# Project Janus v0.56 — Primary Strength Match Preregistration

**Milestone:** Project Janus v0.56  
**Document Classification:** Formal Match Preregistration Protocol  
**Date:** 2026-11-06  
**Repository Branch:** `v0.3-benchmark-harness`  
**Git Base HEAD:** `f6025c3`  
**Candidate Engine:** Janus Native N7 (C++17 SEE-Enhanced Capture Ordering)  
**Baseline Engine:** Janus Native N5 (C++17 Production Baseline)  

---

## 1. Experimental Objective & Formal Hypotheses

The objective of this preregistered experiment is to determine whether Static Exchange Evaluation (SEE) capture ordering in both main search and quiescence search confers a statistically demonstrable playing strength improvement over the frozen production baseline N5 under Fischer blitz time controls.

### 1.1 Formal Hypotheses
- **Null Hypothesis ($H_0$):** Static Exchange Evaluation capture ordering produces no change in playing strength against Baseline N5 under equal Fischer time controls:
  $$\Delta_{\text{score}} = \mu_{\text{N7}} - \mu_{\text{N5}} = 0$$
- **Alternative Hypothesis ($H_1$):** Static Exchange Evaluation capture ordering significantly alters playing strength:
  $$\Delta_{\text{score}} \neq 0$$
- **Directional Expectation:** By demoting losing captures ($\text{SEE} < 0$) below killer moves and correctly prioritizing winning captures in both main and quiescence search, N7 should achieve deeper effective search and superior tactical conversion, resulting in $\Delta_{\text{score}} > 0$.

---

## 2. Experimental Controls & Configuration Integrity

### 2.1 Engine Configurations
Both engines are instantiated from the exact same bitboard binary executable (`analysis/v0.56/native/janus_native_engine.exe`), guaranteeing identical compilation flags (MSVC x64 `/O2 /Ot /Oi /std:c++17`), identical board state representation, identical move generator, identical static evaluation function, and identical hardware footprint. Configuration differences are restricted strictly to UCI parameters:

| Parameter | Baseline (Janus N5) | Candidate (Janus N7) | Rationale |
| :--- | :--- | :--- | :--- |
| `UseKillerOrdering` | `true` | `true` | Standard quiet move ordering |
| `UseHistoryOrdering` | `true` | `true` | Standard quiet move ordering |
| `UsePVS` | `false` | `false` | Isolated from PVS interactions |
| `UseLMR` | `true` | `true` | Standard quiet move reductions |
| `UseSEEOrdering` | **`false`** | **`true`** | **Experimental Factor 1 (Main Search SEE)** |
| `UseSEEInQuiescence` | **`false`** | **`true`** | **Experimental Factor 2 (Q-Search SEE)** |
| Transposition Table Size | 64 MB (1,048,576 slots) | 64 MB (1,048,576 slots) | Equal memory budget |
| Max Plies / Horizon | 300 plies | 300 plies | Standard safety limit |

### 2.2 Opening Suite & Paired Structure
- **Corpus File:** `analysis/v0.56/corpus/independent_openings_v056.json`
- **Corpus SHA-256 Digest:** `d4db2cf96044421ed5ab195f1af49d1d34df0297fcab196b1b7fc92b58b1784a`
- **Pair Count:** 100 paired openings (200 total games).
- **Opening Independence:** 100% disjoint from all opening suites utilized in v0.50, v0.51, v0.52, v0.53, v0.54, and v0.55.
- **Color Balance:** Each opening is played exactly twice per pair:
  - Game 1: N7 plays White, N5 plays Black.
  - Game 2: N5 plays White, N7 plays Black.

### 2.3 Time Control & Clock Allocation
- **Base Clock:** 3.0 seconds (3,000 ms).
- **Increment:** 0.10 seconds (100 ms) per move (Fischer 3+0.1).
- **Clock Enforcement:** Native UCI engine clock management (`wtime`, `btime`, `winc`, `binc`), deducting elapsed time per ply with 10ms minimum floor.

---

## 3. Adjudication & Tournament Integrity Protocol

### 3.1 Strict FIDE Rules Adjudication
All game terminations are adjudicated programmatically via the independent `python-chess` reference library:
1. **Checkmate:** King is in check with no legal evasions (Score: 1-0 or 0-1).
2. **Stalemate:** Side to move has no legal moves and is not in check (Score: 1/2-1/2).
3. **Threefold Repetition:** The exact position (including turn, castling rights, and en passant square) occurs 3 times (Score: 1/2-1/2).
4. **Fifty-Move Rule:** 100 half-moves elapsed without a pawn push or capture (Score: 1/2-1/2).
5. **Insufficient Material:** Neither side has mating material (K vs K, K+B vs K, K+N vs K, K+B vs K+B with same-colored bishops) (Score: 1/2-1/2).

### 3.2 Safety Horizon Limit
- **Non-FIDE Safety Limit:** 300 plies (150 full moves). Any game reaching ply 300 without natural termination is scored 1/2-1/2 (`safety_horizon_300_plies`).

### 3.3 Disqualification Criteria
- Engine process crash or unhandled exception.
- Engine stall (failure to emit `bestmove` within time budget + 5.0s grace window).
- Emission of an illegal move or malformed UCI string.
- Occurrence of any disqualification immediately yields a forfeit loss (0.0 points) for that game.

---

## 4. Statistical Methodology

### 4.1 Paired Observation Unit
To eliminate opening bias, the unit of observation is the paired opening score difference:
$$d_i = \text{Score}_{\text{N7}}(i) - \text{Score}_{\text{N5}}(i) \quad \text{for } i \in \{1, 2, \dots, 100\}$$
where $\text{Score}_{\text{N7}}(i) \in \{0.0, 0.5, 1.0, 1.5, 2.0\}$ and $d_i \in \{-2.0, -1.5, -1.0, -0.5, 0.0, +0.5, +1.0, +1.5, +2.0\}$.

### 4.2 Statistical Significance Testing
- **Parametric Test:** Two-sided Paired Student's t-test with $df = 99$:
  $$t = \frac{\bar{d}}{s_d / \sqrt{n}}$$
  Critical threshold: $\alpha = 0.05$ ($|t| \ge 1.9842$).
- **Non-Parametric Bootstrap:** 10,000 paired bootstrap resamples over the 100 opening pairs to generate empirical 95% confidence intervals on:
  - Mean points per pair $\bar{d}$
  - Total score percentage $S_{\%}$
  - Performance Elo difference $\Delta \text{Elo} = -400 \log_{10}(1 / S_{\%} - 1)$

---

## 5. Preregistered Decision Framework

Upon match completion, the milestone classification will follow the preregistered criteria:

| Category | Disposition | Criteria |
| :--- | :--- | :--- |
| **Category A** | **Promotion to Production** | Statistically significant strength improvement ($p < 0.05$, $t > 1.9842$), lower 95% bootstrap Elo bound $> 0.0$, 0 tactical regressions, 0 engine stalls/illegal moves. |
| **Category B** | **Neutral Retention / Experimental Flag** | Search tree compression demonstrated (fixed-depth nodes down $> 5\%$), no statistically significant strength regression ($p \ge 0.05$, score $\ge 48.0\%$). Retained behind UCI option for tactical scenarios. |
| **Category C** | **Rejection** | Statistically significant playing strength regression ($p < 0.05$, score $< 48.0\%$) or severe time-management deficit. |
| **Category D** | **Invalidated / Disqualified** | Engine crashes, illegal move generation, or tournament harness integrity violation. |

---

## 6. Execution Manifest
- **Runner Script:** `analysis/v0.56/tests/run_preregistered_match.py`
- **Output PGN:** `analysis/v0.56/pgn/n7_vs_n5.pgn`
- **Output Raw Telemetry:** `analysis/v0.56/raw/n7_vs_n5_raw.json`
- **Workers:** 8 concurrent processes
- **Preregistration Status:** **LOCKED & FROZEN PRIOR TO MATCH COMMENCEMENT**

