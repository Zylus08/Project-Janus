# Project Janus — Phase 2, Milestone P2.2
## Phase 15: Milestone P2.3 Strategic Direction & Technical Roadmap

**Author:** Principal Computer Chess Architect, Systems Engineer & Research Lead  
**Milestone:** P2.2 — Neural Evaluation Failure Forensics, Score Calibration & Scalable Dataset Readiness  
**Date:** 2026-11-16  
**Subject:** Empirical Roadmap & Prerequisite Action Items for Milestone P2.3  

---

### 1. Executive Summary & Strategic Rationale

Milestone P2.2 has definitively established the causal factors behind Janus H1's playing strength deficit:
1. **Feature Representation:** DP-PS-768 is strictly linear in piece placement; it cannot encode king shelter, open king files, or attacking geometry.
2. **Training Objective:** Pure game-outcome BCE loss on $49.5\%$ drawn positions compresses output logits by $4\times$ to $10\times$, introduces an uncalibrated $+52\text{ cp}$ side-to-move bias, and distorts the piece value hierarchy ($Q < N$).
3. **Runtime Bottleneck:** Search bypassed incremental updates by executing full scratch recomputations (`evaluate_full`) at every leaf node, suffering a $6\times$ latency penalty.
4. **Hybrid Contamination:** Blending flawed neural evaluations into Classical R1 (Hybrid H2) degrades playing strength by $-424\text{ Elo}$.

Based on this evidence, Milestone P2.3 will execute a focused, four-pillar architectural upgrade.

---

### 2. The Four Pillars of Milestone P2.3

```
+-----------------------------------------------------------------------------------+
|                         MILESTONE P2.3 EXECUTION PILLARS                          |
+-----------------------------------------------------------------------------------+
|  PILLAR 1: FEATURE ARCHITECTURE EXPANSION                                         |
|  - Transition from DP-PS-768 to Standard HalfKP-40960 (40,960 features).          |
|  - Index non-king pieces jointly with the friendly king square coordinate.        |
|  - Enable direct learning of pawn shields, king safety, and tactical threats.    |
+-----------------------------------------------------------------------------------+
|  PILLAR 2: DATASET SCALING WITH SEARCH-SCORE GROUNDING                            |
|  - Deploy the verified Phase 10 self-play pipeline to generate 20,000 games       |
|    (~500,000 quality-controlled positions).                                       |
|  - Ground training labels with depth-searched centipawn evaluations.              |
+-----------------------------------------------------------------------------------+
|  PILLAR 3: LAMBDA-LOSS TRAINING OBJECTIVE                                         |
|  - Optimize with blended loss: 0.8 * MSE(eval, teacher) + 0.2 * BCE(eval, result).|
|  - Center Startpos score at 0.0 cp and enforce monotonic piece valuation.         |
|  - Train with cosine learning-rate decay across 25 epochs.                        |
+-----------------------------------------------------------------------------------+
|  PILLAR 4: C++ SEARCH ACCUMULATOR STACK OPTIMIZATION                              |
|  - Wire Accumulator array into SearchStackEntry along the recursive search tree.  |
|  - Replace evaluate_full() (7.5 us) with O(1) incremental update_move() (0.1 us).|
|  - Elevate neural search throughput from 100k NPS to > 500k NPS.                 |
+-----------------------------------------------------------------------------------+
```

---

### 3. Step-by-Step Milestone P2.3 Work Plan

1. **Phase 2.3.1 (Engine & Accumulator Stack Optimization):**
   - Add `Accumulator stack[MAX_SEARCH_PLY]` to `R1SearchCore`.
   - Update `make_move` in search to call `update_move()` incrementally.
   - On friendly king moves, execute friendly perspective refresh; maintain enemy perspective incrementally.
2. **Phase 2.3.2 (Self-Play Generation Campaign):**
   - Execute `generate_self_play_dataset.py` to produce $500,000$ positions across $20,000$ games.
   - Partition strictly by game ID into Train ($400\text{k}$), Val ($50\text{k}$), Test ($50\text{k}$).
3. **Phase 2.3.3 (HalfKP-40960 Model Architecture & Training):**
   - Define PyTorch HalfKP-40960 $\to 128 \times 2 \to 32 \to 1$ network ($5.25\text{M}$ parameters, $10\text{ MB}$).
   - Train using Lambda-Loss with cosine decay.
   - Quantize to INT16 accumulators and INT8 weights.
4. **Phase 2.3.4 (Candidate Freeze & Correctness Gates):**
   - Export header and binary weights: `janus_nnue_h3.bin`.
   - Pass all 12 formal correctness gates with $100\%$ mathematical parity.
5. **Phase 2.3.5 (Independent Playing Strength Qualification):**
   - Execute 100-game match: **H3 (NNUE) vs Classical R1.0**.
   - Execute 100-game match: **H3 (NNUE) vs Frozen H1**.
   - Target: Demonstrate statistically verified playing-strength parity or advancement over Classical R1 ($p < 0.05$).

---

### 4. Readiness Summary

Milestone P2.2 has completed all forensic investigations, resolved all theoretical contradictions, and eliminated all blind alleys. 
Project Janus is now fully prepared to initiate **Milestone P2.3: HalfKP-40960 Architecture, Search Accumulator Optimization & Strength Qualification**.
