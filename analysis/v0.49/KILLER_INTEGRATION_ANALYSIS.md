# Project Janus v0.49 — Killer Move Integration Analysis

**Milestone:** Project Janus v0.49  
**Parent Baseline Commit:** `6b46eb4` (v0.48 Final)  
**Evaluated Architecture:** Candidate K1 (Multi-Stage Lazy Picker with Killer Priority)  
**Test Corpus:** 37-position diagnostic corpus at Depth 4  
**Raw Telemetry:** `analysis/v0.49/raw/killer_analysis_raw.json`

---

## 1. Executive Summary

Phase G investigated whether prioritizing 2-slot killer moves inside the lazy move selection framework reduces search work or improves move ordering efficiency.

### Primary Empirical Findings:
1. **Search Tree Equivalence:** Candidate K1 produced **407,705 nodes**, exactly identical to Candidate L1 (407,705 nodes, $+0.62\%$ relative to K0).
2. **Move Agreement:** 36 / 37 positions (**97.3%**) produced the exact same best move as Baseline K0, with zero tactical misses and zero blunders.
3. **Killer Volume:** Across the 37 positions at Depth 4, **37,985 killer move opportunities** were identified and prioritized before quiet moves.
4. **Interpreter Partitioning Overhead:** Despite prioritizing killer moves ahead of quiets, Candidate K1 required **37.64 seconds** vs 36.14 seconds for L1 ($+4.31\%$ runtime overhead). Partitioning Python move lists into `caps`, `killers`, and `quiets` within `rest_provider()` incurs generator/list allocation costs that exceed the sorting savings.

---

## 2. Comparative Matrix (Depth 4)

| Configuration | Total Search Nodes | Node Delta vs K0 | Wall-Clock Time | Time Delta vs K0 | Move Agreement with K0 | Killer Opportunities |
|---|---:|---:|---:|---:|---:|---:|
| **Baseline K0** | **405,197** | Baseline | 36.08 s | Baseline | 37 / 37 (100.0%) | N/A (Eager Sort) |
| **Candidate L1** | 407,705 | +0.62% | **36.14 s** | **+0.16%** | 36 / 37 (97.3%) | Embedded in sort |
| **Candidate K1** | 407,705 | +0.62% | 37.64 s | +4.31% (Slower) | 36 / 37 (97.3%) | **37,985** |

---

## 3. Detailed Architectural Takeaway

In Janus's existing search architecture, killer moves are already assigned fixed high priority scores in `_move_order_score`:
- Killer Slot 0: `700,000`
- Killer Slot 1: `600,000`
- Winning captures: `100,000` to `200,000` + MVV-LVA
- History quiets: `0` to `10,000`

Because CPython's built-in `list.sort()` is implemented in native C Timsort, sorting a 30-element list of pre-scored moves in C is actually **faster** than running Python `for` loops to filter moves into multiple stage buckets (`caps`, `killers`, `quiets`).

Therefore, multi-stage move picking only becomes faster if implemented entirely in native C/Cython where move generation yields unboxed integer moves directly into fixed buffers without Python object overhead. In pure Python, Candidate L1's lightweight two-phase approach (TT immediate yield $\to$ fallback sort) remains the optimal design.

