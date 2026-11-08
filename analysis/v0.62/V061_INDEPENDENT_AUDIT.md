# Independent Audit of v0.61 Evidence, Artifacts & Provenance

**Milestone:** Project Janus v0.62  
**Author:** Independent Experimental Auditor & Statistical Validation Specialist  
**Date:** 2026-11-07  
**Evaluated Milestone:** Project Janus v0.61  
**Target Commit:** `95389dc` on branch `v0.3-benchmark-harness`  
**Raw Audit Telemetry:** `analysis/v0.62/raw/v061_reconstructed_audit.json`  

---

## 1. Git HEAD & Provenance Audit

| Attribute | Expected Target | Reconstructed Reality | Status |
| :--- | :--- | :--- | :---: |
| **Git Branch** | `v0.3-benchmark-harness` | `v0.3-benchmark-harness` | **MATCH** |
| **Parent Commit** | `08db0c0` | `08db0c0` | **MATCH** |
| **v0.61 Milestone Commit** | `95389dc` | `95389dccd5f2d20bb8e7ebf128b7d178db720804` | **MATCH** |
| **Working Tree State** | Clean | Clean (0 modified, 0 untracked outside v0.62) | **MATCH** |

---

## 2. File Integrity & SHA-256 Hash Verification

All core software components, model artifacts, and test baselines were independently hashed:

| Artifact Description | File Path | Recorded SHA-256 Hash | Size (Bytes) | Verification |
| :--- | :--- | :--- | :--- | :---: |
| **C1 Native Source (Frozen)** | `analysis/v0.56/native/janus_native.cpp` | `43ad79ade44cc6d6dd97a4cfeb6e9ba2b32c8d080190808d22cac486616397a4` | 80,677 | **VERIFIED** |
| **C1 Native Engine (Frozen)** | `analysis/v0.56/native/janus_native_engine.exe` | `a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f` | 341,504 | **VERIFIED** |
| **C1 Native DLL (Frozen)** | `analysis/v0.56/native/janus_native.dll` | `23f34a44e4bbe9232d034fe2077e231e3a6c23073715cbe046279f187bfce4d5` | 259,072 | **VERIFIED** |
| **NNUE-V2 Native Source** | `analysis/v0.61/native/janus_native.cpp` | `b67184fe787c5c0c9cb046ae9b43e8ea0c1e847c2125bb79555ba6fa982994e6` | 88,730 | **VERIFIED** |
| **NNUE-V2 Engine (AVX2)** | `analysis/v0.61/native/janus_native_engine.exe` | `fc82936845a758df6e25dc74ec069c9bcf04724a350122e23b88939c39bc077b` | 381,440 | **VERIFIED** |
| **NNUE-V2 Native DLL** | `analysis/v0.61/native/janus_native.dll` | `4832866660dbf144414f553f19159045db327e559c55b6fb89db7a5c8df59f33` | 321,024 | **VERIFIED** |
| **NNUE-V2 SIMD Kernel C++** | `analysis/v0.61/native/nnue_v2.cpp` | `ff7013a8716ff72e73703ee52834c9c1b3531bfa2be7338ba51fb59c1626fdb9` | 13,554 | **VERIFIED** |
| **NNUE-V2 SIMD Header** | `analysis/v0.61/native/nnue_v2.h` | `de97448d325652f4a56c07521a00a0b22a07ddf1773177651c6df341a9bc989d` | 2,935 | **VERIFIED** |
| **NNUE-V2-Small Model** | `analysis/v0.61/models/janus_nnue_v2_small.jnnue` | `ff7ac9a0d45d1426615b13cf17d23f38d3886f4df344f6f4370db0420eb24f2b` | 100,628 | **VERIFIED** |
| **NNUE-V2-Compact Model** | `analysis/v0.61/models/janus_nnue_v2_compact.jnnue`| `463d1595085e9e4ee8d7c49bb0b81a7b1bfe95ba450a8a6beffea7713d6a8f15` | 205,284 | **VERIFIED** |
| **Stockfish 19 Teacher** | `tools/stockfish/stockfish.exe` | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` | 103,046,300 | **VERIFIED** |
| **v0.56 Opening Suite** | `analysis/v0.56/corpus/independent_openings_v056.json`| `d4db2cf96044421ed45a557b4458399eec3851eb72e81fa049d5c22501a4e101` | 63,189 | **VERIFIED** |
| **v0.61 Tournament PGN** | `analysis/v0.61/pgn/v061_v2_vs_c1_match.pgn` | `1f3db98de7f2350c3ff4da37895e64a1ceebdb2274b772c7ea2eb7db8957bf2a` | 207,851 | **VERIFIED** |
| **v0.61 Tournament Raw** | `analysis/v0.61/raw/v061_v2_vs_c1_match_raw.json`| `29e295f8b57dd260492cb71e069fc6368d54238e55e6c55d09f7a77f09f9845d` | 303,699 | **VERIFIED** |

---

## 3. Independent Tournament Reconstruction

The 200 individual games in `analysis/v0.61/raw/v061_v2_vs_c1_match_raw.json` and `analysis/v0.61/pgn/v061_v2_vs_c1_match.pgn` were independently parsed and reconstructed move-by-move:

### Table 1: Independent Tournament Telemetry Audit

| Metric | v0.61 Claimed Value | Reconstructed Audit Value | Audit Reconciliation |
| :--- | :--- | :--- | :---: |
| **Total Games** | 200 | 200 | **BIT-EXACT** |
| **Candidate Wins** | 71 | 71 | **BIT-EXACT** |
| **Draws** | 86 | 86 | **BIT-EXACT** |
| **Candidate Losses** | 43 | 43 | **BIT-EXACT** |
| **Total Points** | 114.0 / 200 (57.00%) | 114.0 / 200 (57.00%) | **BIT-EXACT** |
| **Estimated Elo Delta** | +49.0 Elo | +49.0 Elo | **BIT-EXACT** |
| **10k Bootstrap Elo CI (95%)** | [+12.2, +85.0] Elo | [+12.2, +85.0] Elo | **BIT-EXACT** |
| **Mean Paired Difference / Pair**| +0.280 | +0.2800 | **BIT-EXACT** |
| **Paired Diff 95% CI** | [+0.070, +0.480] | [+0.0700, +0.4800] | **BIT-EXACT** |
| **Degrees of Freedom** | 99 | 99 | **BIT-EXACT** |
| **Student-t Statistic** | +2.6075 | +2.6075 | **BIT-EXACT** |
| **Student-t p-Value** | $1.0532 \times 10^{-2}$ | $1.05319 \times 10^{-2}$ | **BIT-EXACT** |
| **PGN Game Record Count** | 200 games | 200 games | **BIT-EXACT** |

### Adjudication & Termination Breakdown:
- **Threefold Repetitions:** 84 (42.0%)
- **Checkmates (Black Delivery):** 68 (34.0%)
- **Checkmates (White Delivery):** 46 (23.0%)
- **Insufficient Material Draws:** 1 (0.5%)
- **50-Move Rule Draws:** 1 (0.5%)
- **Engine Forfeits / Timeouts / Illegal Moves:** **0 (0.0%)**

Every recorded game finished in a strictly legal FIDE terminal state without procedural anomalies.

---

## 4. Opening Suite Provenance & Dataset Contamination Audit

### 4.1 Provenance of `independent_openings_v056.json`
- Origin: Created in Project Janus v0.56 to serve as an unmemorized opening corpus for classical baseline qualification.
- Structure: Exactly 100 openings covering 12 ECO codes (A00–E99) with depths ranging from 8 to 12 plies.
- Position Count: Traversal of all move sequences generates **1,142 unique position EPDs**.

### 4.2 Cross-Split Contamination Audit
To verify whether NNUE-V2 possessed unfair training memory of the tournament opening positions, the 1,142 opening positions were cross-referenced against the 100,000 supervised training positions:

| Dataset Partition | Total Partition Positions | Overlapping Opening Positions | Overlap Percentage | Contamination Severity |
| :--- | :--- | :--- | :--- | :--- |
| **Training Split (`value_v2_train.json`)** | 80,000 | 285 positions | 0.356% | **Benign Trunk Overlap** |
| **Validation Split (`value_v2_val.json`)** | 10,000 | 5 positions | 0.050% | **Negligible** |
| **Test Split (`value_v2_test.json`)** | 10,000 | 8 positions | 0.080% | **Negligible** |
| **Full-Game Leakage** | 3,560 training games | 0 complete games | 0.000% | **Zero Leakage** |

### Findings & Nuance:
The 285 overlapping positions consist entirely of universal standard opening trunk plies (e.g. `1. e4`, `1. d4`, `1. c4`, `1. Nf3 Nf6`, `1. e4 c5 2. Nf3`). Because the Lichess Elite dataset comprises master games, early standard opening moves inevitably appear in thousands of games.
**Crucially, zero full opening sequences or middlegame transitions from the opening suite existed as complete games in the training corpus.**

### Scientific Limitation:
While the overlap is benign, **the v0.61 tournament reused `independent_openings_v056.json`**, which was previously used in v0.56–v0.58. Therefore, from a strict metrological standpoint, v0.61's result cannot be certified as an *independent confirmatory replication* until validated on a **completely new, unseen 100-pair opening suite**.

---

## 5. Native AVX2 Performance & Denominator Verification

The claimed speedups were re-audited against the microbenchmark code in `analysis/v0.61/native/test_nnue_v2_native.cpp`:
- **Denominator Workload:** 1,000,000 consecutive operations per test measured with `std::chrono::high_resolution_clock`.
- **Environment:** MSVC 19.43 `/O2 /W4 /std:c++17 /arch:AVX2` on Windows AMD64.
- **Incremental Accumulator Update:**
  - Scalar C++17: 134.19 ns
  - AVX2 SIMD: 15.00 ns (**8.95x speedup**)
- **Feedforward Network (L1 + L2):**
  - Scalar C++17: 490.62 ns
  - AVX2 SIMD: 113.36 ns (**4.33x speedup**)
- **End-to-End Leaf Latency:**
  - Scalar C++17: 624.81 ns
  - AVX2 SIMD: **128.36 ns** (**4.87x speedup**, 7.79M evals/sec)
- **Comparison to Historical Baselines:**
  - v0.60 Scalar Leaf Latency: 529.40 ns
  - v0.61 AVX2 Leaf Latency: 128.36 ns (**75.8% reduction in latency**)

The latency reduction and throughput numbers are verified to be mathematically and experimentally sound.

---

## 6. Audit Verdict

1. **Internal Validity:** The reported v0.61 experimental data, PGN logs, telemetry JSON, hashes, and statistical calculations are 100% genuine, unmanipulated, and completely reproducible.
2. **Confirmatory Requirement:** Because the v0.61 match reused `independent_openings_v056.json`, Phase 2 & 3 must execute an **independent confirmatory match on a brand-new, unseen opening suite** to qualify for final Category A production promotion.

