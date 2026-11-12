# Milestone P1.11 Strategic Architectural Decision & Future Roadmap

## 1. Executive Context & The Classical Plateau

Across Milestones P1.8 through P1.11, Project Janus has exhaustively explored handcrafted classical chess enhancements:
- Positional evaluation terms (E5 $\to$ E10 $\to$ E11 $\to$ E15) adding mobility, king safety, pawn structure, and outpost bonuses.
- Search ordering heuristics (M0 $\to$ M2 countermove, staged movegen, continuation histories H1–H3).
- Selective pruning (Reverse Futility Pruning, Null Move Pruning, Late Move Pruning, Quiescence SEE).
- Concurrency scaling (Lazy SMP reaching 4.43M NPS on 4 threads).

Despite these advances, the competitive tournament evidence yields an inescapable conclusion:
**Handcrafted classical chess engines without automated numerical optimization reach an empirical strength plateau.**
Every handcrafted evaluation term introduces non-linear interactions with search selectivity. In X7 and X12, simpler terms produced higher effective node speed and deeper tactical horizons that human intuition cannot surpass by adding more manual rules.

---

## 2. Strategic Architectural Recommendations

To break through this plateau and achieve genuine competitive gains in subsequent milestones, the following strategic directions are recommended:

### Direction 1: Automated Classical Parameter Optimization (SPSA / Texel Tuning)
- **Problem:** Janus currently utilizes manually estimated piece-square tables, mobility curves, and pruning margins ($120\times d, 90\times d, 40\times d$). These values are suboptimal and miscalibrated across diverse positions.
- **Solution:** Implement an automated **Simultaneous Perturbation Stochastic Approximation (SPSA)** tuning harness or Texel logistic regression tuning on quiet positions.
- **Charter Compliance:** SPSA tunes the *classical handcrafted weights* without introducing neural networks, staying strictly compliant with non-ML mandates if defined as classical parameter optimization.

### Direction 2: Architectural Decoupling: Lean 1T vs Parallel 4T
- **Problem:** Attempting to maintain a single unified engine binary with conditional branches creates code bloat and cache penalties for single-threaded play (where X7 outperformed X16 by +117 Elo).
- **Solution:** Formally bifurcate the engine development tracks:
  1. **Janus Classical Lean (1T):** Stripped-down, branch-free, ultra-fast tactical engine focused purely on NPS depth maximization.
  2. **Janus Classical SMP (Multicore):** Full Lazy SMP architecture with thread-local pawn caches, dynamic time allocation, and sophisticated history dampening.

### Direction 3: Real Endgame Tablebase Deployment
- **Problem:** In Milestones P1.9 through P1.11, tablebase probing remained classified as "Adapter and Fallback Verified Only" because no `.rtbw` or `.rtbz` files existed on disk.
- **Solution:** Provision a dedicated 3-4-5 piece Syzygy tablebase repository, verify real runtime WDL/DTZ probing, and measure true endgame conversion gains under tournament conditions.

### Direction 4: Multi-ply Threat-Aware Pruning
- **Problem:** LMR over-prunes defensive lines because it cannot distinguish between quiet passive moves and quiet defensive refutations.
- **Solution:** Implement quiet threat detection (detecting opponent checks or tactical threats at root) to conditionally bypass LMR, extending the Direction A concepts proven in P1.11.

---

## 3. Decision Matrix for Subsequent Milestones

| Architecture Proposal | Feasibility | Expected Strength Gain | Non-ML Compliance | Recommended Priority |
| :--- | :--- | :--- | :--- | :--- |
| **SPSA Parameter Tuning** | High | +40 to +70 Elo | Full (Classical weights) | **Priority 1 (Highest)** |
| **Bifurcated 1T/4T Binaries** | High | +30 to +50 Elo (on 1T) | Full | **Priority 2** |
| **Real Syzygy 5-man Files** | Medium | +15 to +25 Elo | Full | **Priority 3** |
| **Quiet Threat Detection** | Medium | +10 to +20 Elo | Full | **Priority 4** |
| **NNUE Hybridization** | High | +500 to +700 Elo | Violates Current Charter | **Deferred to Phase 2** |
