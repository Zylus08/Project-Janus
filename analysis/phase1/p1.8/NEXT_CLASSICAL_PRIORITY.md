# PROJECT JANUS — PHASE 1, MILESTONE P1.8
## Next Classical Research Priorities (Milestone P1.9 Roadmap)

### 1. Executive Summary

Milestone P1.8 successfully demonstrated that co-designing expressive handcrafted classical evaluation with a 64B cache-line packed parallel search core produces a stronger multithreaded engine (**Janus Classical X13**), outscoring baseline X12 by +12 decisive games (+20.9 Elo) and scoring the project's first 2 draws against unrestricted Stockfish 19.

However, the empirical evidence from Match C (slower time controls) and Match SF (external benchmark) clearly demarcates the remaining classical bottlenecks. To continue closing the performance gap without violating the non-ML charter, Milestone P1.9 must address three critical architectural priorities.

---

### 2. Milestone P1.9 Core Priorities

#### Priority 1: Deterministic Syzygy Tablebase Integration (3–4–5 Piece WDL/DTZ)
- **Problem**: Diagnostic analysis in Phase 1 demonstrated that **25.0% of all engine failures (F6)** are endgame horizon and outcome errors. In Match SF, complex endgames require deep calculation that Stockfish avoids or resolves with instant evaluation precision.
- **Solution**: Implement native Syzygy tablebase probing (Fathom / Ronald de Man algorithm audited in Phase 5).
  - WDL probing in search at depths $\ge \text{SyzygyProbeDepth}$.
  - DTZ probing at root for instantaneous conversion of won endgames and guaranteed salvage of theoretical draws.
  - Zero machine learning; 100% deterministic mathematical retrograde analysis.

#### Priority 2: Simultaneous Perturbation Stochastic Approximation (SPSA) Calibration
- **Problem**: In Match C (3.0s time control), handcrafted evaluation weights exhibited diminishing returns. Human intuition in weighting evaluation features (e.g., passed pawn bonus vs. bishop pair vs. king attack units) contains inherent non-linear biases.
- **Solution**: Subject the 24 handcrafted evaluation parameters of E10 to large-scale SPSA optimization against grandmaster game collections and self-play matches.
  - Strictly non-ML: optimizes linear classical heuristics without neural networks or learned value functions.

#### Priority 3: Search Selectivity & History-Directed Pruning Refinement
- **Problem**: Single-thread throughput between X7 and X13 shows an ~8% NPS differential due to richer evaluation bitboard scans.
- **Solution**: Refine search pruning economics:
  - History-directed Late Move Reductions: scale reductions inversely with quiet history and continuation history score.
  - Extended Futility Pruning: prune moves at depths 1–3 when static evaluation plus maximum positional gain fails to reach alpha.
  - Capture-only search extensions on passed pawn pushes to the 7th rank.

---

### 3. Implementation Sequence for Milestone P1.9

```
+-------------------------------------------------------------------------------+
|                      MILESTONE P1.9 IMPLEMENTATION ROADMAP                    |
+-------------------------------------------------------------------------------+
|  Phase 1: Tablebase Subsystem Integration (Fathom tbprobe C++ port)           |
|  Phase 2: Tablebase Search Probing & Root Adjudication Logic                  |
|  Phase 3: SPSA Classical Evaluation Parameter Tuning Framework                |
|  Phase 4: History-Directed LMR & Extended Futility Search Engineering          |
|  Phase 5: Single-Thread and Multithreaded Strength Requalification            |
|  Phase 6: Matched Unrestricted Stockfish 19 Qualification                     |
+-------------------------------------------------------------------------------+
```
