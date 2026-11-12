# Janus Classical X16: Candidate Selection and Binary Freeze

## 1. Candidate Designation & Architectural Identity

In Milestone P1.11, following the counterfactual pruning verification audit (Phase 2), evaluation-pruning compatibility study (Phase 3), and architecture decision record (Phase 4), the new candidate engine **Janus Classical X16** is formally selected and frozen.

Janus Classical X16 adopts **Direction A: Evaluation-Aware Pruning Safety & History-Dampened LMR**, directly addressing the primary defect discovered in Janus's search pipeline: the indiscriminate over-pruning of quiet defensive moves by Late Move Reductions (LMR) which produced a 33.3% move disagreement rate in tactical defense.

Like X15, X16 maintains an adaptive split between single-threaded and multithreaded topologies:
- **Janus Classical X16-S (1 Thread):** Zero synchronization overhead, 128MB shared TT, thread-local search stack, evaluation-aware pruning safety, RFP margin $120\times d$ ($+40\times d$ when not improving), history-dampened LMR.
- **Janus Classical X16-P (4 Threads):** 4 Lazy SMP worker threads, shared lockless 128MB TT with atomic 128-bit entries, 16K thread-local pawn hash table, dynamic time management, quadratic Late Move Pruning ($N \le 3 + 2\times d^2$), RFP margin $90\times d$ ($+40\times d$ when not improving), history-dampened LMR.

---

## 2. Integrated Architectural Interventions

The specific C++17 algorithmic changes integrated into `engine/classical_x/janus_classical_x.cpp` are:

```cpp
// 1. Search stack static evaluation tracking
struct SearchStackEntry {
    uint16_t current_move;
    int piece;
    int static_eval;
};
thread_local SearchStackEntry g_ss[MAX_SEARCH_PLY];

// 2. Evaluation-aware static evaluation & improving flag computation
int static_eval = native_evaluate(b);
g_ss[ply].static_eval = static_eval;
bool improving = false;
if (ply >= 2 && !in_check && g_ss[ply - 2].static_eval != -INF) {
    improving = (static_eval > g_ss[ply - 2].static_eval);
}

// 3. Evaluation-aware Reverse Futility Pruning (RFP) margin expansion
if (g_use_reverse_futility && depth <= 3 && ply > 0 && !in_check && std::abs(beta) < MATE_SCORE - 100) {
    g_telemetry_rfp_probes++;
    int rfp_margin = g_rfp_margin_per_depth * depth;
    if (g_use_pruning_safety && !improving) {
        rfp_margin += 40 * depth;
    }
    if (static_eval - rfp_margin >= beta) {
        g_telemetry_rfp_cutoffs++;
        return static_eval;
    }
}

// 4. History-dampened Late Move Reductions (LMR)
if (g_use_pruning_safety) {
    if (!improving) {
        dynamic_reduction = std::max(1, dynamic_reduction - 1);
    }
    if (tot_h > 2000) {
        dynamic_reduction = std::max(1, dynamic_reduction - 1);
    } else if (tot_h < -2000) {
        dynamic_reduction += 1;
    }
}
```

---

## 3. Binary Freeze & Cryptographic Manifest

Candidate X16 has been compiled from source and frozen alongside all baseline controls:

| Engine | Role | Source Path / Origin | Binary Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Janus Classical X16** | Proposed Candidate | `engine/classical_x/janus_classical_x.cpp` | `analysis/phase1/p1.11/control/janus_classical_x16.exe` | 1,598,464 | `97e69fa99c708400c33e95b2bb32e3db79d8467970e1a895927a459f34061ab9` |
| **Janus Classical X7** | Qualified 1T Baseline | Commit `b34e342` | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | 370,176 | `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b` |
| **Janus Classical X12** | Qualified 4T Baseline | Commit `78ca3d5` | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | 2,874,368 | `00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059` |
| **Janus Classical X15** | Frozen platform ref | Commit `24c663c` | `analysis/phase1/p1.10/control/janus_classical_x15.exe` | 1,596,416 | `5b3cfcfe85b81ca03acd85f65196fb6599d29a100f272d2c1fbd66af26374e28` |
| **Stockfish 19** | External Benchmark | Commit `edb0d9d` | `tools/stockfish/stockfish.exe` | 42,959,960 | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` |

---

## 4. Compiler Environment and Invariants

- **Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.44.35222 for x64
- **Flags:** `/O2 /Ot /Oi /std:c++17 /EHsc`
- **Machine Architecture:** AMD64 / Windows 11 Pro
- **Governing Restrictions:** Strictly non-ML. No neural networks, no NNUE, no SPSA, no Texel tuning or offline-fitted parameters.
- **Verification Status:** 100% pass rate across Gate 1 (Symmetry), Gate 2 (Mate Precision), Gate 3 (Low-Clock Stability), and Gate 4 (X15 Reproducibility).

