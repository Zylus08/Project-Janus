# Project Janus v0.49 — Native Performance Evaluation

**Milestone:** Project Janus v0.49  
**Parent Baseline Commit:** `6b46eb4` (v0.48 Final)  
**Evaluated Configurations:**
- **Baseline K0:** Standard eager sorting (`moves.sort(key=...)`)
- **Candidate L1:** Lazy two-phase move selection (TT immediate yield $\to$ deferred sort)
- **Candidate N1:** Native C DLL stable partial sort via `ctypes`
**Telemetry Data:** `analysis/v0.49/raw/microbenchmarks_raw.json` & `analysis/v0.49/raw/n1_search_benchmark_raw.json`

---

## 1. Microbenchmark Findings (Phase E1)

Microbenchmarks measured the sorting of move arrays with realistic score distributions (TT move, 2–4 captures, 2 killers, quiets):

| Candidate Move Count ($N$) | Python Eager Sort (`list.sort`) | Native Batch Partial Sort | Native Per-Move Call | Relative Speedup (Native vs Py Eager) |
|---|---:|---:|---:|---:|
| **$N = 10$** | **1.30 µs** | 3.40 µs | 4.30 µs | -161% (Slower) |
| **$N = 25$** | **3.40 µs** | 5.40 µs | 8.10 µs | -58.8% (Slower) |
| **$N = 35$** | **5.20 µs** | 7.00 µs | 10.30 µs | -34.6% (Slower) |
| **$N = 50$** | 9.50 µs | **8.60 µs** | 13.80 µs | **+9.4% (Faster)** |
| **$N = 75$** | 10.60 µs | 11.60 µs | 20.70 µs | -9.4% (Slower) |

### Key Insight:
CPython's internal `list.sort()` is already a highly optimized C implementation (Timsort in `Objects/listobject.c`). For typical chess positions ($N \approx 25\text{--}40$ moves), the boundary cost of allocating `(ctypes.c_int * n)` in Python and passing pointers into C offsets any algorithmic advantage of native sorting.

---

## 2. Fixed-Depth Search Performance (Phase E2)

Evaluated across the 37-position diagnostic corpus at Depth 4:

| Metric | Baseline K0 | Candidate L1 | Candidate N1 | N1 vs K0 Delta |
|---|---:|---:|---:|---:|
| **Total Search Nodes** | 405,197 | 407,705 | **405,197** | **0.00%** |
| **Total Wall-Clock Time** | 19.35 s | 19.36 s | 20.63 s | **+6.66% (Slower)** |
| **Measured Ordering Time** | 1.562 s | 1.423 s | **0.746 s** | **-52.2% (Faster)** |
| **NPS Throughput** | 20,940 | 21,059 | 19,641 | **-6.20%** |
| **Node Matches to K0** | 37 / 37 | 35 / 37 | **37 / 37** | **100.0%** |
| **Move Matches to K0** | 37 / 37 | 36 / 37 | **37 / 37** | **100.0%** |

### Decomposition of the Search Paradox:
Why did N1's wall-clock search time increase by $+6.66\%$ even though its measured ordering time dropped from $1.562\text{ s}$ to $0.746\text{ s}$ ($-52.2\%$)?
1. **List Pre-Evaluation Overhead:** In K0, `moves.sort(key=...)` computes keys lazily on demand inside CPython's sorting loop. In N1, Python must evaluate `scores = [self._move_order_score(...) for m in moves]` before passing the array to C. This intermediate list comprehension adds Python interpreter bytecode overhead.
2. **Ctypes Array Marshalling:** Constructing `(ctypes.c_int * n)(*scores)` and `(ctypes.c_int * n)()` creates two temporary C-type buffer objects on every node search, adding Python garbage collection pressure.
3. **Conclusion:** While the C kernel itself executes in nanoseconds, wrapping it with `ctypes` at every node incurs a net deficit.

---

## 3. Performance Acceptance Evaluation (Phase E3)

| Preregistered Acceptance Criterion | Candidate N1 Status | Evaluation |
|---|---|---|
| **Criterion 1: Exact intended selection behaviour** | **PASS** | 100.0% identical to K0 in all 37 positions. |
| **Criterion 2: Reproducible build** | **PASS** | Automated build via MSVC BuildTools `cl.exe`. |
| **Criterion 3: No correctness regression** | **PASS** | 0 blunders, 0 tactical regressions. |
| **Criterion 4: Material ordering-time reduction** | **PASS** | Ordering time cut from 1.562s to 0.746s ($-52.2\%$). |
| **Criterion 5: Material end-to-end runtime improvement** | **FAIL** | End-to-end runtime regressed by $+6.66\%$. |

**Phase E Verdict:** Candidate N1 fails Criterion 5. A microbenchmark or ordering-time win that does not translate into an end-to-end search runtime improvement cannot be promoted.

