# PROJECT JANUS v0.54 — MOVE ORDERING RECONNAISSANCE

**Phase:** Phase 0 — Baseline Reconnaissance  
**Date:** 2026-11-05  
**Topic:** Investigation of Killer and History Heuristics across Milestone History  

---

## 1. Executive Reconnaissance Question

Did killer-move and history-heuristic move ordering already exist in the compiled native C++17 engine (`janus_native.cpp`), or did earlier references refer strictly to Python-level prototypes?

---

## 2. Milestone-by-Milestone Evolutionary Audit

### 2.1 Python Milestones (v0.46 – v0.49)
- **v0.46 – v0.48:** Python-level experiments implemented prototype killer moves (`self.killers[ply][0..1]`) and an eager Python dictionary-based history heuristic.
- **v0.48 – v0.49 Findings:** Profiling demonstrated that eager Python dictionary lookups and move sorting consumed up to 20–30% of total search time in CPython. Python-level incremental move pickers (L2) proved slower than CPython's native `list.sort()`, leading to the conclusion that performance-critical move scoring must be executed natively.

### 2.2 Native Transition (v0.50 – v0.53)
- **v0.50 (Native N2 Prototype):** Search orchestration was completely rewritten in C++17. To establish clean differential parity with Python K0, the move ordering function `score_move_for_ordering` was implemented with a simplified K0 baseline policy:
  - Hash Move (TT): `10,000,000`
  - Queen Promotion: `900,000`
  - Underpromotions: `800,000`
  - Captures (MVV-LVA): `100,000 + (victim * 10) - attacker`
  - Quiet Moves: **`0`**
- **v0.51 (Native Engine Qualification):** Preserved the v0.50 move ordering policy unchanged.
- **v0.52 (Native LMR):** Introduced Late Move Reductions. Reductions were applied to late quiet moves based on move search count ($moves\_searched \ge 4$), but quiet moves were still sorted arbitrarily in move-generation order (all having score 0).
- **v0.53 (Native PVS):** Introduced Principal Variation Search. PVS probed late moves with null windows, relying heavily on TT move cutoffs, but quiet moves still lacked any dynamic prioritization.

### 2.3 Clarification on `native_reset_history()` in Native Code
In `janus_native.cpp`, several functions named `native_push_history`, `native_pop_history`, `native_reset_history`, and `g_game_history` exist.
**Audit Finding:** These structures store 64-bit Zobrist position keys in a 1,024-entry stack exclusively for **FIDE threefold repetition detection**, both in the game root and in-tree search paths. They do **not** implement move-ordering history heuristic.

---

## 3. Current Native Search Reality

In the production C++17 baseline (`janus_native.cpp` lines 1198–1237):
```cpp
static int score_move_for_ordering(const NativeBoard* b, uint16_t m, uint16_t tt_move) {
    if (m == tt_move) return 10000000;

    int flag = move_flag(m);
    if (flag == 3) { // Promotion
        int promo = move_promo(m);
        return (promo == 3) ? 900000 : 800000;
    }

    // Capture scoring via MVV-LVA...
    if (victim != NO_PIECE) {
        ...
        return 100000 + (victim * 10) - attacker;
    }

    return 0; // Quiet moves: NO PRIORITIZATION
}
```

When a quiet move causes a beta cutoff:
```cpp
        if (alpha >= beta) {
            if (is_lmr_eligible) {
                g_lmr_cutoffs++;
            }
            if (g_use_pvs) {
                g_pvs_cutoffs++;
            }
            break; // Beta cutoff: NO KILLER OR HISTORY UPDATES PERFORMED
        }
```

---

## 4. Architectural Opportunity for v0.54

Because quiet moves have zero differentiation in the baseline N3 engine, their search order is determined solely by the legal move generator. Consequently:
1. Moves that frequently cause beta cutoffs at similar depths or plies are not prioritized.
2. In LMR searches, effective quiet moves may be pushed past move index 4, causing them to be unnecessarily reduced and forcing expensive full-depth re-searches.
3. Introducing **native C++ killer moves** and a **native C++ history heuristic** directly targets this structural weakness without incurring any Python interpreter boundary overhead.

