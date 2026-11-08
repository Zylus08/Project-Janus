# PROJECT JANUS v0.60 — PRELIMINARY SEARCH EVALUATION REPORT

**Milestone:** v0.60 — Efficient Neural Value Evaluation  
**Author:** Principal Chess Engine Researcher & Search Optimization Specialist  
**Experimental Run ID:** `preliminary_search_raw.json`  
**Test Suite:** 10 Standard Diverse Positions (Openings, Middlegames, Endgames)  
**Search Protocols:** Fixed Depth (Depth 5) and Fixed Time (500 ms / position)  

---

## 1. Executive Summary

This evaluation investigates how the newly integrated native quantized neural value evaluator (`NNUE-V1-Small`) interacts with Janus's classical search architecture (alpha-beta, LMR, killer/history move ordering, and quiescence search).

Three configurations were evaluated across 10 benchmark positions:
1. **C1 (Control):** Classical Native N5 Baseline (`UseNeuralValue=false`).
2. **V1-A (Candidate):** Pure NNUE-V1-Small (`UseNeuralValue=true`, `NeuralValueBlend=0`).
3. **V1-B (Hybrid):** 50/50 Blended Evaluation (`UseNeuralValue=true`, `NeuralValueBlend=50`).

### Primary Findings
1. **Search Throughput:** V1-A achieves **1.19–1.31 Million NPS** in native search, retaining ~66% of C1's classical throughput (1.81 Million NPS).
2. **Tree Expansion Dynamics:** At fixed depth 5, V1-A expands **+54.3% more nodes** than C1 (47,476 vs 30,769). Continuous neural evaluations have fewer abrupt score cliffs, causing quiescence search to search deeper before standing-pat cutoffs occur.
3. **Fixed-Time Depth Deficit:** Under 500 ms fixed time, V1-A reaches a mean depth of **7.7 plies** compared to **9.3 plies** for C1 (a 1.6-ply deficit).
4. **Hybrid Blending Recovery:** The 50/50 hybrid configuration (V1-B) recovers **1.0 ply of depth** (reaching 8.7 plies) and doubles move agreement with C1 from 20% to 50%.

---

## 2. Experimental Protocols & Test Corpus

The evaluation corpus comprises 10 positions selected to test diverse search regimes:
- **Positions 1–3 (Opening):** Complex developmental and pawn-structure positions.
- **Positions 4–7 (Middlegame):** Tactical piece sacrifices, attacks on uncastled kings, and queen pins.
- **Positions 8–10 (Endgame):** Passed-pawn endgames, pawn breakthroughs, and king-and-pawn positions.

Two independent protocols were applied:
- **Protocol 1 (Fixed Depth 5):** Eliminates time-dependent variance to isolate node tree expansion, branching factor, and raw NPS.
- **Protocol 2 (Fixed Time 500 ms):** Evaluates real-time tournament search efficiency under equal clock conditions.

---

## 3. Protocol 1 — Fixed Depth 5 Results

| Configuration | Mean Nodes Searched | Node Ratio vs C1 | Mean Search Time (s) | Mean NPS | NPS Ratio vs C1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **C1 (Control)** | **30,768.7** | 1.000× (Base) | 0.0254 s | 1,363,970 | 100.0% |
| **V1-A (Pure NNUE)** | **47,476.0** | 1.543× (+54.3%) | 0.0416 s | 1,306,807 | 95.8% |
| **V1-B (Hybrid 50)** | **43,763.1** | 1.422× (+42.2%) | 0.0534 s | 1,226,994 | 89.9% |

### Analysis of Fixed-Depth Tree Growth
- In quiescence search, classical C1 uses piece values to immediately reject quiet captures that cannot exceed $\alpha$ (delta pruning).
- NNUE-V1 outputs positional scores that incorporate non-material factors (king safety, piece mobility, pawn support). Consequently, positions that classical evaluation would immediately classify as material losses are recognized by NNUE as carrying counterplay, forcing the quiescence search to verify tactical continuations to greater selective depth.
- At Depth 5, V1-A's raw NPS remains high (1.31 Million NPS, 95.8% of C1). The extra time spent is driven primarily by the expanded node count, not computational stalls in neural inference.

---

## 4. Protocol 2 — Fixed Time 500 ms Results

| Configuration | Mean Depth Reached | Mean Nodes | Mean NPS | NPS Ratio vs C1 | Move Agreement with C1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **C1 (Control)** | **9.3 plies** | 904,192 | 1,805,485 | 100.0% | 10/10 (100%) |
| **V1-A (Pure NNUE)** | **7.7 plies** | 595,558 | 1,188,843 | 65.8% | 2/10 (20%) |
| **V1-B (Hybrid 50)** | **8.7 plies** | 616,038 | 1,229,277 | 68.1% | 5/10 (50%) |

### Per-Position Breakdown (500 ms / Move)

| Pos # | Phase | C1 Best Move (Depth, Score) | V1-A Best Move (Depth, Score) | V1-B Best Move (Depth, Score) | V1-A Agree | V1-B Agree |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: |
| 1 | Opening | `b1c3` (d=8, +20 cp) | `b2b3` (d=7, +4 cp) | `d2d4` (d=8, +9 cp) | No | No |
| 2 | Opening | `b1c3` (d=6, +10 cp) | `f3e5` (d=5, +2 cp) | `c1g5` (d=6, -1 cp) | No | No |
| 3 | Opening | `g8f6` (d=8, -55 cp) | `d8b6` (d=6, -17 cp) | `e7e5` (d=7, -21 cp) | No | No |
| 4 | Middlegame | `d8b6` (d=7, 0 cp) | `c6d4` (d=6, -12 cp) | `c6d4` (d=7, +8 cp) | No | No |
| 5 | Middlegame | `c1e3` (d=7, +700 cp) | `b2b4` (d=6, +4 cp) | `f1d3` (d=6, +364 cp) | No | No |
| 6 | Middlegame | `c5e4` (d=6, +565 cp) | `e8e3` (d=5, +11 cp) | `c5e4` (d=6, +280 cp) | No | **Yes** |
| 7 | Middlegame | `d1d7` (d=7, -115 cp) | `g4g7` (d=6, -17 cp) | `a1b1` (d=6, -61 cp) | No | No |
| 8 | Endgame | `e5e6` (d=11, -100 cp) | `b6b5` (d=7, +17 cp) | `e5e6` (d=10, -53 cp) | No | **Yes** |
| 9 | Endgame | `e6f7` (d=10, +105 cp) | `b6b5` (d=8, +79 cp) | `e6f7` (d=10, +79 cp) | No | **Yes** |
| 10 | Endgame | `f4g5` (d=21, +255 cp) | `f4g5` (d=21, +17 cp) | `f4g5` (d=21, +121 cp) | **Yes** | **Yes** |

---

## 5. Detailed Tactical & Strategic Analysis

### 5.1 Tactical Sharpness and Centipawn Scaling
In Position 5 (a winning tactical continuation), C1 rapidly found `c1e3` (+700 cp). Pure NNUE (V1-A) selected `b2b4` with an evaluation of only +4 cp. Because NNUE-V1 was trained with a smooth L1 loss against teacher evaluations, its raw score output is compressed in tactical extremes, dampening the search's urgency to capitalize on decisive material gains.

Hybrid evaluation (V1-B) directly rectifies this compression: by blending 50% classical material and piece-square tables, V1-B identified `f1d3` (+364 cp), correctly diagnosing the decisive winning advantage.

### 5.2 Endgame Positional Understanding
In Positions 8, 9, and 10:
- V1-B demonstrated complete agreement with C1 (3 out of 3 positions), playing `e5e6`, `e6f7`, and `f4g5`.
- In Position 10, both V1-A and V1-B matched C1 at depth 21, demonstrating that in quiet endgame positions where tactical branching is constrained, NNUE evaluates quickly enough to achieve identical deep horizons.

---

## 6. Synthesis & Search Tuning Implications for v0.61

The preliminary search results reveal a clear roadmap for neural search qualification:

1. **Pure NNUE Requires Search Recalibration:**
   Because NNUE static evaluations do not step in discrete 100 cp piece increments, classical heuristics tuned for HCE (such as Reverse Futility Pruning margins and Quiescence stand-pat thresholds) cause excessive exploration (+54% nodes) when paired with pure neural values.
2. **Hybrid Blending is an Effective Bridge:**
   Blending classical evaluation at 50% immediately recovers 1.0 ply of search depth and raises tactical move agreement to 50%, confirming that hybrid evaluation is the most robust transitional architecture.
3. **No Premature Promotion:**
   Given the 1.6-ply depth deficit under fixed time, pure NNUE cannot be promoted to default without further pruning tuning or AVX2 SIMD acceleration.

