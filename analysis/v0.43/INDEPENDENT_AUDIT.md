# Project Janus v0.43 — Independent Clean-Room Audit Report (Phase I)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Audit Pipeline:** `scripts/audit_v043_pipeline.py`  
**Audit Report JSON:** `analysis/v0.43/independent_audit.json`  
**Manifest:** `analysis/v0.43/sha256_manifest.json`  
**Verdict:** **VERIFIED_VALID**  
**Date:** 2026-11-03  

---

## 1. Audit Scope & Verification Principles

The v0.43 independent audit was executed via a clean-room pipeline verifying:
1. **Repository & Codebase Provenance:** Full ancestry traceability from `f499329` to current HEAD `41f407d`. Zero modifications to engine source code.
2. **Opening Manifest Integrity:** SHA-256 digest verification of `openings_v043_100.json` (`2f929719ab8377e1...`).
3. **PGN Correctness:** Move-by-move parse of 400 games (32,826 plies) using `chess.pgn`.
4. **Clock Compliance:** 32,826 move telemetry records examined for negative clocks or timing violations.
5. **Attempt Accounting:** 400 completed games matched against attempt logs with zero exclusions.
6. **Statistical Re-computation:** Independent re-derivation of paired differences, $t$-statistics, and bootstrap intervals.
7. **Regression Unit Tests:** Automated execution of all RFP, repetition, and draw semantics tests.

---

## 2. Independent Audit Verdict Matrix

| Audit Dimension | Criterion | Evaluated Result | Verdict |
|:---|:---|:---:|:---:|
| **Experimental Integrity** | 100 colour-reversed pairs completed without dropouts | 400/400 games completed (0 failures) | **PASS** |
| **Statistical Correctness** | Accurate calculation of mean delta, SE, $t$-statistic, and CI | Fully recomputed & verified | **PASS** |
| **Configuration Equivalence** | Single-variable isolation (`enable_rfp` flag only) | Machine-readable diff confirmed | **PASS** |
| **Search Correctness** | Zero illegal moves across all 400 games | 32,826 / 32,826 plies legal | **PASS** |
| **Clock Telemetry** | Zero negative clock readings | 0 / 32,826 moves negative | **PASS** |
| **Unit Test Invariants** | 100% pass rate across invariant test suite | 21 / 21 tests pass | **PASS** |
| **Reproducibility** | Full replication dataset persisted with SHA-256 digests | 16 artifacts hashed in manifest | **PASS** |

---

## 3. Recomputed Statistical Summary

- **Total Complete Pairs ($N$):** 100
- **Baseline K0 Score:** 123.0 / 200.0 (61.50%)
- **Candidate RFP Score:** 119.5 / 200.0 (59.75%)
- **Mean Paired Delta ($\bar{\Delta}$):** **-0.0350 points / pair (-1.75% per game)**
- **Standard Error ($\text{SE}$):** **0.0888**
- **Student's $t$-statistic (df = 99):** **-0.3940**
- **One-tailed $p$-value ($H_1: \mu_\Delta > 0$):** **0.6528** (Fails to reject $H_0$)
- **Two-tailed $p$-value ($H_0: \mu_\Delta = 0$):** **0.6945**
- **10,000-Resample Pair Bootstrap 95% CI:** **[-10.25%, +7.00%] per game**
- **Pair Outcomes:** RFP > K0: 30 (30.0%), Tied: 37 (37.0%), K0 > RFP: 33 (33.0%)

---

## 4. Overall Audit Verdict

$$\mathbf{VERIFIED\_VALID}$$

The experimental pipeline, data integrity, and statistical calculations are 100% sound and verified.

