# Janus Classical X18: Performance Against Historical Classical References
**Milestone:** Phase 1, Milestone P1.13  
**Date:** November 13, 2026  
**Auditor:** Independent Reproducibility Auditor & Historical Chess Engine Specialist  
**Governing Standard:** JCTS v2 Classical Testing Protocol  
**Candidate Under Audit:** Janus Classical X18  
**Reference Engines Tested:** Stockfish 4 (2013), Stockfish 11 (2020)  
**Compilation Target:** Unrestricted Native x86-64 MSVC binaries (Strictly Classical Non-ML)  

---

## 1. Scope & Objective

The objective of Tier 2 historical benchmarking is to measure Project Janus not against modern neural network or NNUE systems, but against the historical progression of non-ML classical chess engines.

By testing Janus against:
1. **Stockfish 4 (SF4, 2013):** A foundational classical engine featuring early Lazy SMP, king safety, basic evaluation terms, and elementary LMR.
2. **Stockfish 11 (SF11, 2020):** The absolute historical peak of handcrafted classical chess programming before the NNUE revolution, embodying 12+ years of community evaluation tuning, complex continuation histories, multi-cut pruning, and probabilistic search selectivity.

we quantify the exact historical epoch corresponding to Janus's current playing strength.

---

## 2. Match Telemetry & Statistical Results

### 2.1 Match 4: Historical Classical Entry Hurdle (`x18_1t_vs_sf4_1t`)
* **Engines:** Janus-X18-1T vs Stockfish-4-1T
* **Time Control:** 1.5s base + 50ms increment per move
* **Openings:** 20 balanced opening pairs (40 games total)
* **Hash Allocation:** 64 MB per engine
* **Threads:** 1

| Metric | Measured Value | Standard Formulation / Confidence Interval |
| :--- | :--- | :--- |
| **Wins (X18)** | 1 | 2.5% |
| **Draws** | 1 | 2.5% |
| **Losses (X18)** | 38 | 95.0% |
| **Total Points (X18)** | 1.5 / 40 | **3.75%** |
| **95% Wilson Score Interval** | **[0.87%, 14.73%]** | Normal approximation with continuity correction |
| **Elo Difference ($\Delta\text{Elo}$)** | **$-563.75$** | Logistic Elo: $-400 \log_{10}(1/S - 1)$ |
| **Elo 95% Confidence Bounds** | **$[-822.52, -304.98]$** | Wilson score bound inversion |

#### Pentanomial Breakdown (20 Opening Pairs):
* **WW:** 0 pairs
* **WD:** 0 pairs
* **DD / WL:** 1 pair (Pair 13: Game 25 won by X18, Game 26 won by SF4)
* **LD:** 1 pair (Pair 16: Game 31 drawn, Game 32 won by SF4)
* **LL:** 18 pairs

#### Notable Games:
* **Game 25 (1-0 Win):** Janus-X18-1T (White) vs Stockfish-4-1T (Black), ECO A80 (*Dutch Defense, Krejcik Gambit*). X18 exploited SF4's delayed king castling through early queenside piece activation, maintaining an evaluation advantage that crossed $+5.00$ at ply 84, triggering an authentic eval-resignation adjudication at ply 92.
* **Game 31 (1/2-1/2 Draw):** Janus-X18-1T (White) vs Stockfish-4-1T (Black), ECO A53 (*Old Indian Defense, 3.Nc3*). X18 held a balanced rook-and-pawn endgame through active rook defense, reaching the 160-ply adjudication limit without conceding material.

---

### 2.2 Match 5: Historical Classical Peak Ceiling (`x18_1t_vs_sf11_1t`)
* **Engines:** Janus-X18-1T vs Stockfish-11-1T
* **Time Control:** 1.5s base + 50ms increment per move
* **Openings:** 20 balanced opening pairs (40 games total)
* **Hash Allocation:** 64 MB per engine
* **Threads:** 1

| Metric | Measured Value | Standard Formulation / Confidence Interval |
| :--- | :--- | :--- |
| **Wins (X18)** | 0 | 0.0% |
| **Draws** | 0 | 0.0% |
| **Losses (X18)** | 40 | 100.0% |
| **Total Points (X18)** | 0.0 / 40 | **0.00%** |
| **95% Wilson Score Interval** | **[0.00%, 8.76%]** | Clopper-Pearson / Wilson upper bound |
| **Clopper-Pearson 95% Upper Bound** | **$p < 0.0876$** | Exact binomial confidence bound for zero successes |
| **Elo Difference ($\Delta\text{Elo}$)** | **Undefined (Zero Score)** | Finite representation is mathematically prohibited |
| **Conservative Elo Upper Bound** | **$\Delta\text{Elo} < -407.03$** | Derived from $p = 0.0876$: $-400 \log_{10}(1/0.0876 - 1)$ |

#### Pentanomial Breakdown (20 Opening Pairs):
* **LL:** 20 pairs (100.0%)

*Interpretation:* Stockfish 11 represents a complete playing-strength barrier for Janus X18. Across 40 games, X18 was unable to secure a single draw, demonstrating that the gap between Janus and peak classical engines is absolute.

---

## 3. Comparative Gap Analysis: Janus Classical vs Historical Stockfish Ladder

Combining the results of the reference calibration tournament (Phase 1) with the candidate tournament (Phase 12), we construct the comprehensive non-ML classical strength ladder:

| Engine | Version / Epoch | Estimated Elo (Scale: SF4 = 2800) | Head-to-Head Score vs Janus | Dominant Architectural Advantages Over Janus |
| :--- | :---: | :---: | :---: | :--- |
| **Stockfish 11** | 2020 (Peak Classical) | ~3450 | **100.0%** (40–0–0) | Multi-ply continuation history, multi-cut pruning, singular extensions, 200+ Texel-tuned evaluation terms |
| **Stockfish 8** | 2016 | ~3250 | **92.5%** (calibration) | Advanced pawn storm evaluation, refined piece-square tables, sophisticated fail-high reductions |
| **Stockfish 6** | 2015 | ~3100 | **90.0%** (calibration) | Threat detection in move ordering, null-move verification, king safety zone tables |
| **Stockfish 4** | 2013 | ~2800 | **96.25%** (38–1–1) | Standard piece-square tables, basic LMR, alpha-beta root search |
| **Janus X18-1T** | 2026 (Candidate) | ~2236 | — | Elementary History-LMR, material + simple PST, basic killer heuristics |
| **Janus X7-1T** | 2026 (Qualified) | ~2300 | **59.0%** vs X18 | Safe uniform LMR, material + simple PST, stable killer heuristics |

### Architectural Factors Explaining the Gap:
1. **Move Ordering Selectivity:**  
   As established in our pipeline profiling (Phase 2), Stockfish 11 achieves effective branching factor $b_{\text{eff}} \approx 1.4\text{--}1.8$, searching 8× to 28× fewer nodes to reach the same nominal depth. Janus operates at $b_{\text{eff}} \approx 2.4\text{--}3.1$.
2. **Quiet Tactical Verification:**  
   Stockfish 11 never prunes quiet moves with negative history if they are checks, threats, or past-two-ply continuations. Janus X18's heuristic blindly pruned quiet moves at $H < -2000$, conceding early tactical concessions against SF4 and SF11.
3. **Pawn Structure & King Safety Diagnostics:**  
   Even SF4 possesses sophisticated king-danger tables that reward attacking pieces aimed at king flight squares. Janus's static evaluation remains primarily dominated by raw material and static piece-square tables.

---

## 4. Conclusion
Janus Classical X18 has not bridged the historical gap to Stockfish 4, and remains outclassed by Stockfish 11. The historical calibration confirms that Janus's true developmental peer group lies in early 2000s classical engines, and that architectural progress requires principled continuation-history frameworks rather than static cutoff heuristics.
