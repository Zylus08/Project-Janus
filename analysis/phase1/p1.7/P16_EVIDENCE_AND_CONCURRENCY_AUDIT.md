# Project Janus — Phase 1, Milestone P1.7
## Phase 0: P1.6 Evidence Reconciliation & Concurrency Audit

**Date:** 2026-11-11  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Evaluator:** Principal Computer Chess Engineer, Concurrency Specialist & Independent Statistical Auditor  
**Scope:** Forensic reconciliation of Milestone P1.6 data, re-computation of paired tournament statistics from raw PGNs, and structural audit of the shared Transposition Table memory layout and synchronization protocol.

---

### 1. Executive Reconciliation Summary

All empirical measurements and benchmark figures reported in Milestone P1.6 were independently audited from the raw PGN archives, JSON telemetry files, and C++ engine source code:

| Metric / Experiment | Reported in P1.6 | Independently Verified | Audit Determination |
| :--- | :---: | :---: | :--- |
| **X11 (1T) vs X7 (1T) Score** | 99.5 / 200 (49.75%) | **99.5 / 200 (49.75%)** | **CONFIRMED** (69W - 61D - 70L across 100 pairs) |
| **X11 (4T) vs X7 (1T) Score** | 14.0 / 40 (35.00%) | **14.0 / 40 (35.00%)** | **CONFIRMED** (9W - 10D - 21L across 20 pairs) |
| **X11 (1T) vs SF19 (1T) Score** | 2.0 / 40 (5.00%) | **2.0 / 40 (5.00%)** | **CONFIRMED** (0W - 4D - 36L; 4 resilient draws) |
| **X11 (4T) vs SF19 (4T) Score** | 0.5 / 40 (1.25%) | **0.5 / 40 (1.25%)** | **CONFIRMED** (0W - 1D - 39L across 20 pairs) |
| **2T Throughput Speedup** | 1.96x (97.8% eff) | **1.96x (97.8% eff)** | **CONFIRMED** (2,689,855 NPS vs 1,375,725 NPS) |
| **4T Throughput Speedup** | 3.26x (81.5% eff) | **3.26x (81.5% eff)** | **CONFIRMED** (4,485,095 NPS vs 1,375,725 NPS) |
| **Single-Thread LMP Node Delta** | 11.8% reduction | **11.8% reduction** | **CONFIRMED** (12,525,568 vs 14,209,024 nodes) |
| **Single-Thread TT Overhead** | 2.3% throughput cost| **2.3% throughput cost** | **CONFIRMED** (1,606,942 vs 1,645,763 NPS) |

---

### 2. Independent Re-computation of Tournament Statistics

Every game in the four P1.6 PGN files was re-parsed move by move using `python-chess` to verify outcomes, paired scoring, and statistical test parameters.

#### Tournament Summary Table

| Tournament File | Games (Pairs) | W - D - L | Score (%) | Elo Diff | Clustered 95% CI | Paired $t$-stat | Degrees of Freedom | $p$-value (Reported Norm) | $p$-value (Exact Student-$t$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `x11_1t_vs_x7.pgn` | 200 (100) | 69 - 61 - 70 | 99.5 (49.75%) | −1.7 | [−87.1, +83.4] | $t = -0.0815$ | $df = 99$ | $p = 0.9350$ | $p = 0.9352$ |
| `x11_4t_vs_x7_1t.pgn` | 40 (20) | 9 - 10 - 21 | 14.0 (35.00%) | −107.5 | [−309.7, +39.1] | $t = -2.8536$ | $df = 19$ | $p = 0.0043$ | **$p = 0.0101$** |
| `x11_1t_vs_sf19.pgn` | 40 (20) | 0 - 4 - 36 | 2.0 (5.00%) | −511.5 | [−800.0, −315.4] | $t = -19.6150$ | $df = 19$ | $p < 0.0001$ | $p < 0.0001$ |
| `x11_4t_vs_sf19_4t.pgn` | 40 (20) | 0 - 1 - 39 | 0.5 (1.25%) | −759.1 | [−800.0, −473.4] | $t = -39.0000$ | $df = 19$ | $p < 0.0001$ | $p < 0.0001$ |

#### Statistical Methodology Audit:
1. **Four-Thread Match 2 Significance:**  
   In Match 2 (X11 4T vs X7 1T), 20 paired matches were contested. The correct degrees of freedom for the clustered paired sample is $df = N_{\text{pairs}} - 1 = 19$.  
   The historical P1.6 script computed $p$ using a standard normal approximation ($z = -2.8536 \implies p = 0.0043$).  
   Evaluating the exact Student's $t$-distribution with $df = 19$ yields:
   - Two-sided $p$-value: **$p = 0.0101$**
   - One-sided $p$-value: **$p = 0.0050$**
   While both confirm statistically significant regression ($p < 0.05$), the exact Student's $t$ distribution should be reported for small sample sizes ($N \le 30$).
2. **Proper Interpretation of $p = 0.935$ in Match 1:**  
   In Match 1 (X11 1T vs X7 1T), the paired $t$-test yielded $p = 0.9350$.  
   **Crucial Statistical Mandate:** A high $p$-value ($p = 0.9350$) does **not** prove statistical equivalence. In Neyman-Pearson hypothesis testing, failing to reject the null hypothesis ($H_0: \Delta = 0$) simply indicates insufficient statistical evidence to assert a difference. The 95% confidence interval spanning $[−87.1, +83.4]$ Elo demonstrates substantial uncertainty; equivalence testing requires a formal two one-sided test (TOST) within a pre-registered equivalence margin $[-\delta, +\delta]$, which was not satisfied.

---

### 3. Mandatory Shared TT Architecture Reconciliation

A critical contradiction in historical Milestone P1.6 documentation was the conflation of the terms **"lockless"** and **"spinlock-protected"**. An exhaustive source and binary layout audit of `ParallelTranspositionTable` resolves this discrepancy.

#### A. Actual Synchronization Mechanism
The implementation in `engine/classical_x/janus_classical_x.cpp` and `control/janus_classical_x11.cpp` is:
```cpp
struct alignas(64) TTCluster {
    std::atomic_flag lock;
    TTEntry entries[4];
};

bool ParallelTranspositionTable::probe(...) {
    ...
    while (c.lock.test_and_set(std::memory_order_acquire)) {
        _mm_pause();
    }
    // ... read operations ...
    c.lock.clear(std::memory_order_release);
    return hit;
}
```
- **Determination:** This is **strictly NOT lockless**. It is a **coarse per-cluster spinlock mutual-exclusion table**.
- A lockless / lock-free Transposition Table utilizes lock-free atomic read/write primitives (such as atomic 64-bit/128-bit load/store instructions or XOR-hash validation) where no thread ever waits for another thread to release a lock.
- In Candidate X11, concurrent probes or stores addressing the same cluster index serialize on `c.lock.test_and_set()`.

#### B. Memory Layout and Cache Alignment Deconstruction
Compiling a diagnostic verification binary under MSVC x64 reveals the exact compiler layout of `TTCluster`:
- `sizeof(TTEntry)`: **16 bytes** (`key`: 8B, `score`: 2B, `depth`: 1B, `flag`: 1B, `age`: 1B, `pad`: 1B, `best_move`: 2B).
- `sizeof(std::atomic_flag)`: **4 bytes** in MSVC x64.
- `offsetof(TTCluster, lock)`: **byte 0**.
- `offsetof(TTCluster, entries)`: **byte 8** (compiler inserts 4 bytes of padding after `lock` to satisfy `alignof(uint64_t) = 8`).
- Span of `entries[4]`: 64 bytes, occupying bytes 8 through 71.
- Total raw bytes needed: $8 + 64 = 72$ bytes.
- Effect of `alignas(64)`: Because 72 bytes exceeds 64 bytes, MSVC pads the struct to the next multiple of 64: **`sizeof(TTCluster) = 128 bytes`**!

```
TTCluster Memory Layout (128 Bytes, Spanning Two 64-Byte Cache Lines):
Cache Line 0 (Bytes 0..63):
[ Lock (4B) ][ Pad (4B) ][ Entry 0 (16B) ][ Entry 1 (16B) ][ Entry 2 (16B) ][ Entry 3 part (8B) ]
Cache Line 1 (Bytes 64..127):
[ Entry 3 rest (8B) ][ Unused Compiler Tail Padding (56 Bytes) .................................. ]
```

#### C. Full Allocation and Efficiency Accounting
For `NUM_TT_CLUSTERS = 262,144`:
- **Total Heap Allocation:** $262,144 \times 128\text{ bytes} = \mathbf{33,554,432\text{ bytes}}$ (**exactly 32.0 MB**).
- **Useful TT Data (`entries`):** $262,144 \times 64\text{ bytes} = \mathbf{16,777,216\text{ bytes}}$ (**50.0%**).
- **Synchronization Data (`lock`):** $262,144 \times 4\text{ bytes} = \mathbf{1,048,576\text{ bytes}}$ (**3.1%**).
- **Dead Padding / Alignment Waste:** $262,144 \times 60\text{ bytes} = \mathbf{15,728,640\text{ bytes}}$ (**46.9%**).

#### Severe Architectural Consequences:
1. **Cache Line Split:** Every cluster straddles two distinct 64-byte L1/L2 cache lines. Accessing Entry 3 requires two separate cache line fills.
2. **Cache Capacity Halved:** 15.73 MB of CPU cache is wasted storing zero-padding.
3. **Lock Bouncing:** When a thread acquires `c.lock`, it invalidates Cache Line 0 on all other cores, forcing cache coherence traffic across cores even if another thread only wants to read Entry 0 or 1.

This discovery establishes the primary suspect for Phase 1 and Phase 2 investigation into why multithreading degraded playing strength.

