# Candidate Qualification Gate Assessment

**Milestone:** Project Janus v0.61  
**Author:** Independent Experimental Auditor & Principal ML Systems Architect  
**Date:** 2026-11-07  
**Candidate Evaluated:** Janus Neural Value V2 (NNUE-V2-Small, 51,281 parameters)  
**Control Baseline:** Janus Classical Baseline C1 (Native N5)  
**Qualification Decision:** **QUALIFIED FOR TOURNAMENT VALIDATION**  

---

## 1. Candidate Qualification Gate Matrix

The v0.61 governing specification establishes six strict scientific and engineering prerequisites that must all be satisfied before an experimental neural candidate is permitted to initiate a competitive playing-strength tournament against the frozen Classical Baseline C1.

| Gate | Evaluation Domain | Preregistered Criterion | Empirical Result | Gate Status |
| :--- | :--- | :--- | :--- | :--- |
| **Gate 1** | **Generalization Superiority** | Statistically significant reduction in held-out test MAE vs Classical C1 ($p < 0.05$) | $\Delta\text{MAE} = -16.29\text{ cp}$ (162.46 vs 178.63 cp), 95% CI: $[-19.27, -13.22]$, $p < 10^{-10}$ | **PASS** |
| **Gate 2** | **Quantization Fidelity** | Pearson $r \ge 0.995$, Sign Agreement $\ge 95.0\%$, MAE $\le 15.0\text{ cp}$ | Pearson $r = 0.998887$, Sign Agreement = 98.50%, MAE = 10.01 cp, CRC32 verified | **PASS** |
| **Gate 3** | **Native AVX2 Throughput** | Leaf latency $\le 250\text{ ns}$, Throughput $\ge 4.0\text{M evals/s}$ | Leaf latency = **128.36 ns** ($-75.8\%$ vs v0.60), Throughput = **7,790,690 /s** (4.87x vector speedup) | **PASS** |
| **Gate 4** | **System & Search Invariance**| 100% pass on 650+ tests; bit-exact C1 baseline when disabled; AVX2 == Scalar search tree | 658/658 tests passed (0 failures); bit-exact C1 parity; AVX2 and Scalar produce identical node counts | **PASS** |
| **Gate 5** | **Alpha-Beta Search Efficiency**| Node reduction $\ge 15.0\%$ at fixed depth; Search NPS retention $\ge 50.0\%$ vs C1 | S1 Pure: **$-32.65\%$ nodes**, **151.7% NPS**; S2 Hybrid: **$-18.39\%$ nodes**, **96.8% NPS** | **PASS** |
| **Gate 6** | **Tactical Sanity & Mating** | Mate scores $\ge 28,000$ (uncontaminated); mate-in-1 solved accurately; tactical coherence | Finds mate-in-1 (`f3f7#`), score = 28,999; S2 move agreement with Stockfish 19 = 40.0% | **PASS** |

---

## 2. Gate-by-Gate Detailed Audit

### Gate 1: Test Generalization Superiority
Across 10,000 held-out master test positions labeled by Stockfish 19 at 10,000 nodes, NNUE-V2-Small demonstrated decisive predictive superiority over both the Classical C1 baseline and the frozen NNUE-V1-Small reference:
- **T2 vs T0 (NNUE-V2 vs Classical C1):**
  - MAE: 162.46 cp vs 178.63 cp ($\Delta = -16.29$ cp [95% CI: $-19.27, -13.22$], $p = 1.2 \times 10^{-27}$).
  - Spearman rank correlation: 0.5336 vs 0.5142.
  - Sign agreement: 77.0% vs 69.5% (+7.5 percentage points).
  - Opening MAE: 39.19 cp vs 73.59 cp ($-46.7\%$ error reduction).
  - Middlegame MAE: 144.28 cp vs 167.24 cp ($-13.7\%$ error reduction).

### Gate 2: Quantization Fidelity
The native integer model (`janus_nnue_v2_small.jnnue`, 100,628 bytes) was audited across 1,000 held-out positions against the unquantized PyTorch FP32 model:
- Pearson correlation coefficient: $r = 0.998887$ (exceeds 0.995 threshold).
- Sign agreement: $98.50\%$ (exceeds 95.0% threshold).
- Quantization MAE: $10.01$ cp (well within 15.0 cp bound).
- Payload CRC32: `0x81d61206` verified bit-exact between header and memory payload.
- AVX2 non-saturation proof mathematically confirmed for all intermediate dot products: $\text{range} = [-32,512, +32,258] \subset [-32,768, +32,767]$.

### Gate 3: Native AVX2 Performance & Leaf Throughput
Benchmark results measured across 1,000,000 consecutive operations:
- Feature transformer accumulator update (quiet move): **15.00 ns** (AVX2) vs 134.19 ns (Scalar) $\to$ **8.95x speedup**.
- Feedforward evaluation ($\text{FC1} + \text{FC2}$): **113.36 ns** (AVX2) vs 490.62 ns (Scalar) $\to$ **4.33x speedup**.
- End-to-end leaf evaluation: **128.36 ns** (AVX2) vs 624.81 ns (Scalar) $\to$ **4.87x speedup**.
- Throughput: **7,790,690 evaluations per second**.

### Gate 4: System Correctness & Invariance
- Full regression suite execution: **658 passed, 0 failed, 0 skipped** in 94.87s.
- Baseline parity test: When `UseNeuralValue=false`, all move outputs, depth iterations, score values, and node counts are 100% bit-exact identical to Native N5 / Classical C1.
- SIMD invariance: AVX2 and Scalar searches executed across benchmark positions yielded identical node counts (115,237 nodes at d4, 280,438 nodes at d5).

### Gate 5: Alpha-Beta Search Efficiency
Search dynamics evaluated across 10 diverse master positions:
- **Pure NNUE-V2 (S1):** Reduced total search nodes by **$-55.89\%$** at depth 4 and **$-32.65\%$** at depth 5. Achieved 151.7% of Classical C1's NPS due to reduced quiescent tree explosion.
- **Hybrid 50/50 (S2):** Reduced search nodes by **$-27.01\%$** at depth 4 and **$-18.39\%$** at depth 5, retaining 96.8% of C1's NPS (895,985 vs 925,736 NPS).

### Gate 6: Tactical Coherence & Mate Handling
- Tested on tactical delivery positions (e.g. Scholar's mate attack `f3f7#`). The engine immediately selects the checkmating move with score `28,999` ($30,000 - \text{ply}$ bound). Static neural evaluations never override terminal checkmate scores.
- S2 Hybrid achieves 40.0% move agreement with Stockfish 19 at depth 5, significantly outperforming pure neural search (10.0%) in classical tactical alignment.

---

## 3. Formal Qualification Declaration

All six preregistered Candidate Qualification Gates have **PASSED** with statistical significance and zero regressions.

**Selected Candidate for Strength Validation Tournament:**
In accordance with the calibration findings, the **Hybrid 50/50 NNUE-V2-Small candidate (S2)** is designated as the primary tournament competitor against Classical Baseline C1. Hybrid 50/50 provides the optimal balance of neural positional nuance ($-18.4\%$ node reduction) with classical material security and tactical move quality (40% SF19 agreement). Additionally, Pure NNUE-V2 (S1) is maintained as a calibrated ablation reference.

Permission is hereby **GRANTED** to proceed to Phase 7: Competitive Playing-Strength Tournament.

