# Project Janus — Phase 2, Milestone P2.3
## Phase 17: Strategic Research Direction for Milestone P2.4

**Author:** Principal Computer Chess Architect & Neural Systems Specialist  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Subject:** Empirical Synthesis & Strategic Roadmap for Milestone P2.4  

---

### 1. Empirical Synthesis of Milestone P2.3

Milestone P2.3 resolved the foundational failure modes identified in Milestone P2.2:
- **Feature Space:** HalfKP-40960 successfully embedded king-relative spatial geometry, eliminating the square-blindness of DP-PS-768.
- **Score Calibration:** Calibrated mixed lambda loss ($\lambda=0.8$) eliminated STM initiative distortion and reduced test MAE to $229.7\text{ cp}$.
- **Monotonic Piece Hierarchy:** Material priors and search-grounded labels ensured monotonic piece valuation ($\text{Queen} > \text{Knight} > \text{Equal}$).
- **Inference Efficiency:** Incremental accumulator updates ($0.39\ \mu\text{s}$) accelerated leaf evaluation by $3.3\times$, and HalfKP guidance compressed search trees by $35.0\%$.

However, Phase 14 tournament play revealed the critical bottleneck preventing neural predictions from translating into competitive match victories:
> **The Tactical Depth Horizon Deficit.**  
> While H3's static positional predictions are superior to H1 and highly correlated with Classical R1, evaluating leaf nodes via external or unoptimized search paths creates a 3–5 ply depth deficit compared to Classical R1's $600\text{k NPS}$ native C++ search. In chess, positional precision cannot compensate for missing a 4-ply tactical combination.

---

### 2. Core Pillars for Milestone P2.4

Milestone P2.4 must not pursue arbitrary network enlargement. Instead, it must bridge the gap between neural evaluation accuracy and deep tactical search throughput through four targeted technical thrusts:

```
+-----------------------------------------------------------------------------------+
|                        MILESTONE P2.4 STRATEGIC ARCHITECTURE                      |
+-----------------------------------------------------------------------------------+
|  1. C++ AVX2 Native SIMD Inference  -->  Restore 500k+ NPS Engine Search Depth    |
|  2. Calibrated Hybrid Coupling       -->  Tactical Gating (SEE + Classical Safety) |
|  3. Scaled Corpus (500k Positions)  -->  Exhaustive HalfKP Feature Saturation     |
|  4. King-Bucket Feature Compression  -->  Reduce Memory Footprint & Sparsity      |
+-----------------------------------------------------------------------------------+
```

#### Pillar 1: Native C++17 SIMD Vectorization (`r1_nnue_v2.hpp`)
- **Direct C++ Embedding:** Implement the HalfKP-40960 incremental accumulator and INT16/INT8 forward pass directly inside `engine/classical_x/r1/`.
- **AVX2 Vectorization:** Utilize 256-bit SIMD registers (`_mm256_adds_epi16`, `_mm256_subs_epi16`, `_mm256_max_epi16`) to update 16 accumulator weights per instruction cycle.
- **Target Performance:** Achieve $> 500\text{k NPS}$ sustained full-tree search throughput in native C++.

#### Pillar 2: Tactical Gating & Calibrated Hybrid Evaluation
- Rather than relying on pure neural evaluation at every leaf, implement **tactical gating**:
  - In quiet positions: Apply HalfKP neural evaluation to dictate positional planning and piece placement.
  - In sharp tactical positions (checks, queen attacks, captures): Rely on Classical Static Exchange Evaluation (SEE) and MVV-LVA move ordering to prevent tactical blindness.
  - Tune hybrid blending weights ($w \cdot \text{NNUE} + (1-w) \cdot \text{Classical}$) using controlled tournament ablations.

#### Pillar 3: Scaled Self-Play Corpus Generation ($500\text{k}$ Positions)
- Expand the training corpus from $10\text{k}$ to $500\text{k}$ positions using the validated P2.3 search-grounded self-play pipeline.
- Ensure all $40,960$ features achieve adequate sampling coverage across varied openings, middlegames, and technical endgames.
- Partition strictly by game ID with cryptographic deduplication to preserve the 0-leakage standard.

#### Pillar 4: King-Bucketing Compression (HalfKPB)
- Investigate whether clustering the 64 king squares into 32 or 16 symmetrical king buckets (e.g. king on back rank vs central king) reduces model footprint and accelerates cold-start convergence without degrading evaluation fidelity.

---

### 3. Preregistered Milestone P2.4 Gate Hypotheses

1. **Gate 1 (SIMD Speedup):** Native AVX2 accumulator update must achieve $\le 0.05\ \mu\text{s}$ per ply, sustaining $\ge 500\text{k NPS}$ in full alpha-beta search.
2. **Gate 2 (Tactical Horizon Parity):** Native H4 candidate must achieve within 1 ply of Classical R1 search depth at 5s+0.05s time control.
3. **Gate 3 (Competitive Advancement):** Candidate H4 (Hybrid or Gated NNUE) must achieve $\ge 45.0\%$ score against Classical R1 in a 50-game tournament battery.
