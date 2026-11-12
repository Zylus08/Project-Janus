# Phase 5: Architectural Intervention Implementation Report

**Milestone:** Phase 1, Milestone P1.11  
**Charter:** Classical Search Architecture Decision, Counterfactual Pruning Verification & Competitive Strength Recovery  
**Architect:** Principal Computer Chess Engineer & C++17 Performance Architect  
**Candidate Engine:** Janus Classical X16 (`janus_classical_x16.exe`)  
**SHA-256 Checksum:** `97e69fa99c708400c33e95b2bb32e3db79d8467970e1a895927a459f34061ab9`  
**Binary Size:** 1,598,464 bytes  
**Source File:** [`engine/classical_x/janus_classical_x.cpp`](file:///E:/ChessXML/project-janus-phase1/engine/classical_x/janus_classical_x.cpp)  

---

## 1. Executive Implementation Summary

Following the empirical discoveries of Phase 2 (33.3% LMR over-pruning of quiet defensive and king-safety moves) and Phase 3 (score scale volatility under E10/E11 evaluation terms), **Direction A (Evaluation-Aware Pruning Safety & History-Dampened LMR)** was implemented cleanly in the core search loop of `janus_classical_x.cpp`.

The implementation satisfies all non-negotiable architectural mandates:
1. **Strictly Non-ML:** Zero neural parameters, zero learned policies, zero automated parameter fitting.
2. **Zero Memory Allocation:** Stores static evaluations within the existing thread-local search stack `g_ss[ply].static_eval` with zero heap allocation.
3. **Independently Switchable:** Governed by `option name UCI_PruningSafety type check default true`. When toggled to `false`, the engine reproduces Candidate X15 bit-for-bit.
4. **Deterministic at 1 Thread:** Pure bitboard state transitions with zero non-deterministic constructs.

---

## 2. Granular Code Changes & Mechanical Specifications

### 2.1 Search Stack Augmentation
In `janus_classical_x.cpp`, `SearchStackEntry` was extended to track static evaluations across the tree:
```cpp
struct SearchStackEntry {
    uint16_t current_move;
    int piece;
    int static_eval;
};
thread_local SearchStackEntry g_ss[MAX_SEARCH_PLY];
```
Before root search iteration, all stack entries are initialized to `-INF`:
```cpp
for (int i = 0; i < MAX_SEARCH_PLY; i++) g_ss[i].static_eval = -INF;
```

### 2.2 The "Improving" Search Flag
At the beginning of each `negamax` node, the static evaluation is evaluated and recorded:
```cpp
bool in_check = (native_is_check(b) != 0);

int static_eval = native_evaluate(b);
g_ss[ply].static_eval = static_eval;
bool improving = false;
if (ply >= 2 && !in_check && g_ss[ply - 2].static_eval != -INF) {
    improving = (static_eval > g_ss[ply - 2].static_eval);
}
```

### 2.3 Evaluation-Aware Reverse Futility Pruning (RFP)
When the position is **not improving** (the side to move is under pressure), the RFP fail-high threshold is expanded by $+40 \times d$:
```cpp
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
```
*Effect:* Prevents premature fail-high cutoffs when static evaluations are temporarily inflated.

### 2.4 History-Dampened Late Move Reductions (LMR)
Quiet move reductions are dynamically dampened whenever the position is defensive or the quiet move possesses positive continuation history:
```cpp
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
*Effect:* Protects critical quiet defensive refutations (like `e1g1`, `h2h3`, and `d4d5`) from being buried by aggressive LMR reductions.

---

## 3. Configuration Ablation Matrix

| Configuration ID | Architecture Description | Pruning Safety Active | Dynamic LMR Policy | RFP Base Margin | Thread Execution Profile |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **C0** | Frozen X15 Baseline Control | `false` | Baseline L3 | $120 \times d$ (1T) / $90 \times d$ (4T) | Candidate S (1T) / Candidate P (4T) |
| **C1** | Improving-Flag Safety Only | `true` (improving only) | Improving-dampened | $+40 \times d$ non-improving | Candidate S (1T) / Candidate P (4T) |
| **C2** | Full Direction A (Candidate X16) | `true` (full) | Improving + Conthist | $+40 \times d$ non-improving | Candidate S (1T) / Candidate P (4T) |
| **C3** | Aggressive LMR Dampening | `true` (aggressive) | Max $\pm 2$ ply shift | $+60 \times d$ non-improving | Candidate S (1T) / Candidate P (4T) |

---

## 4. Verification & Build Integrity

- **Compilation Command:**
  `cl /O2 /Ot /Oi /std:c++17 /EHsc /Fe:janus_classical_x.exe janus_classical_x.cpp`
- **Compiler Version:** MSVC 19.43.34809 for x64 (Visual Studio 2022 v17.13.5).
- **Control Binary Location:** [`analysis/phase1/p1.11/control/janus_classical_x16.exe`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/control/janus_classical_x16.exe).
- **Executable Size:** 1,598,464 bytes.
- **SHA-256 Checksum:** `97e69fa99c708400c33e95b2bb32e3db79d8467970e1a895927a459f34061ab9`.

