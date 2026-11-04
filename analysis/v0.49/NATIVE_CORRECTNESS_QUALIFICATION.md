# Project Janus v0.49 — Native Correctness Qualification

**Milestone:** Project Janus v0.49  
**Parent Baseline Commit:** `6b46eb4` (v0.48 Final)  
**Evaluated Binary:** `analysis/v0.49/native/move_picker.dll` (ABI 4901)  
**Test Suite:** `analysis/v0.49/run_native_correctness.py`  
**Search Benchmark:** `analysis/v0.49/run_n1_search_benchmark.py`

---

## 1. Executive Disposition: HARD GATE PASSED

Candidate N1 has successfully met all preregistered correctness requirements:
1. **Ordering Equivalence (D1):** Exact 100.0% match with Python eager ordering across all edge cases (extreme scores, negative scores, empty lists, large branching factors up to 200 moves).
2. **Move Integrity (D2):** Zero duplicate indices, zero omissions, zero out-of-bounds memory accesses, zero input mutations.
3. **Search Equivalence (D3):** **Exact 100.0% node-for-node (405,197 vs 405,197 nodes) and move-for-move identity to K0** across all 37 positions of the diagnostic corpus at Depth 4.
4. **Fault & Fallback Integrity (D4):** Seamless degradation to pure-Python reference on simulated DLL absence.

---

## 2. Test Suite Audit Details

| Test ID | Test Category | Conditions | Result |
|---|---|---|---|
| **Test 1** | Edge Cases | Empty list, single-element list ($N=0, 1$) | **PASS** (100% match) |
| **Test 2** | Extreme & Negative Scores | Scores from $-2,147,483,640$ to $+2,147,483,640$ | **PASS** (100% match) |
| **Test 3** | Strict Stability Under Collisions | All scores equal ($100 \dots 100$) for $N \in \{2, 5, 10, 25, 50\}$ | **PASS** (100% generation order preserved) |
| **Test 4** | Large Branching Factors & Heavy Ties | 100 random trials with $N \in [2, 200]$, narrow score range | **PASS** (100% match with Python reference) |
| **Test 5** | Incremental vs Partial Sort | Next-best selection vs full partial sort | **PASS** (100% permutation identity) |
| **Test 6** | Fault and Fallback | Simulated missing DLL, invalid dimensions | **PASS** (Graceful fallback) |

---

## 3. Search Tree Equivalence (Phase D3)

Evaluating Candidate N1 against Baseline K0 and Candidate L1 across all 37 positions at Depth 4:

| Metric | Baseline K0 | Candidate L1 | Candidate N1 | N1 vs K0 Fidelity |
|---|---:|---:|---:|---:|
| **Total Nodes** | **405,197** | 407,705 | **405,197** | **100.0% Exact Match** |
| **Position Node Matches** | 37 / 37 | 35 / 37 | **37 / 37** | **100.0% (37/37)** |
| **Best Move Agreement** | 37 / 37 | 36 / 37 | **37 / 37** | **100.0% (37/37)** |
| **Root Score Agreement** | 37 / 37 | 35 / 37 | **37 / 37** | **100.0% (37/37)** |
| **Tactical Regressions** | 0 | 0 | **0** | **0 Regressions** |
| **Blunder Count** | 0 | 0 | **0** | **0 Blunders** |

Candidate N1 is the first move-ordering candidate in Project Janus that achieves **absolute, bit-level search-tree equivalence to Baseline K0** while delegating move selection to native C.

