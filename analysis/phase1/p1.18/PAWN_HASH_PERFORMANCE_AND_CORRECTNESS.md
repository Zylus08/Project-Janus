# Pawn-Hash Performance & Correctness Certification (Phase 9 Report)
**Project Janus — Phase 1, Milestone P1.18**
**Component:** 64K-Entry Thread-Local Pawn Hash Table (`g_pawn_table`)
**Date:** 2026-11-14 | **Raw Data:** `analysis/phase1/p1.18/raw/pawn_hash_profile_raw.json`

---

## 1. Executive Summary

Milestone P1.17 established that enabling the 64K-entry pawn hash table on single-thread configurations recovered substantial search throughput without compromising correctness. Milestone P1.18 extends this architecture by embedding **Track A Backward Pawn Detection** directly into the cached pawn structure evaluation function (`eval_pawn_structure`).

This report provides a formal performance benchmark, memory footprint audit, and collision safety certification for the active pawn hash implementation in Candidate X23.

---

## 2. Table Architecture & Cache Topology

### 2.1 Table Specifications
- **Table Size:** $2^{16} = 65,536$ entries (`PAWN_HASH_SIZE`).
- **Entry Structure (`PawnEntry`):**
  ```cpp
  struct PawnEntry {
      uint64_t key;              // 8 bytes: Full 64-bit Zobrist pawn key
      int16_t mg[2];             // 4 bytes: Midgame pawn score (White, Black)
      int16_t eg[2];             // 4 bytes: Endgame pawn score (White, Black)
      uint64_t passed_pawns[2];  // 16 bytes: Passed pawn bitboards
  };
  ```
- **Entry Size:** Exactly 32 bytes (power-of-two, perfectly cache-line aligned: 2 entries per 64-byte L1 CPU cache line).
- **Total Memory Footprint:** $65,536 \times 32\text{ bytes} = 2,097,152\text{ bytes} = 2.0\text{ MB}$.
- **Thread Safety:** `thread_local PawnEntry g_pawn_table[PAWN_HASH_SIZE]` guarantees complete thread isolation with zero lock contention, zero false sharing, and zero synchronization overhead across SMP search threads.

### 2.2 Zobrist Hash Key Formulation
Pawn hashing computes an independent 64-bit Zobrist key based exclusively on pawn locations:
$$K_{\text{pawn}} = \bigoplus_{s \in P_{\text{WHITE}}} Z[0][\text{PAWN}][s] \;\oplus\; \bigoplus_{s \in P_{\text{BLACK}}} Z[1][\text{PAWN}][s]$$
Because pawn moves occur in only $\approx 10\text{--}15\%$ of search plies, the pawn structure remains unchanged across the vast majority of non-pawn piece moves.

---

## 3. Empirical Performance Benchmarks

### 3.1 Microbenchmark Probe & Evaluation Latency
Under controlled microbenchmarking across 200,000 evaluations of a complex Sicilian position:

| Evaluation Mode | Latency per Evaluation | Speedup Factor |
| :--- | :---: | :---: |
| **Pawn Hash Enabled (Warm Cache)** | **2,139.4 ns** | **$1.13\times$ ($+13.5\%$)** |
| **Pawn Hash Disabled (Recalculate Every Node)** | **2,427.6 ns** | $1.00\times$ (Baseline) |

- **Net Time Saved per Eval Call:** $288.2\text{ ns}$.
- **Raw Pawn Hash Probe Latency:** $\approx 12.4\text{ ns}$ (direct L1/L2 cache hit).
- **Recalculation Avoided:** Passing over 8 files, scanning friendly/enemy bitboards, checking isolated/doubled/backward pawns, and determining candidate passers.

### 3.2 Search Tree Hit Rate
Across five diverse benchmark searches up to depth 12:
- Average Pawn Hash Probes: $412,850$
- Average Pawn Hash Hits: $364,959$
- **Average Hit Rate:** **$88.4\%$** (Range: $84.2\%$ in open tactical positions to $92.8\%$ in closed pawn chain structures).

---

## 4. Correctness & Collision Certification

### 4.1 Strict 64-bit Key Verification
Every probe checks:
```cpp
if (g_pawn_table[p_idx].key == p_key) {
    // Cache Hit: read mg, eg, passed_pawns
} else {
    // Cache Miss: compute eval_pawn_structure and overwrite
}
```
With 64-bit keys and a 65,536-entry table, the collision probability per search of $10^7$ nodes is less than $10^{-5}$, and a hash collision simply leads to a transient evaluation discrepancy that is refuted by minimax search, with zero risk of illegal moves or corrupted bitboards.

### 4.2 Color Symmetry
Pawn evaluation symmetry was verified across 225 mirrored opening positions:
- White and Black evaluations with pawn hash enabled match within $0.00\text{ cp}$ bitwise equality when colors are inverted.
- Symmetry pass rate: **100.0% (225 / 225 positions)**.

---

## 5. Certification Verdict

The 64K thread-local pawn hash table is certified as **fully correct, thread-safe, and highly performant**. It allows Candidate X23 to evaluate sophisticated pawn structural terms (including Track A backward pawns) with zero search tree throughput penalty.
