# Project Janus v0.42 — Independent Clean-Room Audit Report (Phase H)

**Milestone:** v0.42  
**Audit Pipeline:** `scripts/audit_v042_pipeline.py`  
**JSON Report:** `analysis/v0.42/independent_audit.json`  
**Manifest:** `analysis/v0.42/sha256_manifest.json`  
**Verdict:** **VERIFIED_VALID**  
**Date:** 2026-11-03  

---

## 1. Audit Scope & Methodology

This clean-room audit was conducted to independently verify:
1. Integrity and preservation of historical v0.41 reference artifacts.
2. Direct paired ablation calculations between Baseline K0 and Candidate RFP.
3. Chess rule compliance and draw semantics in search routines (`_negamax`, `_quiescence`, `_terminal_score`).
4. Correctness invariant unit tests (`test_v040_rfp`, `test_v041_repetition_quiescence`, `test_v042_draw_semantics`).
5. Cryptographic SHA-256 digest generation for all v0.42 evidence artifacts.

---

## 2. Invariant Unit Test Verification

| Test Module | Coverage | Tests Run | Result |
|:---|:---|:---:|:---:|
| `tests.test_v040_rfp` | RFP invariants, check exemption, mate guard, quiet cutoff | 7 | ✓ ALL PASS |
| `tests.test_v041_repetition_quiescence` | 3-fold repetition at non-root plies, quiescence, 75-move | 7 | ✓ ALL PASS |
| `tests.test_v042_draw_semantics` | Automatic 75-move, 5-fold repetition, 50-move non-auto, TT draw guard | 7 | ✓ ALL PASS |
| **Total** | — | **21** | **✓ 21/21 PASS** |

---

## 3. Paired Ablation Verification

Direct verification of colour-reversed pairs across `analysis/v0.39/match_q0_k0` and `analysis/v0.41/match_rfp`:
- **Opening Alignment:** Verified 25 / 25 opening IDs strictly identical.
- **K0 Baseline Score:** 22.5 / 50.0 (45.0%).
- **RFP Candidate Score:** 37.0 / 50.0 (74.0%).
- **Mean Paired Delta:** $\bar{\Delta} = +0.5800$ points/pair ($+29.0\%$ per game).
- **Standard Error:** $\text{SE} = 0.2095$.
- **Student's $t$-statistic:** $t = 2.7682$ ($p = 0.0053 < 0.01$).
- **10,000-Resample Bootstrap 95% CI:** $[+9.0\%, +49.0\%]$ per game.
- **Verdict:** Mathematical and statistical re-computation confirmed.

---

## 4. Draw Semantics Audit Verification

| Requirement | Implementation Verification | Status |
|:---|:---|:---:|
| Automatic 75-move draw | Triggers at `halfmove_clock >= 150` via `is_seventyfive_moves()` | ✓ VERIFIED |
| Automatic fivefold repetition | Triggers at 5th repetition via `is_fivefold_repetition()` | ✓ VERIFIED |
| Threefold repetition modeling | Evaluated as draw at `ply > 0`; root searches non-repeating alternatives | ✓ VERIFIED |
| 50-move claimable draw | Not enforced as automatic draw (`halfmove_clock >= 100` absent from draw checks) | ✓ VERIFIED |
| TT draw proximity guard | Non-zero TT cutoffs suppressed when `halfmove_clock + depth >= 150` | ✓ VERIFIED |
| RFP/NMP draw proximity guard | Pruning suppressed when `halfmove_clock >= 140` | ✓ VERIFIED |

---

## 5. Artifact Digest Manifest

All artifacts in `analysis/v0.42/` are cryptographically hashed and indexed in `analysis/v0.42/sha256_manifest.json`.

---

## 6. Overall Audit Verdict

$$\mathbf{VERIFIED\_VALID}$$

Candidate RFP meets all preregistered empirical and correctness criteria.

