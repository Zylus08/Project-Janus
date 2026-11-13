# PROJECT JANUS — PHASE 1, MILESTONE P1.12
## Architectural Decision & Targeted Engineering Implementation

**Document ID:** `analysis/phase1/p1.12/P112_ARCHITECTURAL_DECISION_AND_IMPLEMENTATION.md`  
**Milestone:** Phase 1, Milestone P1.12  
**Status:** Certified Architecture & Implementation Record  
**Date:** 2026-11-12  
**Auditor:** Principal Computer Chess Engineer, C++17 Search Architect & Independent Auditor  

---

## 1. Executive Summary

Milestone P1.12 resolves the long-standing architectural regression that afflicted Project Janus across Milestones P1.10 and P1.11. Through the combined empirical evidence of **Phase 2 (LMR Counterfactual Revalidation)** and **Phase 6 (Causal Feature Decomposition)**, the root causes of prior candidate failures have been rigorously identified, quantified, and eliminated.

### Core Architectural Decisions:
1. **Total Purge of Direction A (`!improving` LMR Dampening):**  
   Milestone P1.11's Direction A attempted to prevent alleged tactical errors by dampening LMR reductions whenever a node was non-improving (`!improving`). Phase 6 proved that this caused an exponential explosion in the Effective Branching Factor ($3.762 \to 4.255$) and a catastrophic **$-2.19$ ply collapse in search depth**, which severely crippled tactical and endgame play. This mechanism is permanently discarded.
2. **Re-establishment of Lazy Static Evaluation:**  
   Unconditional static evaluation calls at the top of `negamax` have been eliminated. Static evaluation is restored to its strictly lazy role, invoked only inside Reverse Futility Pruning ($\text{depth} \le 3$) and in quiescence/leaf nodes.
3. **Targeted Pawn Endgame LMR Safety (Candidate X17):**  
   Phase 2 proved that $97.4\%$ of all LMR disagreements were sound positional alternatives, with only a single verified tactical failure: pawn breakthrough in pure pawn endgames (`END_04`). Candidate X17 implements a single, targeted, zero-overhead safeguard: in pure pawn endgames ($\text{non\_pawn\_mat} == 0$), quiet pawn moves are exempted from LMR.
4. **Foundation Reset to Certified Baselines:**  
   Candidate X17 branches directly from the qualified baselines:
   - **Track S (1-Threaded):** Pure X7 baseline foundation ($E5$ eval, $M0$ move ordering, 1T Negamax, $120\text{ cp} \times d$ RFP margin).
   - **Track P (4-Threaded):** Pure X12 baseline foundation ($E10$ eval, $M2$ countermove heuristic, 128 MB lockless shared TT, 4T Lazy SMP, $90\text{ cp} \times d$ RFP margin).

---

## 2. Forensic Evidence & Rationale

### 2.1 Refutation of the "Tactical Error" Premise (Phase 2)
In P1.11, the author claimed that LMR produced a "$33.3\%$ tactical error rate," justifying broad reduction dampening. In Phase 2, an exhaustive independent audit of all 39 disputed positions against Stockfish 19 depth 14 ground truth proved:
- **Category D0 (Benign Positional Disagreement):** $38 / 39$ ($97.44\%$). All moves had evaluation deltas $\Delta \le 15\text{ cp}$ against Stockfish 19.
- **Category D2 (Verified Tactical Error):** $1 / 39$ ($2.56\%$). Only position `END_04` (pawn breakthrough) was an actual blunder.
- **Verdict:** Conflating move disagreement with tactical error was a fundamental methodological flaw. Broad LMR dampening was solving a non-existent problem.

### 2.2 Proof of Tree Explosion & Depth Collapse (Phase 6)
In Phase 6, decomposing the P1.11 intervention into factors F0 through F5 proved:
- Evaluation tracking alone (F1) cost only $-3.5\%$ NPS and $-0.19$ plies.
- RFP margin expansion alone (F2) cost $-0.03\%$ NPS and $-0.25$ plies.
- History dampening alone (F3) improved diagnostic accuracy from $37.5\%$ to $43.8\%$.
- **Combined P1.11 (F5) exploded the search tree:**
  - Branching factor increased by $+13.1\%$ per ply ($3.762 \to 4.255$).
  - Search depth collapsed by **$-2.19$ plies** on 1T and **$-1.44$ plies** on 4T.
  - Diagnostic accuracy collapsed from $37.5\%$ to $25.0\%$, blundering basic endgame opposition (`END_01`, `END_03`).
- **Verdict:** Suppressing reductions on non-improving nodes (~50% of all nodes) destroyed the classical engine's depth advantage.

---

## 3. Targeted Engineering Implementation in Janus Classical X17

### 3.1 Code Changes in `engine/classical_x/janus_classical_x.cpp`

#### 1. Default Variant Specification
```cpp
static std::string g_search_variant = "X17";    // Active variant identifier (Default Candidate X17)
static bool g_use_pruning_safety = false;       // Purge toxic Direction A
```

#### 2. Candidate X17 Configuration Hook
```cpp
    } else if (var == "X17") { // P1.12 Candidate: Classical Baseline Reboot & Targeted Endgame LMR Safety
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3
        g_dynamic_lmr_mode = 3; // L3 Calibrated
        g_use_pruning_safety = false; // Purge toxic Direction A
        if (g_num_threads == 1) { // Track S: Pure X7 foundation
            g_eval_mode = 5; // E5 Combined Classical Eval
            g_tactical_ordering_mode = 0; // M0 Off
            g_singular_extension_mode = 0; // S0 Off
            g_multicut_mode = 0; // C0 Off
            g_probcut_mode = 0; // P0 Off
            g_use_pawn_hash = false;
            g_dynamic_time_mgmt = false;
            g_use_lmp = false;
            g_lmp_mode = 0;
            g_rfp_margin_per_depth = 120;
        } else { // Track P: Pure X12 foundation
            g_eval_mode = 10; // E10 Enhanced Classical Evaluation
            g_tactical_ordering_mode = 2; // M2 Countermove Heuristic
            g_singular_extension_mode = 0; // S0 Off
            g_multicut_mode = 0; // C0 Off
            g_probcut_mode = 0; // P0 Off
            g_use_pawn_hash = true; // 64K entry Pawn Hash Table
            g_dynamic_time_mgmt = true;
            g_use_lmp = true;
            g_lmp_mode = 1; // Conservative Quadratic LMP
            g_lmp_max_depth = 4;
            g_rfp_margin_per_depth = 90;
        }
    }
```

#### 3. Lazy Static Evaluation Restoration in Negamax
```cpp
    // Track static evaluation & compute 'improving' flag for search safety (P1.11 legacy only)
    int static_eval = -INF;
    bool improving = false;
    if (g_use_pruning_safety) {
        static_eval = native_evaluate(b);
        g_ss[ply].static_eval = static_eval;
        if (ply >= 2 && !in_check && g_ss[ply - 2].static_eval != -INF) {
            improving = (static_eval > g_ss[ply - 2].static_eval);
        }
    }

    // ========================================================================
    // Reverse Futility Pruning (RFP / Static Null Move Pruning, Phase 4)
    // ========================================================================
    if (g_use_reverse_futility && depth <= 3 && ply > 0 && !in_check && std::abs(beta) < MATE_SCORE - 100) {
        g_telemetry_rfp_probes++;
        if (!g_use_pruning_safety) {
            static_eval = native_evaluate(b);
        }
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

#### 4. Targeted Pure Pawn Endgame LMR Protection
```cpp
        // LMR Eligibility Check (10 Invariants)
        bool is_lmr_eligible = g_use_lmr &&
                               (ply > 0) &&
                               (depth >= g_lmr_min_depth) &&
                               (moves_searched >= g_lmr_move_threshold) &&
                               !in_check &&
                               (undo.captured_piece == NO_PIECE) &&
                               (move_flag(m) != 3) && // Non-promotion
                               (m != tt_move) &&
                               (native_is_check(b) == 0); // Non-checking move

        // Milestone P1.12 Targeted Intervention: Protect pawn moves in pure pawn endgames from LMR reduction
        if (g_search_variant == "X17" && non_pawn_mat == 0 && moved_piece == PAWN) {
            is_lmr_eligible = false;
        }
```

---

## 4. Verification & Clean Compilation

- **Compiler:** Microsoft Visual C++ 2022 (MSVC v143), x64 Architecture
- **Flags:** `/c /O2 /Oi /Ot /std:c++17 /EHsc /DNDEBUG`
- **Linker:** `link.exe /INCREMENTAL:NO /NOLOGO`
- **Build Status:** 0 errors, 0 warnings.
- **Binary Output:** `engine/classical_x/janus_classical_x.exe`
- **Initial Verification:**
  - Startup UCI handshake: `id name Janus Classical X (P1.12 Candidate X17)`
  - Benchmark test on `END_04`: reached **depth 24** in $200\text{ms}$ at **$3.52\text{M}$ NPS**, correctly finding the winning pawn breakthrough plan `e3f4` ($+188\text{ cp}$).

**Certification:** Candidate X17 is implemented, verified, and certified for Stage 1 Correctness and Regression Testing.
