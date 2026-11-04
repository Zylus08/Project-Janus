# Project Janus v0.52 — Formal Match Preregistration Document

**Protocol:** Preregistered Controlled Strength Ablation  
**Date:** 2026-11-04  
**Auditor / Experiment Lead:** Principal Chess Engine Research Engineer  
**Status:** **FROZEN & IMMUTABLE PRIOR TO MATCH EXECUTION**  

---

## 1. Experimental Objective & Hypothesis

**Research Question:** Does Late Move Reductions (LMR) improve competitive playing strength in the native C++17 Janus search engine under controlled Fischer time controls?

**Null Hypothesis ($H_0$):**  
Candidate N3 (`UseLMR=true`) exhibits no playing strength advantage over Baseline N2 (`UseLMR=false`), meaning the mean paired score difference per opening pair $\bar{d} \le 0.0$, or the result fails to achieve statistical significance at $\alpha = 0.05$ (two-sided paired Student-t test, $df = 99$).

**Alternative Hypothesis ($H_1$):**  
Candidate N3 achieves a statistically significant playing strength advantage over Baseline N2 ($\bar{d} > 0.0$, $p < 0.05$, with positive 95% bootstrap confidence interval).

---

## 2. Cryptographic Manifest of Artifacts Under Test

The following binary and source artifacts are frozen prior to match launch:

| Component | Path | SHA-256 Checksum |
|---|---|---|
| **C++17 Engine Source** | `analysis/v0.52/native/janus_native.cpp` | `16451277fdc7196a19b9224cffb9f62834fc3dddac75dbb7b1c12e7bcddb4ee3` |
| **Native UCI Executable** | `analysis/v0.52/native/janus_native_engine.exe` | `8a55d332447a8972b53248566684a9f5f64b5d1b443059e524afa425aca7428a` |
| **Native DLL Bridge** | `analysis/v0.52/native/janus_native.dll` | `df1dca954f2d2dd4443fc8f400f1f98ee7cc39c474068103cbd01224d8e886c0` |
| **Opening Suite (100 Pairs)**| `analysis/v0.52/corpus/openings_v052_100.json` | `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b` |
| **Tournament Controller** | `analysis/v0.52/tests/tournament_controller.py` | `2573dbcbc5213c4ecbbb4e1a1d88ffa9ce391c7a0e6502eb5e3c56dd18c7159f` |

---

## 3. Controlled Experimental Protocol

1. **Format:** 100 opening pairs (200 games total). Each opening position is contested twice, alternating colors between Game A (N3 White vs N2 Black) and Game B (N2 White vs N3 Black) to eliminate opening color bias.
2. **Single Independent Variable:** 
   - Control (N2): `janus_native_engine.exe` with `UseLMR=false` (baseline search).
   - Candidate (N3): `janus_native_engine.exe` with `UseLMR=true`, `LMRMinDepth=3`, `LMRMoveThreshold=4`, `LMRBaseReduction=1`.
   - Transposition Table: 1,048,576 entries (16 MB) for both engines.
   - Ponder: Off for both engines.
3. **Time Control:** 
   - Initial Base Time: 3.0 seconds (3,000 ms).
   - Fischer Increment: 100 milliseconds per move.
4. **Adjudication Rules:**
   - Checkmate: 1-0 or 0-1.
   - Stalemate: 1/2-1/2.
   - Insufficient Material: 1/2-1/2.
   - 75-Move Rule: 1/2-1/2 (Automatic, FIDE 9.6.2).
   - 5-Fold Repetition: 1/2-1/2 (Automatic, FIDE 9.6.1).
   - 50-Move Rule Claim: 1/2-1/2 (Claimable, FIDE 9.3).
   - 3-Fold Repetition Claim: 1/2-1/2 (Claimable, FIDE 9.2).
   - Emergency Circuit Breaker: 300 plies (150 full moves). Any game reaching 300 plies is logged as `safety_limit_300_plies` and never mislabeled as a FIDE draw.
5. **Statistical Evaluation Framework:**
   - Primary Metric: Mean score per opening pair $d_i = \text{score}_{\text{N3}}(\text{Game } A) + \text{score}_{\text{N3}}(\text{Game } B) - 1.0 \in [-1.0, +1.0]$.
   - Paired Student-t test ($df = 99$, two-sided).
   - 100,000 paired bootstrap resamples for 95% confidence intervals.
   - Logistic Elo difference formula: $\Delta\text{Elo} = -400 \log_{10}(1/S - 1)$.

