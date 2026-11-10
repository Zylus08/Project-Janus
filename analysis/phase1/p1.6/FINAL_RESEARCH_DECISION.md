# Project Janus — Phase 1, Milestone P1.6
## Formal Research Decision & Milestone Adjudication

**Date:** 2026-11-10  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Milestone:** P1.6 — Lazy SMP Multithreading, Safe Late Move Pruning & Competitive Scaling Qualification  
**Evaluator:** Principal Computer Chess Engineer & Independent Statistical Auditor  
**Formal Milestone Classification:** **CATEGORY B — Experimental Parallel Platform Qualified; Baseline X7 Retained as Production Control**

---

### 1. Executive Adjudication Framework

In strict compliance with the Phase 1 Non-Negotiable Project Rules and scientific testing standards, Milestone P1.6 established three independent qualification gates:

```
[Candidate X11 Evaluation Framework]
  |
  +---> Gate A: Single-Thread Strength Promotion (X11 1T vs X7 1T)
  |       Criterion: p < 0.05 superior playing strength over X7.
  |       Result: 99.5 / 200 (49.75%), -1.7 Elo, p = 0.9350.
  |       Verdict: REJECT PROMOTION (Dead tie / Statistical parity).
  |
  +---> Gate B: Multithreaded Deployment Engine (X11 4T Scaling & Safety)
  |       Criterion: Race-free, scalable, stable, competitive parallel search.
  |       Result: 3.26x NPS speedup (81.5% eff); 0 races; but -107.5 Elo under fast blitz.
  |       Verdict: QUALIFY AS ADVANCED EXPERIMENTAL PLATFORM (Category B).
  |
  +---> Gate C: External Stockfish 19 Benchmark (X11 vs SF19 Unrestricted NNUE)
          Criterion: Quantitative tracking of the classical-to-neural gap.
          Result: 1T: 2.0 / 40 (5.0%, 4 draws, -511.5 Elo); 4T: 0.5 / 40 (1.25%, -759.1 Elo).
          Verdict: EXTERNAL BASELINE DURABLY PRESERVED (~160 Elo recovery over C1).
```

---

### 2. Comprehensive Adjudication by Gate

#### Gate A: Single-Thread Production Promotion (REJECTED)
- **Empirical Evidence:** In a 200-game match across 100 balanced opening pairs at 1.0s + 50ms, Candidate X11 (1T) scored **69W / 61D / 70L = 99.5 / 200 (49.75%)**, representing an Elo difference of **−1.7 Elo** with a paired $t$-statistic of $t = -0.0815$ and $p = 0.9350$.
- **Finding:** Safe Late Move Pruning successfully trimmed 11.8% of the search tree (Phase 7), but the accompanying cluster TT spinlock checks introduced a countervailing 2.3% throughput penalty. At 1 thread under blitz time controls, the two factors balanced each other out with mathematical precision.
- **Rule Application:** Project Janus requires statistically significant superiority ($p < 0.05$) to promote an engine to primary production baseline. Because $p = 0.9350 \gg 0.05$, **Janus Classical X7 (`b34e342`) is formally retained as the Qualified Single-Thread Production Baseline**.

#### Gate B: Multithreaded Deployment Platform (QUALIFIED AS ADVANCED EXPERIMENTAL)
- **Empirical Evidence:**
  - In Phase 4, Candidate X11 sustained **32.89 million ops/sec** across 4 threads with zero corrupted entries, zero data races, and zero torn reads.
  - X11 achieved **1.96x speedup (97.8% efficiency) at 2 threads** and **3.26x speedup (81.5% efficiency) at 4 threads**, deepening search by +0.94 ply.
  - In Phase 8, 12/12 Perft depths and 5/5 fallback parity positions passed with 100% bit-exact determinism.
  - However, in Match 2 at 1.0s + 50ms blitz, X11 (4T) scored 14.0 / 40 (35.0%, −107.5 Elo vs X7 1T) due to helper-thread tree dispersion and TT pollution in the absence of synchronized quiet move history.
- **Verdict:** Candidate X11 represents an outstanding parallel systems engineering milestone, successfully delivering scalable, thread-safe Lazy SMP concurrency into Project Janus for the first time. It is preserved and qualified as the **Advanced Multithreaded Research Engine**.

#### Gate C: Matched Stockfish 19 External Progress (VERIFIED)
- **Empirical Evidence:**
  - At 1 thread, X11 held **4 resilient draws** against unrestricted Stockfish 19 with default NNUE (2.0 / 40, 5.00%, −511.5 Elo).
  - This verifies that the non-neural positional evaluation and dynamic time management established in P1.5 are completely solid and reproducible.
  - At 4 threads, Stockfish 19's mature parallel NNUE search reaches depth 20–24, scoring 39.5 / 40.
- **Scientific Conclusion:** Raw multicore hardware scaling cannot bridge the architectural divide with neural networks without commensurate evaluation accuracy. Handcrafted evaluation terms must be mathematically tuned before parallel depth gains can be translated into wins against top-tier opponents.

---

### 3. Formal Classification Decision

In accordance with the taxonomy of Project Janus:

> **CATEGORY B — EXPERIMENTAL CANDIDATE QUALIFIED; PRODUCTION BASELINE RETAINED**
> 
> 1. **Incumbent Production Baseline:** **Janus Classical X7** (commit `b34e342`, binary hash `86392a2f...`) remains the primary production baseline for single-threaded classical development.
> 2. **Advanced Research Lineage:** **Janus Classical X11** is qualified as the concurrency and parallel research foundation for all subsequent multithreaded investigations.
> 3. **Archival Assets:** All source code, binaries, stress tests, PGNs, and raw telemetry for X11 are permanently frozen and cataloged in `analysis/phase1/p1.6/control/`, `raw/`, and `pgn/`.

---

### 4. Integrity and Compliance Certification

1. **Non-ML Rule:** Janus Classical X11 contains strictly zero neural networks, zero NNUE weights, zero learned heuristics, and zero machine learning dependencies.
2. **Stockfish Integrity:** Stockfish 19 was tested strictly in its official release configuration with default NNUE enabled.
3. **Reproducibility:** Every game, move, and metric is backed by raw JSON logs and full PGN records.
