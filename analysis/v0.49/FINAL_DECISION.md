# Project Janus v0.49 — Final Optimization Decision

**Milestone:** Project Janus v0.49  
**Parent Baseline Commit:** `6b46eb4` (v0.48 Final)  
**Evaluated Candidates:**
- **Baseline K0:** Standard eager move ordering (`enable_lazy_move_selection=False`, `enable_rfp=False`)
- **Candidate L1:** Lazy move selection reference (`enable_lazy_move_selection=True`)
- **Candidate N1:** Native C DLL stable partial sort via `ctypes`
- **Candidate H1:** Flattened 1D 4096-element integer history array
- **Candidate H2:** Stage-separated lazy quiet history scoring
- **Candidate K1:** Multi-stage lazy move selector with killer priority

---

## 1. Selected Milestone Outcome: CATEGORY B

> ### **Category B: Efficiency Improvement Retained, Strength Unconfirmed**
> **Baseline K0 remains the immutable production default (`enable_lazy_move_selection=False`, `enable_rfp=False`).**  
> **Candidate L1 is retained as an experimental configuration (`enable_lazy_move_selection=True`).**  
> **Candidates N1, H1, H2, and K1 are rejected for production promotion due to interpreter boundary overheads, remaining available strictly as diagnostic reference implementations.**

---

## 2. Evaluation Against Formal Decision Criteria

| Category | Preregistered Criteria | Qualification Assessment |
|---|---|---|
| **Category A: Native Optimization Qualified** | Demonstrates correctness, reproducible end-to-end runtime benefit, acceptable fixed-time decision quality, and strength evidence for promotion review. | **DOES NOT QUALIFY.** While Candidate N1 achieved 100.0% node-for-node correctness and cut ordering time by $-52.2\%$, end-to-end search runtime regressed by $+6.66\%$ due to ctypes marshalling. No native speedup was realized. |
| **Category B: Efficiency Improvement Retained, Strength Unconfirmed** | A candidate demonstrates measurable runtime improvement, but playing strength remains unconfirmed. Production default unchanged. | **QUALIFIES FULLY.** Inherited Candidate L1 retains its validated $-17.68\%$ runtime reduction at Depth 5 with 95.95% exact agreement with K0 and zero regressions. Production default remains strictly K0. |
| **Category C: Candidate Regression** | A candidate introduces correctness, portability, performance, or decision-quality regressions that outweigh benefits. | **APPLIES TO CANDIDATES N1, H1, H2, K1.** Each introduced runtime overhead in interpreted Python ($+6.66\%$, $+27.4\%$, $+1.94\%$, $+4.31\%$) that offsets their theoretical advantages. |
| **Category D: Inconclusive** | Inconsistent results, unexplained divergences, or insufficient statistical power. | **DOES NOT APPLY.** All results were reproduced consistently across microbenchmarks, fixed-depth tests, and fixed-time ladders. |

---

## 3. Evidentiary Synthesis

### 3.1 The Micro-Kernel Paradox (Candidate N1)
The central hypothesis of v0.49 asked whether moving move selection into native compiled code could eliminate Python ordering overhead.
- **Microbenchmarks:** Demonstrated that for small move arrays ($N \le 35$), CPython's internal C-implemented `list.sort()` (Timsort) is actually faster ($1.3\text{--}5.2\ \mu\text{s}$) than calling an external C DLL via `ctypes` ($3.4\text{--}7.0\ \mu\text{s}$) because array allocation and pointer marshalling in `ctypes` costs $\sim 2.5\ \mu\text{s}$ per call.
- **Search Equivalence:** Candidate N1 proved that native C selection can achieve **exact 100.0% node-for-node identity to K0 (405,197 nodes at Depth 4)** and reduce pure sorting time by **$-52.2\%$** (from 1.562s to 0.746s).
- **The Bottleneck:** Pre-evaluating move scores into a Python list comprehension before passing them to C incurred more interpreter bytecode overhead than the C DLL saved, resulting in a $+6.66\%$ net wall-clock search slowdown.

### 3.2 The Staged Laziness Principle (Candidate H2 & K1)
- **Candidate H2:** Demonstrated that stage-separating move ordering into Tactical First $\to$ Quiets Deferred eliminates **69.6% of all quiet history lookups** (saving 670,392 lookups across 37 positions at Depth 4).
- **Candidate K1:** Prioritized 37,985 killer moves before quiets while preserving 97.3% move agreement with K0.
- **Interpreter Overhead:** In pure Python, creating intermediate lists (`caps`, `killers`, `quiets`) inside generator closures costs more CPU time than sorting a single flat list using Python's native C `list.sort()`.

### 3.3 The Supremacy of Candidate L1's Two-Phase Design
Candidate L1 remains the only move-ordering optimization that delivers a net wall-clock speedup ($-17.68\%$ at Depth 5) in interpreted Python. It succeeds because:
1. It does NOT create multiple sub-lists or intermediate score arrays.
2. It tests a single object (`tt_move`) in $O(1)$.
3. If the TT move cuts off (which occurs in 21.4% of cutoffs), it avoids the entire sort.
4. If the TT move fails to cut off, it falls back immediately to Python's built-in C `list.sort()` with zero extra partitioning.

---

## 4. Production Configuration for v0.50

The production default configuration remains completely frozen:

```python
# Production Configuration (Frozen Baseline Reference)
enable_lazy_move_selection = False   # K0 production default
enable_rfp = False                  # Retained experimental, disabled by default

# Experimental Feature Flags
# Candidate L1: enable_lazy_move_selection = True
```

---

## 5. Strategic Recommendations for Future Milestones

1. **Monolithic C Move Generator & Search (Cython / C++):**
   - Micro-kernel offloading (calling native functions for small sub-tasks like sorting 30 moves) is fundamentally bottlenecked by Python/native boundary costs. A native implementation will only yield large performance dividends if move generation, move ordering, and alpha-beta recursion reside together in compiled C/C++, eliminating Python boundary crossings entirely.
2. **Retain L1 as Production Candidate in Compiled Architecture:**
   - The algorithmic principles validated in v0.47–v0.49 (TT-first immediate cutoff, staged tactical-first quiets-deferred, and 2-slot killers) are sound and will produce massive speedups once implemented within a compiled engine core.

