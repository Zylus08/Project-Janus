# Milestone P1.21: Targeted Pruning Compatibility Intervention (Option A Implementation)

**Milestone:** Phase 1, Milestone P1.21 (Search–Evaluation Decoupling, Pruning Reliability & Classical Architecture Decision Gate)  
**Deliverable:** `analysis/phase1/p1.21/TARGETED_PRUNING_COMPATIBILITY_INTERVENTION.md`  
**Phase:** Phase 9 — Targeted Pruning Compatibility Intervention  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Implementation Target:** `engine/classical_x/janus_classical_x.cpp`  
**Intervention Identifier:** Option A — Verified Reverse Futility Pruning (RFP) Correctness Repair  
**Target Search Variant:** `X26` (`X26-S` on 1T, `X26-P` on 4T)  

---

## 1. Executive Summary & Architectural Motivation

Milestone P1.21 established that successive Janus classical research candidates (X23, X24, X25) suffered from severe search-evaluation coupling. While the underlying minimax recursion was mathematically bug-free (Phase 6), minor static evaluation adjustments caused $20\%\text{–}60\%$ search tree inflation (Phase 4, 5, 7) and delayed tactical discovery (Phase 3). 

Forensic auditing in Phase 2 uncovered four major defects in the Reverse Futility Pruning (RFP) contract:
1. Pruning triggered at PV nodes (`beta - alpha > 1`), truncating principal variation branches.
2. The function executed `return static_eval;` without storing a `TT_LOWER` bound in the Transposition Table, causing TT thrashing and lost cutoffs in sibling branches.
3. Pruning ignored existing TT upper bounds (`flag == TT_UPPER` and `score < beta`), overriding deep branch proofs that the position fails low.
4. Pruning operated in pure pawn endgames without checking for non-pawn material, creating critical zugzwang vulnerabilities.

Under Phase 9, we have implemented **Option A (Verified RFP Correctness Repair)** in `engine/classical_x/janus_classical_x.cpp` to resolve all four contract defects in an airtight, parameterized manner.

---

## 2. Technical Implementation Details

### 2.1 Unified TT Probing Interface in Multi-Thread and Single-Thread Modes
To enable reliable TT upper-bound conflict detection across both single-threaded (`g_tt`) and multi-threaded lockless cluster (`g_parallel_tt`) searches, `ParallelTT::probe` was extended with an optional raw entry retrieval pointer:
```cpp
bool probe(uint64_t key, int depth, int ply, int alpha, int beta, int& out_score, uint16_t& out_move, bool allow_cutoff, TTEntry* out_entry = nullptr)
```
In `negamax()`, both paths now uniformly populate `has_entry` and `entry`:
```cpp
if (!g_exact_search_mode && (g_search_variant == "X11" || ... || g_search_variant == "X26" || g_num_threads > 1)) {
    int tt_score = 0;
    bool allow_cutoff = (ply > 0 && excluded_move == 0);
    if (g_parallel_tt.probe(key, depth, ply, alpha, beta, tt_score, tt_move, allow_cutoff, &entry)) {
        g_telemetry_tt_hits++;
        return tt_score;
    }
    if (entry.key == key) {
        has_entry = true;
    }
} else {
    size_t tt_idx = key % TT_SIZE;
    entry = g_tt[tt_idx];
    if (entry.key == key) {
        has_entry = true;
        ...
    }
}
```

### 2.2 The Option A RFP Decision Engine
The RFP decision block in `negamax()` was completely reconstructed to incorporate the four contract repairs under the control of `g_rfp_repair_mode`:

```cpp
// ========================================================================
// Reverse Futility Pruning (RFP / Static Null Move Pruning, Phase 4 & P1.21 Option A)
// ========================================================================
bool is_pv_node = (beta - alpha > 1);
bool rfp_allowed = !g_exact_search_mode && g_use_reverse_futility && depth <= 3 && ply > 0 && !in_check && std::abs(beta) < MATE_SCORE - 100;

if (rfp_allowed) {
    // Contract Repair 1: Non-PV Guard (B1, B2, B3)
    if (g_rfp_repair_mode >= 1 && is_pv_node) {
        rfp_allowed = false;
    }

    // Contract Repair 4: Zugzwang & Non-Pawn Material Guard (B3)
    if (g_rfp_repair_mode >= 3) {
        int us_rfp = b->side_to_move;
        uint64_t my_non_pawns = b->pieces[us_rfp][KNIGHT] | b->pieces[us_rfp][BISHOP] | 
                                b->pieces[us_rfp][ROOK]   | b->pieces[us_rfp][QUEEN];
        if (my_non_pawns == 0) {
            rfp_allowed = false;
        }
    }

    // Contract Repair 3: TT Upper-Bound Conflict Check (B3)
    if (g_rfp_repair_mode >= 3 && has_entry) {
        int tt_s = score_from_tt(entry.score, ply);
        if (entry.flag == TT_UPPER && tt_s < beta) {
            rfp_allowed = false;
        }
    }
}

if (rfp_allowed) {
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

        // Contract Repair 2: Store TT Lower Bound (B2, B3)
        if (g_rfp_repair_mode >= 2 && !aborted && excluded_move == 0) {
            if (g_search_variant == "X11" || g_search_variant == "X12" || g_search_variant == "X13" || g_search_variant == "X14" || g_search_variant == "X26" || g_num_threads > 1) {
                g_parallel_tt.store(key, static_eval, (int8_t)depth, TT_LOWER, ply, 0);
            } else {
                size_t tt_idx = key % TT_SIZE;
                TTEntry& entry_ref = g_tt[tt_idx];
                if (entry_ref.key != key || depth >= entry_ref.depth || entry_ref.age != g_tt_age) {
                    entry_ref.key = key;
                    entry_ref.score = (int16_t)score_to_tt(static_eval, ply);
                    entry_ref.depth = (int8_t)depth;
                    entry_ref.flag = TT_LOWER;
                    entry_ref.age = g_tt_age;
                    entry_ref.best_move = 0;
                }
            }
        }

        return static_eval;
    }
}
```

---

## 3. Parametric Ablation Architecture (B0 through B3)

To permit rigorous scientific attribution in Phase 10, the repairs are organized hierarchically:

| Ablation Level | Identifier | Non-PV Guard | TT Lower Store | TT Conflict Check | Zugzwang Guard | Description |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **B0** | `Legacy RFP` | ❌ | ❌ | ❌ | ❌ | Historical baseline behavior (identical to X22, X24, X25). |
| **B1** | `Non-PV RFP` | ✅ | ❌ | ❌ | ❌ | Restricts RFP strictly to Cut / Null-Window nodes. |
| **B2** | `TT-Recorded RFP` | ✅ | ✅ | ❌ | ❌ | B1 + records `TT_LOWER` bound in transposition table on cutoff. |
| **B3** | `Full X26 RFP` | ✅ | ✅ | ✅ | ✅ | B2 + suppresses RFP on TT upper-bound conflict and pure pawn endgames. |

### 3.1 Control Interfaces
- **UCI Protocol:**
  - `setoption name UCI_RfpRepair value true` (Activates B3 / full repair).
  - `setoption name UCI_RfpRepair value false` (Reverts to B0 / legacy).
  - `setoption name UCI_RfpRepairMode value <0..3>` (Explicitly selects B0, B1, B2, or B3).
- **C Native DLL Interface:**
  - `native_set_rfp_repair_mode(int mode)`
  - `native_get_rfp_repair_mode()`
- **Telemetry Query:**
  - `telemetry_report` outputs `rfp_repair_mode <0..3>`.

---

## 4. Search Variant `X26` Definition

Candidate `X26` is established as the active developmental baseline in `native_apply_search_variant("X26")`:
- **Evaluator Configuration:**
  - `g_use_backward_pawns = 0` (Removes the unstable backward pawn penalty from P1.18).
  - `g_use_king_file_exposure = 0` (Removes open file king penalty).
  - `g_use_connected_pawns = 1` (Preserves Option B connected & supported passers from P1.20).
  - `g_use_true_outposts = 1` (Preserves outpost piece evaluation from P1.16).
  - `g_use_pawn_hash = true` (64K entry thread-local pawn hash table).
- **Search Configuration:**
  - Track S (1T): `g_eval_mode = 5` (E5 Classical Combined), `g_rfp_margin_per_depth = 120`, `g_rfp_repair_mode = 3`.
  - Track P (4T): `g_eval_mode = 10` (E10 Enhanced Classical), `g_rfp_margin_per_depth = 90`, `g_rfp_repair_mode = 3`, `g_use_lmp = true` (L1 quadratic).

With the implementation complete, Phase 10 controlled ablations will rigorously evaluate B0, B1, B2, and B3.
