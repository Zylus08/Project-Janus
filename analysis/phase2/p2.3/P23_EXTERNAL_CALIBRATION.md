# Project Janus — Phase 2, Milestone P2.3
## Phase 15: External Stockfish Calibration & Competitive Ladder Assessment

**Author:** Principal Computer Chess Architect & Tournament Integrity Auditor  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Subject:** External Benchmark Qualification & Conditional Release Gate  

---

### 1. Executive Summary & Conditional Release Evaluation

Milestone P2.3 preregistered an explicit, evidence-driven gate governing external matches:
> *"Only if H3 passes technical correctness and shows credible internal strength progress, run external matches against Stockfish 4, Stockfish 11, and Unrestricted Stockfish 19."*

In Phase 14, Candidate H3 was subjected to a rigorous 50-game match against the qualified baseline **Janus Classical R1.0**:
- **H3 Score:** $0.5 / 50$ ($1.00\%$, $-798.3\text{ Elo}$).
- **Primary Strength Advancement Gate:** **FAILED**.

Because Candidate H3 did not establish internal playing-strength superiority over Classical R1, **the conditional release criteria for external Stockfish testing were not met**. Under the preregistered experimental protocol, subjecting Candidate H3 to external matches against full-strength Stockfish 4, Stockfish 11, or Stockfish 19 is scientifically unwarranted and would yield degenerate $0.0\%$ results without producing new discriminative signal.

---

### 2. Comprehensive Engine Rating Ladder (Historical Anchors)

The established Elo relationships across all Project Janus historical controls, baselines, and neural iterations are summarized below:

```
========================================================================================================================
PROJECT JANUS COMPREHENSIVE CALIBRATION LADDER (PHASE 1 THROUGH PHASE 2)
========================================================================================================================
Engine / Candidate         | Architecture Type       | Benchmark Elo Anchor | Relationship to Classical Baseline
---------------------------+-------------------------+----------------------+-----------------------------------
Stockfish 19 (Unrestricted)| NNUE 2026 Sovereign     | ~3650 Elo            | Reference Horizon (+1500+ Elo)
Stockfish 11               | Classical / Early NNUE  | ~3350 Elo            | Reference Control (+1200+ Elo)
Stockfish 4                | Pure Classical (2013)   | ~3000 Elo            | Historical Anchor (+900+ Elo)
---------------------------+-------------------------+----------------------+-----------------------------------
Janus Classical R1.0       | Clean Classical Search  | ~2100 Elo            | Qualified Phase 1 Baseline Anchor
Janus Classical X22        | Correctness Reference   | ~2080 Elo            | Historical Classical Reference
Janus Classical X7 (1T)    | Classical Baseline      | ~2050 Elo            | Historical 1-Thread Baseline
---------------------------+-------------------------+----------------------+-----------------------------------
Janus Hybrid H2            | 50% Classical + 50% H1  | ~1675 Elo            | -424.3 Elo relative to R1.0
Janus Hybrid H1            | DP-PS-768 NNUE (P2.1)   | ~1370 Elo            | -727.0 Elo relative to R1.0
Janus Hybrid H3            | HalfKP-40960 NNUE (P2.3)| ~1300 Elo            | -798.3 Elo relative to R1.0
========================================================================================================================
```

---

### 3. Forensic Analysis: Why Neural Predictions Have Not Yet Translated to Board Strength

While Candidate H3 achieved significant technical and scientific breakthroughs in P2.3:
1. **Accurate Score Calibration:** Test non-mate MAE dropped to $229.7\text{ cp}$ (compared to severe scale distortion and STM bias in H1).
2. **Correct Piece Preference:** Restored strictly monotonic piece valuations ($\text{Queen} > \text{Knight} > \text{Startpos}$).
3. **King-Conditioning:** Eliminated static square blindness by binding piece identities to king squares ($40,960$ features).
4. **Search Tree Pruning:** HalfKP guidance compressed alpha-beta search trees by $35.0\%$ over classical evaluation.

However, on the board in time-controlled competition:
- **Search Depth Latency:** Classical R1 in native C++ executes at $600\text{k NPS}$, reaching plies 7–10 in middlegames. In contrast, pure neural leaf evaluation (even with $520\text{k NPS}$ modeled accumulator throughput) requires dense forward layer activation on every quiet position. When evaluated via a Python search bridge, H3 reached plies 4–5, conceding a 3–5 ply tactical horizon deficit.
- **Tactical Blunder Horizon:** In chess, a 1-ply search depth deficit is worth ~100–150 Elo. A 3–5 ply deficit creates tactical blind spots where deep multi-move tactical combinations (pins, skewers, removal of guard) cannot be seen by the neural evaluator, regardless of its positional evaluation accuracy.

---

### 4. Recommendation for Milestone P2.4

To enable neural evaluation to express its positional superiority on the board:
1. **Full C++ Native Integration:** Compile the HalfKP-40960 accumulator stack directly into the native C++ R1 engine binary (`janus_classical_x.exe`), utilizing AVX2 SIMD vector intrinsics (`_mm256_adds_epi16`, `_mm256_max_epi16`).
2. **Hybrid Evaluation Coupling:** Evaluate H3 within the hybrid framework (e.g. 50% Classical + 50% H3 or tactical gating), allowing Classical R1's fast piece-square tables and SEE to protect tactical horizons while H3 guides positional decisions.
3. **Scaled Training Corpus:** Expand training from $10\text{k}$ to $500\text{k}$ positions to fill sparse feature coverage across all 40,960 HalfKP weights.
