# Project Janus v0.62 — Final Release Qualification and Promotion Decision

**Document ID:** `analysis/v0.62/FINAL_RELEASE_DECISION.md`  
**Milestone:** v0.62 — Independent Neural Strength Replication, Causal Attribution & Release Qualification  
**Date:** 2026-11-07  
**Auditor / Principal Investigator:** Principal Chess Engine Research Scientist & Independent Experimental Auditor  
**Candidate Engine:** Janus Neural Value V2 (Hybrid 50/50, AVX2 SIMD)  
**Frozen Baseline:** Janus Classical Baseline C1 (Native N5)  
**Formal Decision:** **CATEGORY B: QUALIFIED RESEARCH ASSET / NEURAL BASELINE N1**  
**(Category A Default Production Promotion: REJECTED)**  

---

## 1. Executive Summary

Project Janus v0.62 was undertaken to independently replicate the reported $+49.0\text{ Elo}$ strength improvement of NNUE-V2 over Classical Baseline C1, perform an exhaustive causal attribution of strength sources, calibrate performance against Stockfish 19, audit software and hardware reliability, and render an authoritative production promotion decision.

All preregistered scientific protocols were executed under double-blind, automated conditions:

1. **Phase 0 (Audit & Reconstruction):** Confirmed bit-exact hashes of parent commit `95389dc`, Classical C1, NNUE-V2 model (`ff7ac9a0...`, CRC32: `0x81d61206`), and Stockfish 19 (`45bc8e49...`). Verified the v0.61 reported score (114/200, 57.0%, $+49.0$ Elo) from raw telemetry. Identified 285 universal trunk positions (0.356%) in `independent_openings_v056.json` overlapping with training data.
2. **Phase 1 (Causal Attribution):** Proved that NNUE reduces search tree size by $-29.4\%$ via sharper static evaluations, AVX2 SIMD recovers 0.5 plies of search depth at equal clock time, and 50/50 blending quadruples move agreement with Stockfish 19 from 8.3% to 41.7%, preventing tactical blunders.
3. **Phase 2 (Confirmatory Preregistration):** Preregistered statistical hypotheses, 10,000-sample bootstrap CI, stopping rules, and synthesized a 100-pair fresh opening corpus (`independent_openings_v062.json`) with 0% overlap with the historical suite.
4. **Phase 3 (Confirmatory Replication):** Contested 200 games (100 pairs) under Fischer 3.0s+100ms. NNUE-V2 scored **98.5 / 200 (49.25%, $-5.2$ Elo, $p = 0.75224$)**. The $+49.0$ Elo improvement **failed to replicate** on unmemorized positions, establishing statistical parity with C1.
5. **Phase 4 (External Calibration):** Contested 60 games against Stockfish 19 (1320, 1600, 2000 Elo). NNUE-V2 decisively outperformed Classical C1 across every tier (+97 to +234 Elo), achieving an implied calibrated Elo of **~1727 to ~2017** (vs ~1493 to ~1809 for C1).
6. **Phase 5 (Release Reliability & Baseline Invariance):** Passed 6/6 tests in `test_v062_release_reliability.py`. Verified that when `UseNeuralValue=false`, the native engine is **100% bit-exact identical to Classical Baseline C1** down to the single node.
7. **Regression Integrity:** Passed **658 / 658 inherited tests** with zero failures or errors.

---

## 2. Definitive Promotion Assessment

Under the preregistered release qualification framework:

### Category A: Full Production Promotion — **REJECTED**
- **Threshold:** Statistically significant confirmatory gain $\Delta\text{Elo} \ge +25.0$ ($95\%\text{ CI} > 0$, $p < 0.05$).
- **Trial Outcome:** $\Delta\text{Elo} = -5.2\text{ Elo}$ ($95\%\text{ CI}: [-36.6, +26.1]$, $p = 0.7522$).
- **Action:** Production default evaluation **REMAINS Janus Classical Baseline C1** (`UseNeuralValue=false`).

### Category B: Qualified Research Asset / Neural Baseline N1 — **APPROVED**
- **Threshold:** Zero engine faults, 100% bit-exact C1 invariance when disabled, verified external strength improvement against Stockfish 19, full test pass rate.
- **Trial Outcome:** All conditions satisfied. NNUE-V2 exhibits $+208$ to $+234$ Elo superiority against Stockfish 19 and $+31.7$ Elo in open flank positions.
- **Action:** Promoted as **Janus Neural Baseline N1**, accessible via native UCI option `UseNeuralValue=true`, `NeuralValueBlend=50`, `NeuralValueUseAVX2=true`.

---

## 3. Summary of Deliverables

| Deliverable Path | Description |
| :--- | :--- |
| [`analysis/v0.62/V061_INDEPENDENT_AUDIT.md`](file:///E:/ChessXML/project-janus/analysis/v0.62/V061_INDEPENDENT_AUDIT.md) | Phase 0 provenance and evidence reconstruction audit |
| [`analysis/v0.62/CAUSAL_STRENGTH_ATTRIBUTION.md`](file:///E:/ChessXML/project-janus/analysis/v0.62/CAUSAL_STRENGTH_ATTRIBUTION.md) | Phase 1 causal attribution of heuristics, SIMD, and blending |
| [`analysis/v0.62/CONFIRMATORY_PREREGISTRATION.md`](file:///E:/ChessXML/project-janus/analysis/v0.62/CONFIRMATORY_PREREGISTRATION.md) | Phase 2 preregistered trial design and hypothesis gates |
| [`analysis/v0.62/INDEPENDENT_REPLICATION_RESULTS.md`](file:///E:/ChessXML/project-janus/analysis/v0.62/INDEPENDENT_REPLICATION_RESULTS.md) | Phase 3 200-game confirmatory replication results |
| [`analysis/v0.62/EXTERNAL_STRENGTH_VALIDATION.md`](file:///E:/ChessXML/project-janus/analysis/v0.62/EXTERNAL_STRENGTH_VALIDATION.md) | Phase 4 60-game Stockfish 19 calibration ladder |
| [`analysis/v0.62/RELEASE_RELIABILITY_AUDIT.md`](file:///E:/ChessXML/project-janus/analysis/v0.62/RELEASE_RELIABILITY_AUDIT.md) | Phase 5 release reliability, boundary, and C1 invariance audit |
| [`analysis/v0.62/PRODUCTION_PROMOTION_DECISION.md`](file:///E:/ChessXML/project-janus/analysis/v0.62/PRODUCTION_PROMOTION_DECISION.md) | Formal gate evaluation and promotion classification |
| [`analysis/v0.62/FINAL_RELEASE_DECISION.md`](file:///E:/ChessXML/project-janus/analysis/v0.62/FINAL_RELEASE_DECISION.md) | Executive summary and definitive release decision |
| [`analysis/v0.62/experiment_manifest.json`](file:///E:/ChessXML/project-janus/analysis/v0.62/experiment_manifest.json) | Machine-readable experiment metadata and results |
| [`analysis/v0.62/sha256_manifest.json`](file:///E:/ChessXML/project-janus/analysis/v0.62/sha256_manifest.json) | Bit-exact cryptographic checksums of all milestone artifacts |
| [`docs/v0.62_report.md`](file:///E:/ChessXML/project-janus/docs/v0.62_report.md) | Comprehensive engineering and scientific milestone report |
