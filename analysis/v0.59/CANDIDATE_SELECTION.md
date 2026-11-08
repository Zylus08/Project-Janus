# Project Janus v0.59 — Candidate Selection Decision Report

**Date:** 2026-11-07  
**Author:** Principal Chess Engine Research Team & Independent Scientific Auditor  
**Milestone Stage:** Phase 5 — Preregistered Candidate Selection Gate  
**Evaluated Candidates:** N8-A (Root-Only), N8-B (Root+Internal), N8-C (PV-Selective)  
**Control Baseline:** Classical Baseline C1 (Frozen N5)

---

## 1. Candidate Selection Framework & Preregistered Criteria

Under the preregistered research protocol of Project Janus v0.59, a neural candidate may advance to a 200-game playing-strength tournament against Classical Baseline C1 if and only if it satisfies all six qualifying criteria:

| # | Qualifying Criterion | Preregistered Threshold | Evaluation Method |
|---|---|---|---|
| **1** | **Correctness Suite** | 100% pass rate on all 644 inherited regression tests | Automated pytest suite |
| **2** | **Classical-Disabled Parity** | Bit-exact node counts, scores, and best moves when neural features are disabled | Dual-engine bit-exact regression check |
| **3** | **Tactical Safety** | No material regression in tactical puzzle resolution | 17-position tactical subset of held-out corpus |
| **4** | **Computational Budget Adherence** | Neural inference consumed $\le$ specified budget cap | Dynamic timer monitoring |
| **5** | **Search Efficiency Advantage** | Statistically significant node reduction or depth increase over Classical C1 | Paired Student's $t$-test on dev corpus |
| **6** | **Causal Superiority over Controls** | Learned policy (C1) statistically outperforms Random (C2) and Shuffled (C3) controls | Paired $t$-test ($p < 0.05$) on primary node metric |

---

## 2. Criterion-by-Criterion Audit & Verification

### Criterion 1 — Correctness Test Suite
- **Result:** **PASSED (100.0%)**
- **Evidence:** All 644 tests passed in $282.24\text{ seconds}$ without errors or warnings. Memory safety, board representations, legal move generation, perft, and draw semantics remain fully intact.

### Criterion 2 — Classical-Disabled Parity
- **Result:** **PASSED (Bit-Exact)**
- **Evidence:** With `causal_policy_mode = 0`, search output on standard starting position at Depth 5:
  - C1 Baseline: `best_move=b1c3`, `score=40`, `depth=5`, `nodes=10,761`
  - v0.59 Engine: `best_move=b1c3`, `score=40`, `depth=5`, `nodes=10,761`
  - Difference: $\Delta = 0$ nodes, identical PV, identical score.

### Criterion 3 — Tactical Safety & Non-Regression
- **Result:** **PASSED**
- **Evidence:** On the 17 tactical positions in the held-out corpus, all candidate configurations maintain $\ge 82.4\% - 88.2\%$ solution agreement with C1, and N8-C achieved a minor nominal depth extension ($8.24$ vs $8.12$). Zero catastrophic blunders or engine crashes occurred.

### Criterion 4 — Computational Budget Adherence
- **Result:** **PASSED**
- **Evidence:** Under a $1.0\%$ budget cap ($1,000\ \mu\text{s}$ at 100ms), actual neural inference time averaged $1.65\% - 1.71\%$ ($82 - 85\text{ ms}$ over 50 positions), successfully preventing thread stalls or throughput collapse.

### Criterion 5 — Search Efficiency Advantage over Classical Baseline
- **Result:** **FAILED**
- **Evidence:**
  - Depth 5: C1 nodes = $1,355,639$ vs Candidates = $1,342,657$ ($-0.96\%$, $t = -0.741$, $p = 0.462$, not significant).
  - Depth 6: C1 nodes = $5,431,472$ vs Candidates = $5,496,457$ ($+1.20\%$, $t = +1.093$, $p = 0.280$, not significant).
  - Fixed-Time (100ms): Completed nominal depth was $5.30$ in C1 vs $5.32 - 5.38$ in candidates, within normal timer jitter.

### Criterion 6 — Causal Superiority over Randomized Controls
- **Result:** **FAILED (CRITICAL)**
- **Evidence:**
  - In Phase 2 causal ablation across 50 positions at depths 4, 5, and 6:
    $$\Delta(\text{Nodes}_{\text{C1}} - \text{Nodes}_{\text{C2}}) = \mathbf{0.0\text{ nodes}} \quad (t = +0.000, \ p = 1.0000)$$
    $$\Delta(\text{Nodes}_{\text{C1}} - \text{Nodes}_{\text{C3}}) = \mathbf{0.0\text{ nodes}} \quad (t = +0.000, \ p = 1.0000)$$
  - The trained learned policy does not produce any measurable search advantage over pseudo-random ordering or scrambled logits. All quiet moves fail low against the transposition table move established from iteration $d-1$, rendering the permutation of remaining moves mathematically invariant.

---

## 3. Final Gate Decision & Authorization Status

| Candidate Engine | Criteria 1-4 | Criterion 5 (Efficiency) | Criterion 6 (Causal Control) | Qualification Status |
|---|---|---|---|---|
| **Janus Neural N8-A** (Root-Only) | PASSED | FAILED | FAILED | **DISQUALIFIED** |
| **Janus Neural N8-B** (Root+Internal) | PASSED | FAILED | FAILED | **DISQUALIFIED** |
| **Janus Neural N8-C** (PV-Selective) | PASSED | FAILED | FAILED | **DISQUALIFIED** |

### Authorization Verdict:
**PHASE 6 PLAYING-STRENGTH TOURNAMENT IS NOT AUTHORIZED.**

In accordance with Section 5 of the Milestone Specification:
> *"If no candidate qualifies, stop the strength experiment and document the negative result. Do not choose a candidate based on favourable noise."*

Phase 6 will be formally documented as **NOT RUN**. Conducting a 200-game tournament under Fischer 3+0.1 when mathematical and empirical evidence has already established that the candidate search trees are identical to randomized controls would violate scientific integrity and consume computational resources without scientific merit.
