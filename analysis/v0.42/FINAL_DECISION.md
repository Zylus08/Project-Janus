# Project Janus v0.42 — Final Decision and Recommendation Framework

**Milestone:** v0.42 — RFP Replication, Rule-Accurate Draw Semantics & Strength Attribution  
**Date:** 2026-11-03  
**Status:** FINAL & APPROVED  

---

## 1. Milestone Decision

### **DECISION: QUALIFIED AS PRODUCTION FEATURE — PROMOTED TO RECOMMENDED SEARCH ENGINE ENHANCEMENT**

Based on the completion and passage of all 12 validation gates, Candidate RFP is officially **QUALIFIED AND CONFIRMED** as a high-performing, tactically reliable playing strength enhancement for Project Janus.

---

## 2. Evidence Synthesis

1. **Direct Paired Strength Attribution:**
   - In direct, paired, opening-matched ablation against Baseline K0 on 25 colour-reversed pairs (50 games each), Candidate RFP achieved:
     $$\bar{\Delta} = +0.5800\text{ points/pair } (+29.0\%\text{ per game})$$
     $$t = 2.7682, \quad p = 0.005345 \quad (p < 0.01)$$
     $$95\%\text{ Bootstrap CI: } [+9.0\%, +49.0\%]\text{ per game}$$
   - The null hypothesis ($H_0: \mu_\Delta \le 0$) is decisively rejected.

2. **Search Tree Efficiency:**
   - Evaluated across the 16-position tactical diagnostic suite at depth 4:
     - Baseline K0: 86,381 nodes, 4.665s
     - Candidate RFP: 73,840 nodes, 4.004s
     - **Tree reduction: -14.52% nodes, -14.18% time**.

3. **Tactical Invariants & Correctness:**
   - Zero tactical regressions observed (13/16 tactical positions solved, identical to baseline).
   - 21 unit tests covering RFP invariants, draw detection, and quiescence pass cleanly.
   - All 451 project unit tests pass.

4. **Draw Semantics Compliance:**
   - Automatic 75-move draw (`is_seventyfive_moves()`) verified across all search phases.
   - Automatic fivefold repetition verified.
   - Claimable 50-move rule correctly excluded from automatic draw triggers.
   - Draw proximity guard (`halfmove_clock < 140`) successfully suppresses pruning near 75 moves.

---

## 3. Configuration & Deployment Policy

- **Engine Flag:** `--enable-rfp`
- **Default Parameter Tuning:**
  - `rfp_max_depth = 2` (pruning confined strictly to shallow frontier plies)
  - `rfp_margin_per_depth = 120` (margin = depth × 120 cp)
- **Deployment Status:**
  - In `JanusSearch` and `janus.uci`, RFP is fully operational, verified, and accessible via the `--enable-rfp` switch.
  - To maintain absolute backwards compatibility with existing test suites that verify default engine instantiation (including `test_01_rfp_disabled_by_default`), the core default remains explicit via `--enable-rfp`, with clear guidance that all competitive match configurations should enable RFP.

---

## 4. Acceptance Gate Matrix (Gates A through L)

| Gate | Category | Criteria | Observed Value | Verdict |
|:---:|:---|:---|:---:|:---:|
| **Gate A** | Repository & Environment Freeze | Clean working tree, documented starting HEAD | Verified (`1d509d0`) | **PASS** |
| **Gate B** | v0.41 Statistical Audit | Verification of W/D/L, t-stat, bootstrap CI | All formulas recomputed & confirmed | **PASS** |
| **Gate C** | Configuration & Implementation Audit | Guard conditions, fail-hard return semantics verified | Full source audit completed | **PASS** |
| **Gate D** | Draw Semantics Audit | Automatic vs claimable draw distinction verified | All 7 draw tests pass | **PASS** |
| **Gate E** | Tactical Correctness & Invariants | 0 tactical regressions in diagnostic suite | 13/16 solved (parity with K0) | **PASS** |
| **Gate F** | Search Efficiency | Node reduction $\ge 5\%$ without NPS collapse | -14.52% nodes, NPS stable | **PASS** |
| **Gate G** | Preregistration Integrity | Hypotheses & endpoints frozen prior to ablation | Registered in `analysis/v0.42/` | **PASS** |
| **Gate H** | Direct Paired Ablation | Paired $t$-test $p < 0.05$, positive delta | $\bar{\Delta} = +0.58$, $p = 0.0053$ | **PASS** |
| **Gate I** | Replication & Cross-Check | Independent verification across both matches | 25/25 openings matched | **PASS** |
| **Gate J** | Clean-Room Independent Audit | End-to-end execution of audit script | `VERIFIED_VALID` | **PASS** |
| **Gate K** | Baseline Preservation | No uncommitted modifications, zero regression | 451/451 tests pass | **PASS** |
| **Gate L** | Documentation & Provenance | Complete reports, manifests, and digests | Complete in `analysis/v0.42/` | **PASS** |
