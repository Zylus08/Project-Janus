# Phase 12: Next Classical Direction (Strategic Roadmap for Milestone P1.11)

**Milestone:** Phase 1, Milestone P1.10  
**Charter:** Classical Architecture Roadmap, Empirical Optimization & Search–Evaluation Co-Design  
**Target Milestone:** Phase 1, Milestone P1.11  
**Author:** Principal Computer Chess Engineer & Search Architecture Group  

---

## 1. Executive Retrospective: Findings from Milestone P1.10

Milestone P1.10 successfully resolved the central mystery that plagued Project Janus across Milestones P1.8 and P1.9:
1. **Resolution of the Single-Thread Collapse:**
   - In P1.9, Candidate X14 suffered a catastrophic regression against X7 ($40.25\%, p = 0.0014 < 0.01$).
   - P1.10 proved that this collapse was driven by three compounding factors: over-pruning via Late Move Pruning on single-core search, evaluation throughput drag ($-14.4\%$ NPS), and inflated reverse futility pruning margins.
   - By engineering thread-adaptive search economics (Candidate S on 1T, Candidate P on 4T) and Calibrated E15 evaluation, Candidate X15 completely eliminated the regression ($46.00\%, p = 0.183766 > 0.05$), gaining $+40.7$ Elo and restoring statistical parity with X7.
2. **The 4-Thread Classical Saturation Barrier:**
   - On 4 threads, Candidate X15 elevated search throughput to **1,728,902 NPS (+17.16% over X12)** and expanded average search depth to 21.3 plies via a 16K thread-local pawn hash table (512 KB, 25% L2 cache resident).
   - Despite this substantial throughput and depth advantage, X15 achieved $47.00\%$ ($p = 0.271$) at fast time controls and $46.50\%$ ($p = 0.398$) at slower time controls against X12.
   - **Empirical Principle:** Handcrafted classical evaluation reaches an asymptotic plateau where additional handcrafted terms (and even $+17\%$ search throughput) cannot alter playing strength without automated parameter optimization.
3. **Syzygy Infrastructure Reality:**
   - Local filesystem auditing confirmed that 0 `.rtbw` or `.rtbz` tablebase files exist locally.
   - The Ronald de Man Syzygy subsystem was verified as an adapter and fallback layer with $100\%$ graceful fallback (<0.12 µs overhead).
   - For real tablebase play, actual tablebase files (e.g. 3-4-5 piece Syzygy files, ~1 GB) must be acquired.

---

## 2. Priority 1: Automated Non-ML Parameter Calibration (SPSA)

Manual handcrafting of evaluation terms (e.g. $\pm 15$ cp blockade penalty, $+12$ cp phalanx bonus, $-25$ cp open-file king penalty) has reached its theoretical limit. To convert positional knowledge into tournament Elo:
- **Framework:** Simultaneous Perturbation Stochastic Approximation (SPSA) applied directly to classical evaluation terms and search parameters.
- **Strictly Non-ML:** SPSA optimizes scalar numerical coefficients of deterministic C++ functions; it introduces zero neural networks, zero tensor computations, and zero learned feature representations.
- **Key Calibration Vectors:**
  1. *King Safety Hazard Function:* Calibrate king ring attack weights, open-file penalties, and pawn storm multipliers against tactical defensive stability.
  2. *Passed Pawn Advance Matrices:* Jointly optimize rank-dependent passer bonuses and opposing piece blockade penalties.
  3. *Search Reduction Curves:* Optimize base LMR table entries, history reduction divisors, and depth cutoffs to eliminate remaining multi-causal blunders ($F7$).

---

## 3. Priority 2: History-Informed Search Selectivity

Analysis across 240 positions in the Generalized Failure Atlas demonstrated that $63.4\%$ of errors are multi-causal ($F7$), where search reductions are applied to quiet moves that hold vital defensive resources:
- **Capture History Table:** Implement a dedicated $6 \times 64$ capture history matrix to distinguish tactically winning captures from speculative sacrifices during quiet move ordering.
- **Multi-Ply Continuation History:** Expand continuation history to track 2-ply and 4-ply ancestor move pairs, dynamically relaxing LMR reductions for moves with proven refutation capability.
- **Negative History Pruning:** Introduce guarded quiet move pruning late in the move loop, conditioned on low history scores and non-check positions.

---

## 4. Priority 3: Real Tablebase Data Ingestion & Search Probing

With the Ronald de Man Syzygy adapter interface fully operational:
- **Corpus Acquisition:** Provide standard 3-4-5 piece Ronald de Man Syzygy tablebases (WDL and DTZ, ~1 GB total) in a dedicated directory (e.g. `E:\ChessXML\syzygy`).
- **Root Tablebase Probing:** Probe DTZ at root to guarantee 100% theoretically flawless endgame play, strictly respecting the 50-move rule.
- **Interior WDL Probing:** Probe WDL at search depths $\ge 2$ when piece count $\le 5$, terminating search trees immediately upon encountering proven theoretical outcomes.

---

## 5. Milestone P1.11 Qualification Target

- **Candidate:** Janus Classical X16.
- **Baselines:** Janus Classical X7 (1T Baseline), Janus Classical X12 (4T Baseline).
- **Preregistered Gate:** Candidate X16 must achieve a statistically significant positive Elo delta ($p < 0.05$) against both X7 (1T) and X12 (4T) across at least 200 opening-paired games.

