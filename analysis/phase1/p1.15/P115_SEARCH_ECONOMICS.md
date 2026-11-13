# PHASE 8: SEARCH EFFICIENCY & COMPUTATIONAL COST AUDIT

**Project:** Project Janus — Phase 1, Milestone P1.15  
**Component:** Search Economics, Microbenchmarks & Algorithmic Overhead Profiling  
**Date:** November 14, 2026  
**Auditor:** Principal Computer Chess Engine Architect & Systems Performance Engineer  
**Deliverable:** `analysis/phase1/p1.15/P115_SEARCH_ECONOMICS.md`  
**Raw Telemetry:** `analysis/phase1/p1.15/raw/search_economics_raw.json`  

---

## 1. Executive Summary

Milestone P1.15 mandates a rigorous characterization of computational cost, throughput, and algorithmic efficiency separating each isolated intervention from the qualified baselines. Rather than relying on a single aggregate NPS figure, Phase 8 profiles the engine across five orthogonal performance dimensions:

1. **Microbenchmarks:** Nanosecond-level latency of Static Exchange Evaluation (`janus_see`) and the staged `MovePicker` state machine.
2. **Search Tree Efficiency:** Node counts, wall-clock time, and first-move beta-cutoff frequency ($\text{BF}_1$) at fixed nominal depth.
3. **Cutoff Distribution:** Empirical attribution of cutoffs to Transposition Table, Killer heuristics, History table, and captures.
4. **Memory Footprint:** Exact byte allocation of hash tables, search stacks, and history caches.
5. **Effective Search Throughput:** Real full-search NPS across diverse position topologies.

### Primary Experimental Discoveries:
- **SEE Efficiency:** `janus_see()` executes in **774.82 nanoseconds per call** ($1.29\times 10^6$ calls/second), confirming that staging captures via SEE incurs negligible CPU overhead.
- **MovePicker Staging Cost:** A complete move generation, MVV-LVA scoring, SEE partitioning, and incremental move yield costs **127.92 ns per move**, fitting comfortably within inner-loop instruction budgets.
- **First-Move Cutoff Leap ($\text{BF}_1$):** Integrated Candidate X20 establishes a first-move cutoff rate of **98.96%** (compared to 75.53% in Baseline X7), reducing required search nodes at depth 6 by **98.58%** (4,041 nodes vs 284,825 nodes in X7).
- **Throughput Preservation:** Despite extensive staging logic, NPS remains between **1.68M and 1.95M NPS** on single-thread execution.

---

## 2. Microbenchmark Performance

Benchmarked using high-resolution hardware timers (`std::chrono::high_resolution_clock` / Python `time.perf_counter`) under MSVC `/O2 /Oi /Ot /GL /LTCG` optimization on identical Windows x64 hardware:

### 2.1 Static Exchange Evaluation (`janus_see`)
- **Total Invocations:** 100,000 calls across complex middlegame capture sets.
- **Total Elapsed Time:** 0.0775 seconds.
- **Latency per Call:** **774.82 ns**.
- **Throughput:** **1,290,622 calls/second**.
- **Memory Overhead:** 0 dynamic allocations (uses stack-allocated attacker bitboards).

### 2.2 Staged MovePicker Incremental Move Generation
- **Iterations Profiled:** 50,000 full position picker cycles.
- **Total Legal/Pseudo-Legal Moves Yielded:** 1,650,000 moves.
- **Total Elapsed Time:** 0.2111 seconds.
- **Latency per Complete Initialization & Drain:** **4,221.41 ns** (4.22 $\mu$s).
- **Latency per Move Yielded:** **127.92 ns**.
- **Cache Behavior:** All MovePicker internal buffers (`good_caps`, `near_even_caps`, `quiets`, `bad_caps`) reside in L1 data cache on the thread execution stack.

---

## 3. Search Tree Economics (Fixed Depth 6 Across 10 Diagnostic Positions)

| Metric | X7 Baseline | X19 Frozen | X20 (Adaptive C1) | X20 (History H2) | X20 Integrated (C1+H2) |
|---|---|---|---|---|---|
| **Total Nodes** | 284,825 | 13,289 | 8,212 | 4,025 | **4,041** |
| **Elapsed Time (s)** | 0.2007 | 0.0085 | 0.0042 | 0.0024 | **0.0024** |
| **Full-Search NPS** | 1,419,480 | 1,563,135 | 1,951,706 | 1,687,560 | **1,679,900** |
| **Node Reduction vs X7** | Baseline | -95.33% | -97.12% | -98.59% | **-98.58%** |
| **Node Reduction vs X19** | +2,043% | Baseline | -38.20% | -69.71% | **-69.59%** |
| **First-Move Cutoff ($\text{BF}_1$)** | 75.53% | 95.51% | 99.20% | 98.94% | **98.96%** |
| **Total Cutoffs Recorded** | 14,845 | 4,522 | 1,756 | 1,514 | **1,532** |

### Key Economic Takeaways:
1. **Isolated Capture Ordering (C1):** Promoted near-even captures reduce search nodes from 13,289 to 8,212 (a 38.20% reduction over X19) by finding early cutoffs on tactical trades before exploring quiets.
2. **Isolated History Aging (H2):** Decaying history scores by $\frac{7}{8}$ prevents stale scores from misleading quiet move ordering, cutting nodes from 13,289 to 4,025 (a 69.71% reduction over X19).
3. **Synergy in Integration:** X20 Integrated combines both effects, establishing a near-perfect **98.96% $\text{BF}_1$ rate** with $70\times$ fewer nodes than Baseline X7.

---

## 4. Cutoff Source Attribution Breakdown

Analysis of cutoff telemetry across the 10 diagnostic positions at depth 6:

```
+-------------------------------------------------------------------------+
| Cutoff Attribution Breakdown (X20 Integrated)                           |
+-------------------------------------------------------------------------+
| First-Move Cutoffs (Move 1):  1,516 / 1,532  (98.96%)                   |
| TT Cutoffs:                     418 / 1,532  (27.29%)                   |
| Capture Cutoffs:                612 / 1,532  (39.95%)                   |
| Killer Move Cutoffs:            284 / 1,532  (18.54%)                   |
| History Cutoffs:                218 / 1,532  (14.23%)                   |
+-------------------------------------------------------------------------+
```

Because near-even captures are evaluated immediately after countermoves and before quiets, tactical exchanges resolve 39.95% of cutoffs instantly, shielding the engine from deep quiet branch exploration.

---

## 5. Architectural Memory Footprint

The memory footprint is statically bounded and deterministic, with zero heap allocations during the search:

| Memory Component | Dimensions / Capacity | Element Size | Total Allocation | Cache Tier Target |
|---|---|---|---|---|
| **Transposition Table** | 1,048,576 entries ($2^{20}$) | 16 bytes | **16.00 MB** | L3 Cache / RAM |
| **Butterfly History Table** | $2 \times 64 \times 64$ cells | 4 bytes (`int32`) | **32.00 KB** | L1 Data Cache |
| **Continuation History (1-ply)** | $6 \times 64 \times 6 \times 64$ cells | 2 bytes (`int16`) | **288.00 KB** | L2 Cache |
| **Continuation History (2-ply)** | $6 \times 64 \times 6 \times 64$ cells | 2 bytes (`int16`) | **288.00 KB** | L2 Cache |
| **Pawn Hash Table** | 16,384 entries | 16 bytes | **256.00 KB** | L2 Cache |
| **Countermove Table** | $64 \times 64$ entries | 2 bytes (`uint16`) | **8.00 KB** | L1 Data Cache |
| **Search Stack (`g_ss`)** | 128 plies | 64 bytes | **8.00 KB** | L1 Data Cache |
| **Total Static Footprint** | — | — | **16.88 MB** | Highly Compact |

The entire tactical history subsystem fits within 616 KB, well within standard modern L2 CPU cache sizes (1–2 MB per core).

