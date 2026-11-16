# Project Janus — Phase 2, Milestone P2.1
## Formal Milestone Decision Gate & Release Adjudication

**Author:** Principal Computer Chess Architect & Experimental Auditor  
**Milestone:** P2.1 — Neural Evaluation Foundations, Incrementally Updatable Inference & Hybrid Search Integration  
**Date:** 2026-11-16  
**Candidate Architecture:** Janus Hybrid H1  
**Candidate Executable:** `analysis/phase2/p2.1/control/janus_hybrid_h1.exe`  
**Candidate SHA-256:** `755C451D064EA38ECC400274CBCE48D28B6F43F67747BB63C0F4E84F6EA4F97A`  

---

### 1. Milestone Objective & Decision Matrix

Milestone P2.1 sets out to establish the complete architectural and empirical foundation for Project Janus neural evaluation.
The governing charter defines three potential release categories:

1. **Category A (Outright Superior Replacement):**
   - The neural candidate demonstrates statistically verified playing strength superior to the qualified classical baseline (Janus Classical R1.0) under identical search conditions ($p < 0.05$, win rate $> 50\%$).
   - *Status:* **REJECTED.** Candidate H1 achieved 1.5% (+0 =3 -97) against Classical R1 in Match M1. It is not currently stronger than Classical R1 in standalone playing strength.

2. **Category B (Validated Research Baseline & Architectural Foundation):**
   - The candidate satisfies 100% of functional correctness, mathematical parity, incremental update integrity, search economics, and stability gates.
   - The hybrid architecture functions smoothly, and the candidate provides the verified infrastructure required for iterative Phase 2 neural scaling.
   - *Status:* **QUALIFIED AND OFFICIALLY ACCEPTED.**

3. **Category C (Architectural Failure / Dead End):**
   - The candidate suffers from search-inference desynchronization, illegal accumulator updates, performance crashes, or unresolvable latency degradation.
   - *Status:* **REJECTED.** Candidate H1 passed all 12 formal correctness gates with 0 errors and completed 450 tournament games with 0 forfeits or crashes.

---

### 2. Evidence Synthesis

#### 2.1 Technical and Mathematical Verification
- **Dual-Perspective HalfKP-768 Schema:** 768 non-overlapping indices, color-inversion symmetry, and exact incremental updates across 3,968 moves with 0 mismatches.
- **Dataset Engineering:** 50,978 globally deduplicated positions extracted from Phase 1 tournaments, partitioned strictly by game into Train (40,736), Val (5,127), and Test (5,115).
- **Quantization Parity:** Fixed-point INT16/INT8 inference achieves Pearson correlation $r = 0.999635$ with PyTorch 32-bit float inference across 500 test positions, with MAE of only $6.51\text{ cp}$ and zero accumulator overflows.
- **Incremental Accumulator Parity:** Verified across 7,917 legal moves over 100 games: **100.000% exact integer equality ($\Delta = 0$)** between incremental updates and scratch recomputations across all 256 accumulator elements.
- **Search Economics:** H1 cuts search tree nodes by 35.7% at Depth 6 in `Startpos` ($20,671$ nodes vs $32,139$ for Classical) while sustaining 110,000 NPS with zero memory allocations during search.
- **12 Formal Correctness Gates:** 12/12 passed (Feature parity, Accumulator parity, Overflow guards, Weight dimensions, Checksum integrity, Embedded fallback, Thread safety, Time-abort responsiveness, UCI lifecycle, Color symmetry, Make/unmake invariance, and Evasion completeness).

#### 2.2 Playing-Strength & Hybrid Integration
- **Match M1 (H1 vs Classical R1):** 1.5% score (+0 =3 -97) confirms that pure 50k-position NNUE requires scaling before it can surpass handcrafted classical evaluation.
- **Match M2 (H2 Hybrid Blend vs H1 Pure NNUE):** 99.0% score (+49 =1 -0) demonstrates that the R1 classical evaluation core successfully acts as a stabilizing anchor in hybrid mode.
- **Matches M3–M7:** Complete protocol stability across 450 tournament games against historical and modern engines (X7, X22-S, Stockfish 4, Stockfish 11, Stockfish 19).

---

### 3. Formal Milestone Decision

**DECISION: QUALIFY JANUS HYBRID H1 AS CATEGORY B (RESEARCH BASELINE & ARCHITECTURAL FOUNDATION).**

Janus Hybrid H1 is frozen into the permanent repository archive:
- Binary: `analysis/phase2/p2.1/control/janus_hybrid_h1.exe`
- Shared Library: `analysis/phase2/p2.1/control/janus_hybrid_h1.dll`
- Quantized Weight File: `models/janus_nnue_h1.bin`
- C++ Header: `engine/classical_x/r1/r1_nnue_weights.hpp`

All technical prerequisites for Milestone P2.2 have been completely achieved.

---

### 4. Roadmap to Milestone P2.2

Milestone P2.2 will advance directly from the verified H1 foundation to address playing-strength scaling:
1. **Dataset Scaling:** Scale training corpus from 50k positions to 2M–5M high-depth self-play positions.
2. **Feature Expansion:** Implement King-relative feature indexing (HalfKP-4096 / HalfKAv2) to capture critical king shelter and attack vectors.
3. **Training Refinement:** Implement lambda-learning schedule combining game result with teacher search score.
4. **Quantized AVX2/NEON SIMD Vectorization:** Optimize accumulator transformations using 256-bit SIMD intrinsics to push NPS beyond 500k.
