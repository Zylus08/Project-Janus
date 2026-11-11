# Phase 11: Final Research & Promotion Decision

**Milestone:** Phase 1, Milestone P1.9  
**Charter:** Endgame Oracle Integration, Classical Evaluation Reliability & Independent Strength Requalification  
**Lineage Line:** Janus Classical (Non-ML Track)  
**Evaluated Candidate:** Janus Classical X (P1.9 Candidate X14)  
**Qualified Single-Thread Baseline:** Janus Classical X7 (`b34e342`, SHA-256: `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b`)  
**Qualified 4-Thread Baseline:** Janus Classical X12 (`78ca3d5`, SHA-256: `00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059`)  
**Decision Authority:** Principal Computer Chess Engineer, Systems Architect & Independent Reproducibility Auditor  

---

## 1. Formal Decision & Lineage Registry

### Verdict: CATEGORY B — Research Improvement Without Confirmed Strength Advancement
Candidate X14 **is NOT promoted** to qualified production baseline status.
The official baseline registry remains:
- **Qualified Single-Thread Production Baseline:** **Janus Classical X7** (RETAINED)
- **Qualified 4-Thread Production Baseline:** **Janus Classical X12** (RETAINED)
- **Advanced Classical Research Platform:** **Janus Classical X14** (CLASSIFIED AS EXPERIMENTAL REFERENCE)
- **Historical Platform:** **Janus Classical X13** (PROMOTION REVOKED IN PHASE 0; FROZEN EXPERIMENTAL PLATFORM)

---

## 2. Adjudication of Preregistered Qualification Gates

| Gate ID | Objective | Opponent & TC | Empirical Result | Gate Status | Promotion Impact |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Gate 1** | Single-Thread Non-Inferiority | X7 (1T) @ 1.0s+50ms (200 games) | 80.5 / 200 (**40.25%**), $-68.6$ Elo, $p = 0.0014$ | **FAILED** | X7 strictly retained as 1T baseline |
| **Gate 2** | 4-Thread Strength Qualification | X12 (4T) @ 1.0s+50ms (200 games) | 97.5 / 200 (**48.75%**), $-8.7$ Elo, $p = 0.6518$ | **FAILED** ($p > 0.05$) | X12 strictly retained as 4T baseline |
| **Gate 3** | Slow Time Control Verification | X12 (4T) @ 3.0s+100ms (100 games) | 50.5 / 100 (**50.50%**), $+3.5$ Elo, $p = 0.8981$ | **PASSED** (Parity Verified) | Time-control reversal eliminated |
| **Gate 4** | Experimental Separation | Tablebases disabled in standard play | $100\%$ Classical Algorithmic Execution | **PASSED** | Methodological purity preserved |

---

## 3. Scientific and Architectural Rationale

### 3.1 Why X14 Cannot Be Promoted over X7 (Single-Thread)
In Match A, Candidate X14 scored **$40.25\%$** against X7 ($p = 0.0014 < 0.01$). This statistically significant negative margin proves that adding 14 handcrafted evaluation terms and thread-local pawn caching introduces an unamortizable latency drag on a single CPU core. X7's ultra-minimalist Flat E5 evaluation remains the fastest, deepest, and strongest classical single-thread architecture in the Janus lineage.

### 3.2 Why X14 Cannot Be Promoted over X12 (4-Thread)
In Match B, Candidate X14 scored **$48.75\%$** against X12 ($p = 0.6518 \gg 0.05$). Under standard scientific hypothesis testing:
$$H_0: \Delta\text{Elo} = 0 \quad \text{vs.} \quad H_1: \Delta\text{Elo} > 0$$
With $t = -0.4527$ and $p = 0.652$, we fail to reject the null hypothesis. There is no statistically significant evidence that X14 is stronger than X12 in tournament play.

In Match C (slower time control across 100 games), X14 scored **$50.50\%$** ($p = 0.8981$). This confirms that X14 and X12 are in near-perfect empirical equilibrium. Promoting an engine that displays exact parity with the control violates the core mission of Project Janus.

### 3.3 Genuine Research Breakthroughs Delivered by P1.9
Although X14 did not achieve a competitive Elo advancement over X12, Milestone P1.9 delivered profound structural and methodological advancements:
1. **Resolution of P1.8 Promotion Error:** Restored scientific integrity to the project by demonstrating that P1.8's promotion of X13 was statistically invalid ($p = 0.218 > 0.05$), formally updating the historical registry.
2. **Elimination of the Time-Control Reversal:** In P1.8, Match C suggested an alarming drop to $41.25\%$ at 3.0s. Phase 7 and Phase 9 proved conclusively that this was a small-sample artifact ($N=40$); at 100 games, X14 maintains full parity ($50.5\%$) with zero degradation.
3. **Multi-Cause Failure Atlas (F7: 63.4%):** Proved empirically across 240 positions that computer chess failures against modern engines cannot be reduced to single-cause silos; evaluation bias systematically distorts search selectivity.
4. **Hardware Cache Architecture:** Identified the physical 2.0 MB L2 cache boundary per core and designed the 16K thread-local pawn hash ($512\text{ KB}$, 25.0% L2 occupancy) delivering $4.76\text{ ns/probe}$ without thread bus contention.
5. **Syzygy Tablebase Infrastructure:** Complete integration of the Ronald de Man standard with full UCI options and verified zero-overhead graceful fallback.

---

## 4. Lineage Summary Table

| Engine | Milestone | Status | 1T Baseline | 4T Baseline | Architecture Key |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Janus Classical X7** | P1.2 | **QUALIFIED 1T BASELINE** | **YES** | — | Staged Movegen + LMR L3 + ContHist H3 + Flat Eval E5 |
| **Janus Classical X10** | P1.5 | Advanced Eval Reference | No | — | Enhanced Eval E10 + 64K Pawn Hash + Dynamic Time |
| **Janus Classical X12** | P1.7 | **QUALIFIED 4T BASELINE** | — | **YES** | 64B TT + Smart Eviction + Warm History + Safe LMP + E10 |
| **Janus Classical X13** | P1.8 | Experimental Platform | No | No (Revoked) | 16K Thread-Local Pawn Hash + Safe LMP |
| **Janus Classical X14** | P1.9 | **Advanced Research Platform** | No | No (Parity) | Refined Eval E11 + 16K Thread-Local Hash + Syzygy Engine |
