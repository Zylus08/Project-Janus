# Project Janus — Phase 2, Milestone P2.3
## Phase 16: Research Adjudication & Architectural Decision Gate

**Author:** Principal Computer Chess Architect, Independent Statistical Auditor & Tournament Integrity Specialist  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Decision Gate Designation:** Milestone P2.3 Final Adjudication  

---

### 1. Executive Summary & Formal Classification

In strict compliance with the Project Janus Evidence-Driven Research Charter, Candidate **Janus Hybrid H3** (HalfKP-40960 NNUE Architecture) is evaluated against formal milestone advancement criteria:

$$\textbf{Final Adjudication: CATEGORY B — Neural Engineering & Prediction Advancement}$$

**Classification Justification:**
Milestone P2.3 successfully solved the major structural, mathematical, and algorithmic flaws of earlier iterations (P2.1 H1 and P2.2 H2):
1. **HalfKP Feature Representation:** Established the first genuine king-conditioned feature architecture ($40,960$ features) with $100.000\%$ accumulator update oracle parity across $2,217$ diagnostic plies.
2. **Mathematically Calibrated Training:** Replaced uncalibrated outcome-only BCE with calibrated mixed lambda loss ($\lambda=0.8$), reducing evaluation error to $229.7\text{ cp}$ MAE and eliminating uncalibrated STM initiative bias.
3. **Correct Value Hierarchy:** Restored strictly monotonic piece ordering ($\text{Queen} > \text{Knight} > \text{Equal}$), resolving the catastrophic piece inversion of P2.2.
4. **Efficient Quantization & Inference:** Delivered INT16/INT8 quantized binary format (`janus_nnue_h3.bin`, SHA-256: `8FD3257B...`) with $r = 0.999780$ correlation to float32 and $3.3\times$ leaf acceleration over scratch recomputation.
5. **Search Economics:** Validated $35.0\%$ search tree compression under HalfKP evaluation guidance.

**However, Candidate H3 failed the Primary Playing-Strength Gate:**
In an authoritative 50-game match against Classical R1.0, Candidate H3 scored $0.5 / 50$ ($1.00\%$, $-798.3\text{ Elo}$, $p < 10^{-4}$). In competitive time-controlled play, pure neural evaluation cannot yet compensate for the tactical depth advantage of native classical search. Therefore, H3 cannot be promoted as an engine playing-strength advancement (Category A). It is classified as an engineering and prediction advancement (Category B).

---

### 2. Independent Subsystem Audit & Status Matrix

| Subsystem Domain | Audit Standard | Milestone Metric / Result | Gate Status |
| :--- | :--- | :--- | :---: |
| **Dataset Integrity** | Zero FEN Leakage, Strict Split by Game | $10,004$ positions, $0$ train-test overlap | **PASS** |
| **Teacher Quality** | Score Stability D5 vs D7, R1 vs X22 Agreement | Mean shift $12.2\text{ cp}$, agreement $14.4\text{ cp}$ | **PASS** |
| **Feature Correctness** | Incremental Accumulator Oracle Parity | $100.000\%$ exact match over $2,217$ plies | **PASS** |
| **Training Quality** | Test Score MAE, Monotonic Piece Hierarchy | Non-mate MAE $229.7\text{ cp}$, Queen $>$ Knight | **PASS** |
| **Quantization Stability**| Numerical Parity, Pearson $r$, Zero Overflows | $r = 0.999780$, MAE $2.73\text{ cp}$, 0 overflows | **PASS** |
| **Inference Performance**| Delta Update Latency vs Scratch Recompute | $0.39\ \mu\text{s}$ update, $3.3\times$ faster leaf eval | **PASS** |
| **Search Correctness** | 16 Formal Invariant Gates, TT & Rules | All 16 Gates PASSED ($100.0\%$) | **PASS** |
| **Search Economics** | Tree Compression under Alpha-Beta | $-35.0\%$ node reduction over KiwiPete | **PASS** |
| **Neural-Only Strength** | Primary Gate: H3 vs Classical R1 (50 Games) | $0.5 / 50$ ($1.0\%$, $-798.3\text{ Elo}$) | **FAILED** |
| **Generational Progress**| Secondary Gate: H3 vs Frozen H1 (50 Games) | $3.5 / 50$ ($7.0\%$, 7 draws, 2 DD pairs) | **INCONCLUSIVE** |

---

### 3. Baseline & Control Retention

In accordance with Category B adjudication:
1. **Janus Classical R1.0 (`6346caf` / `7312B2B7...`) remains the active, sovereign playing-strength baseline of Project Janus.**
2. **Historical Controls Janus Classical X7 (`86392A2F...`), X12, and X22 (`35D095CF...`) remain frozen and intact.**
3. **Candidate H3 artifacts (`janus_nnue_h3.pt` and `janus_nnue_h3.bin`) are archived as qualified research foundations for Milestone P2.4.**
4. No external code, third-party network weights, or pre-trained evaluation coefficients were utilized.
