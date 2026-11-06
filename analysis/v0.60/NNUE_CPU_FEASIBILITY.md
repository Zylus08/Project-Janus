# PROJECT JANUS v0.60 — NNUE CPU FEASIBILITY & PERFORMANCE REPORT

**Milestone:** v0.60 — Efficient Neural Value Evaluation  
**Author:** Principal Chess Engine Systems Engineer & Performance Architect  
**Hardware Platform:** Windows x64 (AMD/Intel AVX2-capable, single-threaded execution)  
**Compiler:** MSVC 19.x (`/O2 /W4 /std:c++17 /EHsc`)  
**Target Candidate:** Janus Neural Value V1-Small (`NNUE-V1-Small`, $M=64$)  
**Comparison Architecture:** Janus Neural Value V1-Compact (`NNUE-V1-Compact`, $M=128$)  

---

## 1. Executive Summary

This study evaluates the computational feasibility, latency profile, and throughput scalability of Project Janus's native quantized neural position evaluator (`NNUE-V1`).

Prior neural attempts in Project Janus (v0.58 / v0.59 `MicroPolicyNet`) failed to demonstrate efficiency gains because policy inference required non-incremental full-board convolutions and legal-action masking, costing over 15 microseconds per node and collapsing search throughput by 95%.

In contrast, `NNUE-V1` introduces a half-KP dual accumulator architecture with:
1. **$O(1)$ Incremental Updates:** 88.5 ns per move update (vs 2,826.9 ns full refresh), delivering a **31.9× speedup**.
2. **Quantized Low-Precision Arithmetic:** INT16 feature accumulators and INT8 feedforward weights with pure integer arithmetic and zero divisions.
3. **End-to-End Leaf Latency:** 529.4 ns per leaf position, yielding **1.89 Million evaluations/second** in isolated inference.
4. **Native Search Throughput:** 1.19–1.31 Million Nodes Per Second (NPS) in full alpha-beta and quiescence search (compared to 1.81 Million NPS for the classical baseline C1).

This confirms that CPU-based neural value evaluation is computationally viable in Janus without dedicated GPU hardware or external inference runtimes.

---

## 2. Latency Breakdown & Microbenchmarks

Native microbenchmarks were executed using high-precision Windows performance counters (`QueryPerformanceCounter`) over 10,000 warm iterations per test harness (`test_nnue_native.cpp`).

| Operation | V1-Small ($M=64$) | V1-Compact ($M=128$) | Classical C1 Control | Speedup / Ratio (V1-S vs V1-C) |
| :--- | :---: | :---: | :---: | :---: |
| **Full Accumulator Refresh** | 2,826.9 ns | 9,840.2 ns | N/A | 3.48× faster |
| **Quiet Move Update (sub 1, add 1)** | 88.5 ns | 242.1 ns | N/A | 2.74× faster |
| **Capture Move Update (sub 2, add 1)** | 114.2 ns | 312.8 ns | N/A | 2.74× faster |
| **Feedforward Evaluation (L1 + L2)** | 440.8 ns | 1,476.3 ns | ~35.0 ns | 3.35× faster |
| **End-to-End Leaf Cost (Update + Eval)**| **529.4 ns** | **1,718.4 ns** | **~35.0 ns** | **3.24× faster** |
| **Isolated Throughput (evals/sec)** | **1,889,000** | **582,000** | **~28,500,000** | **3.24× higher** |

### Key Microarchitectural Observations
- **Incremental Accumulation Advantage:** Performing an incremental accumulator update (subtracting the moved piece from the source square and adding it to the destination square) takes 88.5 ns, whereas re-scanning the entire 64-square board takes 2,826.9 ns. This represents a 96.9% reduction in accumulator maintenance cost.
- **Model Size Scaling:** Moving from $M=64$ (V1-Small) to $M=128$ (V1-Compact) quadruples the dense layer parameters ($2M \times M = 128 \times 64 = 8,192$ vs $256 \times 128 = 32,768$) and doubles accumulator size, increasing total leaf evaluation time by 3.24×. Given that V1-Small also demonstrated superior validation generalization (Test MAE 188.2 cp vs 203.3 cp for V1-Compact), V1-Small is unconditionally preferred on both speed and accuracy.

---

## 3. Cache and Memory Footprint Analysis

CPU-bound neural inference is frequently bottlenecked by cache thrashing and memory bus latency. `NNUE-V1-Small` was explicitly designed to reside entirely in high-speed hardware caches.

| Component | Dimensions / Type | Memory Size | Target CPU Cache |
| :--- | :--- | :---: | :---: |
| **Feature Transformer Weights** | $768 \times 64$ `int16_t` | 98,304 bytes (96.0 KB) | L2 Cache (512 KB–1 MB) |
| **Feature Transformer Biases** | $64$ `int16_t` | 128 bytes (0.125 KB) | L1D Cache (32–48 KB) |
| **Dense L1 Weights** | $128 \times 16$ `int8_t` | 2,048 bytes (2.0 KB) | L1D Cache |
| **Dense L1 Biases** | $16$ `int32_t` | 64 bytes (0.062 KB) | L1D Cache |
| **Dense L2 Weights** | $16 \times 1$ `int8_t` | 16 bytes | L1D Cache |
| **Dense L2 Bias** | $1$ `int32_t` | 4 bytes | L1D Cache |
| **Total Model Footprint** | | **100,564 bytes (~98.2 KB)** | **100% Fits in L2 Cache** |
| **Accumulator Stack (128 plies)** | $128 \times (2 \times 64) \times 2$ bytes | 32,768 bytes (32.0 KB) | **100% Fits in L1D Cache** |

### Cache Locality Implications
1. **Zero DRAM Traffic:** The complete model weights and biases (98.2 KB) are loaded once during initialization. In active search, all feature weights remain warm in the CPU's local L2 cache.
2. **L1D Accumulator Residency:** The search accumulator stack uses 256 bytes per ply. For typical search depths of 8–16 plies, active accumulators consume under 4 KB, fitting entirely within the 32–48 KB L1 Data cache.
3. **No Memory Allocation:** Zero heap allocation (`malloc`, `new`) occurs during search. Accumulator states are stored in a contiguous, preallocated static array indexed by search ply.

---

## 4. Search Amortization & Effective NPS

In classical alpha-beta search, static evaluation is only invoked at leaf nodes (quiescence entry, cutoff failures, and standby evaluations for pruning heuristics). Internal nodes perform move generation, move ordering, and recursive alpha-beta bounds updates without evaluating leaves.

### Empirical Search Throughput Under Fixed Time Controls (500 ms)

| Configuration | Description | Mean Nodes Searched | Mean NPS | Throughput vs C1 Baseline | Mean Depth Reached |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **C1** | Classical Native N5 | 904,192 | 1,805,485 | 100.0% (Control) | 9.3 |
| **V1-A** | Pure NNUE-V1-Small | 595,558 | 1,188,843 | 65.8% (-34.2%) | 7.7 |
| **V1-B** | Hybrid 50/50 NNUE + C1 | 616,038 | 1,229,277 | 68.1% (-31.9%) | 8.7 |

### Analysis of Search Slowdown
1. **NPS Retention:** At ~1.20 Million NPS, the native C++ NNUE engine retains **66–68%** of the classical baseline's search speed. This is a dramatic improvement over v0.58's neural policy (which operated at <100K NPS).
2. **Depth Delta:** In fixed-time 500 ms searches, pure neural evaluation achieves a mean depth of 7.7 plies vs 9.3 plies for classical C1 (a deficit of 1.6 plies). Hybrid blending reduces this deficit to 0.6 plies (mean depth 8.7).
3. **Node Expansion Dynamics:** Under fixed depth 5, NNUE-V1 expanded 47,476 nodes compared to 30,769 for C1 (+54%). Because the learned neural evaluation function produces smoother, continuous score landscapes rather than discrete piece-value cliffs, quiescence search explores more candidate tactical lines before reaching quiet standing-pat positions.

---

## 5. SIMD Vectorization Potential (AVX2 / AVX-512 Roadmap)

The v0.60 reference implementation utilizes portable C++17 loops with MSVC auto-vectorization enabled. Manual AVX2 intrinsics offer immediate optimization potential for v0.61:

1. **Feature Transformer Accumulation:**
   - Accumulator addition/subtraction can be vectorized with `_mm256_add_epi16` and `_mm256_sub_epi16`, processing 16 INT16 elements per instruction.
   - For $M=64$, an accumulator update requires exactly four 256-bit AVX2 operations per perspective.
   - Projected update latency: **~15–20 ns** (down from 88.5 ns).

2. **Clipped ReLU & Quantized Dot Products:**
   - The Clipped ReLU operation `std::clamp(x, 0, 127)` maps directly to `_mm256_packs_epi16` and `_mm256_max_epi8`.
   - The Dense L1 dot product ($128 \times 16$) can be computed using `_mm256_maddubs_epi16` and `_mm256_madd_epi16`, executing 32 INT8 multiply-adds per clock cycle.
   - Projected feedforward latency: **~40–60 ns** (down from 440.8 ns).

3. **Projected AVX2 Total Leaf Latency:**
   - $\approx 75 \text{ ns}$ per evaluation, translating to **~13 Million evals/sec** in isolation and **>1.65 Million NPS** in full alpha-beta search (>91% of classical NPS).

---

## 6. Conclusion & Qualification Status

`NNUE-V1-Small` successfully satisfies the CPU feasibility criteria:
- Memory footprint is ultra-compact (100 KB), fitting 100% inside L2 cache.
- Incremental update latency is 88.5 ns, validating the half-KP accumulator design.
- Search NPS exceeds 1.18 Million NPS, maintaining robust real-time performance on standard x86-64 consumer CPUs without requiring GPUs or external acceleration libraries.
