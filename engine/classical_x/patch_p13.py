#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.3 Engine Implementation Script
Adds:
  - Capture History & Countermove Heuristic (UCI_TacticalOrdering: M0..M3)
  - Singular Extensions (UCI_SingularExtensions: S0..S2)
  - Multi-Cut Pruning (UCI_MultiCut: C0..C1)
  - ProbCut Pruning (UCI_ProbCut: P0..P2)
  - Candidate X8 Variant (UCI_Variant: X8)
  - Strict bit-exact invariance when UCI_Variant X7 is selected.
"""

from pathlib import Path

CPP_PATH = Path(r"E:\ChessXML\project-janus-phase1\engine\classical_x\janus_classical_x.cpp")

def patch_engine():
    with open(CPP_PATH, "r", encoding="utf-8") as f:
        src = f.read()

    print(f"Original source length: {len(src):,} bytes")

    # 1. Add P1.3 Configuration Variables & Telemetry
    config_target = """// P1.2 Telemetry Counters
static uint64_t g_telemetry_conthist_probes = 0;
static uint64_t g_telemetry_conthist_cutoffs = 0;
static uint64_t g_telemetry_dynamic_lmr_reduced = 0;
static uint64_t g_telemetry_dynamic_lmr_researches = 0;
static uint64_t g_telemetry_eval_calls = 0;"""

    config_replacement = """// P1.2 Telemetry Counters
static uint64_t g_telemetry_conthist_probes = 0;
static uint64_t g_telemetry_conthist_cutoffs = 0;
static uint64_t g_telemetry_dynamic_lmr_reduced = 0;
static uint64_t g_telemetry_dynamic_lmr_researches = 0;
static uint64_t g_telemetry_eval_calls = 0;

// ============================================================================
// Milestone P1.3 Search Selectivity Options & Tables
// ============================================================================
static int g_tactical_ordering_mode = 0;   // 0=M0 (Off), 1=M1 (CapHist), 2=M2 (Countermove), 3=M3 (Combined)
static int g_singular_extension_mode = 0; // 0=S0 (Off), 1=S1 (Conservative SE), 2=S2 (Aggressive SE)
static int g_multicut_mode = 0;           // 0=C0 (Off), 1=C1 (Multi-Cut On)
static int g_probcut_mode = 0;            // 0=P0 (Off), 1=P1 (Conservative 200cp), 2=P2 (150cp)

// Capture History: [attacker 0..5][to_sq 0..63][victim 0..5]
static int16_t g_capture_history[6][64][6];

// Countermove Table: [prev_from 0..63][prev_to 0..63]
static uint16_t g_countermove_table[64][64];

// P1.3 Telemetry Counters
static uint64_t g_telemetry_capthist_probes = 0;
static uint64_t g_telemetry_capthist_cutoffs = 0;
static uint64_t g_telemetry_countermove_probes = 0;
static uint64_t g_telemetry_countermove_cutoffs = 0;
static uint64_t g_telemetry_se_probes = 0;
static uint64_t g_telemetry_se_extended = 0;
static uint64_t g_telemetry_multicut_cutoffs = 0;
static uint64_t g_telemetry_probcut_probes = 0;
static uint64_t g_telemetry_probcut_cutoffs = 0;"""

    assert config_target in src, "Failed to find config_target"
    src = src.replace(config_target, config_replacement)

    # 2. Update native_apply_search_variant to support X8 and ensure X7 sets M0, S0, C0, P0
    variant_target = """    } else if (var == "X7") { // P1.2 Integrated Candidate
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3 1-ply + 2-ply
        g_dynamic_lmr_mode = 3; // L3 Dynamic Log + Conthist
        g_eval_mode = 5; // E5 Combined Positional Eval
    }"""

    variant_replacement = """    } else if (var == "X7") { // P1.2 Frozen Baseline (Strict Bit-Exact Invariant)
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3 1-ply + 2-ply
        g_dynamic_lmr_mode = 3; // L3 Dynamic Log + Conthist
        g_eval_mode = 5; // E5 Combined Positional Eval
        g_tactical_ordering_mode = 0; // M0 Off
        g_singular_extension_mode = 0; // S0 Off
        g_multicut_mode = 0; // C0 Off
        g_probcut_mode = 0; // P0 Off
    } else if (var == "X8") { // P1.3 Integrated Candidate (Tactical Search Selectivity)
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3
        g_dynamic_lmr_mode = 3; // L3 Calibrated
        g_eval_mode = 5; // E5
        g_tactical_ordering_mode = 3; // M3 Capture History + Countermove
        g_singular_extension_mode = 1; // S1 Conservative SE
        g_multicut_mode = 1; // C1 Multi-Cut
        g_probcut_mode = 1; // P1 Conservative ProbCut
    }"""

    assert variant_target in src, "Failed to find variant_target"
    src = src.replace(variant_target, variant_replacement)

    # 3. Update score_move_for_ordering with Capture History & Countermove Heuristic
    # Captures:
    cap_order_target = """        if (g_use_see_ordering) {
            int see_val = janus_see(b, m);
            g_see_total_evaluations++;
            if (see_val > 0) {
                g_see_positive_captures++;
                return 100000 + mvv_lva;
            } else if (see_val == 0) {
                g_see_neutral_captures++;
                return 95000 + mvv_lva;
            } else {
                g_see_negative_captures++;
                g_see_ordering_inversions++;
                return 20000 + std::max(-10000, see_val) + mvv_lva;
            }
        }

        return 100000 + mvv_lva;"""

    cap_order_replacement = """        int cap_hist_bonus = 0;
        if ((g_tactical_ordering_mode == 1 || g_tactical_ordering_mode == 3) && attacker < 6 && victim < 6) {
            cap_hist_bonus = g_capture_history[attacker][to][victim];
            g_telemetry_capthist_probes++;
        }

        if (g_use_see_ordering) {
            int see_val = janus_see(b, m);
            g_see_total_evaluations++;
            if (see_val > 0) {
                g_see_positive_captures++;
                return 100000 + mvv_lva + cap_hist_bonus;
            } else if (see_val == 0) {
                g_see_neutral_captures++;
                return 95000 + mvv_lva + cap_hist_bonus;
            } else {
                g_see_negative_captures++;
                g_see_ordering_inversions++;
                return 20000 + std::max(-10000, see_val) + mvv_lva + cap_hist_bonus;
            }
        }

        return 100000 + mvv_lva + cap_hist_bonus;"""

    assert cap_order_target in src, "Failed to find cap_order_target"
    src = src.replace(cap_order_target, cap_order_replacement)

    # Countermove:
    killer_order_target = """    // Killer Moves (Quiet moves only)
    if (g_use_killer_ordering && ply >= 0 && ply < MAX_PLY) {
        if (m == g_killer_moves[ply][0]) return 90000;
        if (m == g_killer_moves[ply][1]) return 80000;
    }"""

    killer_order_replacement = """    // Killer Moves (Quiet moves only)
    if (g_use_killer_ordering && ply >= 0 && ply < MAX_PLY) {
        if (m == g_killer_moves[ply][0]) return 90000;
        if (m == g_killer_moves[ply][1]) return 80000;
    }

    // Countermove Heuristic (Quiet moves only)
    if ((g_tactical_ordering_mode == 2 || g_tactical_ordering_mode == 3) && ply >= 1 && g_ss[ply - 1].current_move != 0) {
        int prev_from = move_from(g_ss[ply - 1].current_move);
        int prev_to = move_to(g_ss[ply - 1].current_move);
        if (m == g_countermove_table[prev_from][prev_to]) {
            g_telemetry_countermove_probes++;
            return 75000; // Ordered immediately after Killer 2 (80,000)
        }
    }"""

    assert killer_order_target in src, "Failed to find killer_order_target"
    src = src.replace(killer_order_target, killer_order_replacement)

    # 4. Update negamax signature and add excluded_move parameter
    negamax_sig_target = """static int negamax(
    NativeBoard* b,
    int depth,
    int alpha,
    int beta,
    int ply,
    uint64_t& nodes,
    std::chrono::steady_clock::time_point deadline,
    bool& aborted,
    uint16_t* out_best_move
) {"""

    negamax_sig_replacement = """static int negamax(
    NativeBoard* b,
    int depth,
    int alpha,
    int beta,
    int ply,
    uint64_t& nodes,
    std::chrono::steady_clock::time_point deadline,
    bool& aborted,
    uint16_t* out_best_move,
    uint16_t excluded_move = 0
) {"""

    assert negamax_sig_target in src, "Failed to find negamax_sig_target"
    src = src.replace(negamax_sig_target, negamax_sig_replacement)

    # Singular Extension & Multi-Cut logic right after TT probe
    tt_probe_target = """    if (entry.key == key) {
        tt_move = entry.best_move;
        if (entry.depth >= depth && ply > 0) {
            int tt_score = score_from_tt(entry.score, ply);
            if (entry.flag == TT_EXACT) return tt_score;
            if (entry.flag == TT_LOWER && tt_score >= beta) return tt_score;
            if (entry.flag == TT_UPPER && tt_score <= alpha) return tt_score;
        }
    }"""

    tt_probe_replacement = """    if (entry.key == key) {
        tt_move = entry.best_move;
        if (entry.depth >= depth && ply > 0 && excluded_move == 0) {
            int tt_score = score_from_tt(entry.score, ply);
            if (entry.flag == TT_EXACT) return tt_score;
            if (entry.flag == TT_LOWER && tt_score >= beta) return tt_score;
            if (entry.flag == TT_UPPER && tt_score <= alpha) return tt_score;
        }
    }

    int extension = 0;
    // Singular Extension & Multi-Cut Verification (Phases 3 & 4)
    if (g_singular_extension_mode > 0 &&
        depth >= 6 &&
        ply > 0 &&
        excluded_move == 0 &&
        tt_move != 0 &&
        entry.key == key &&
        entry.depth >= depth - 3 &&
        entry.flag != TT_UPPER &&
        std::abs(entry.score) < MATE_THRESHOLD) {

        g_telemetry_se_probes++;
        int se_margin = (g_singular_extension_mode == 1) ? (2 * depth) : (depth + 15);
        int se_beta = entry.score - se_margin;
        int se_depth = (depth - 1) / 2;

        int se_score = negamax(b, se_depth, se_beta - 1, se_beta, ply, nodes, deadline, aborted, nullptr, tt_move);

        if (aborted) return 0;

        if (se_score < se_beta) {
            // Move is singular! All alternatives failed low
            extension = 1;
            g_telemetry_se_extended++;
        } else if (g_multicut_mode > 0 && se_score >= beta) {
            // Multi-Cut: an alternative move beat beta
            g_telemetry_multicut_cutoffs++;
            return se_score;
        }
    }"""

    assert tt_probe_target in src, "Failed to find tt_probe_target"
    src = src.replace(tt_probe_target, tt_probe_replacement)

    # ProbCut logic after NMP
    probcut_target = """    int orig_alpha = alpha;
    uint16_t best_move = 0;"""

    probcut_replacement = """    // ProbCut Pruning (Phase 5)
    if (g_probcut_mode > 0 &&
        depth >= 5 &&
        ply > 0 &&
        excluded_move == 0 &&
        !in_check &&
        std::abs(beta) < MATE_THRESHOLD) {

        int pc_margin = (g_probcut_mode == 1) ? 200 : 150;
        int pc_beta = beta + pc_margin;

        if (pc_beta < MATE_THRESHOLD) {
            g_telemetry_probcut_probes++;
            uint16_t pc_caps[MAX_MOVES];
            int pc_count = native_generate_captures(b, pc_caps);

            for (int pci = 0; pci < pc_count; pci++) {
                uint16_t pcm = pc_caps[pci];
                if (janus_see(b, pcm) < 0) continue;

                UndoInfo pc_undo;
                if (!native_make_move(b, pcm, &pc_undo)) continue;

                int pc_score = -negamax(b, depth - 4, -pc_beta, -pc_beta + 1, ply + 1, nodes, deadline, aborted, nullptr);

                native_unmake_move(b, pcm, &pc_undo);

                if (aborted) return 0;

                if (pc_score >= pc_beta) {
                    g_telemetry_probcut_cutoffs++;
                    return beta;
                }
            }
        }
    }

    int orig_alpha = alpha;
    uint16_t best_move = 0;"""

    assert probcut_target in src, "Failed to find probcut_target"
    src = src.replace(probcut_target, probcut_replacement)

    # Skip excluded move in loop and apply extension to child_depth
    move_loop_target = """        legal_moves_count++;
        if (best_move == 0) best_move = m;"""

    move_loop_replacement = """        if (m == excluded_move) continue;

        legal_moves_count++;
        if (best_move == 0) best_move = m;"""

    assert move_loop_target in src, "Failed to find move_loop_target"
    src = src.replace(move_loop_target, move_loop_replacement)

    child_depth_target = """        int child_depth = depth - 1;"""
    child_depth_replacement = """        int child_depth = depth - 1 + (m == tt_move ? extension : 0);"""
    assert child_depth_target in src, "Failed to find child_depth_target"
    src = src.replace(child_depth_target, child_depth_replacement)

    # Calibrated LMR history threshold for X8
    lmr_mod_target = """                int tot_h = h + ch1 + ch2;
                if (tot_h > 10000) dynamic_reduction -= 1;
                else if (tot_h < -5000) dynamic_reduction += 1;
                if (dynamic_reduction < 1) dynamic_reduction = 1;"""

    lmr_mod_replacement = """                int tot_h = h + ch1 + ch2;
                int h_thresh = (g_search_variant == "X8") ? std::max(1000, 250 * depth) : 10000;
                int h_neg_thresh = (g_search_variant == "X8") ? (-h_thresh / 2) : -5000;
                if (tot_h > h_thresh) dynamic_reduction -= 1;
                else if (tot_h < h_neg_thresh) dynamic_reduction += 1;
                if (dynamic_reduction < 1) dynamic_reduction = 1;"""

    assert lmr_mod_target in src, "Failed to find lmr_mod_target"
    src = src.replace(lmr_mod_target, lmr_mod_replacement)

    # Update cutoffs with Capture History and Countermove recording
    cutoff_rec_target = """                    } else {
                        // Gravity history update
                        g_telemetry_conthist_cutoffs++;
                        int bonus = std::min(300, depth * depth);
                        int cur_h = g_history_table[side][from][to];
                        g_history_table[side][from][to] = cur_h + bonus - (cur_h * std::abs(bonus)) / 16384;"""

    cutoff_rec_replacement = """                    } else {
                        // Gravity history update
                        g_telemetry_conthist_cutoffs++;
                        int bonus = std::min(300, depth * depth);
                        int cur_h = g_history_table[side][from][to];
                        g_history_table[side][from][to] = cur_h + bonus - (cur_h * std::abs(bonus)) / 16384;

                        // Countermove heuristic update (Phase 2)
                        if ((g_tactical_ordering_mode == 2 || g_tactical_ordering_mode == 3) && ply >= 1 && g_ss[ply - 1].current_move != 0) {
                            int prev_from = move_from(g_ss[ply - 1].current_move);
                            int prev_to = move_to(g_ss[ply - 1].current_move);
                            g_countermove_table[prev_from][prev_to] = m;
                            g_telemetry_countermove_cutoffs++;
                        }"""

    assert cutoff_rec_target in src, "Failed to find cutoff_rec_target"
    src = src.replace(cutoff_rec_target, cutoff_rec_replacement)

    cap_cutoff_target = """            } else {
                g_ordering_cutoff_captures++;
            }"""

    cap_cutoff_replacement = """            } else {
                g_ordering_cutoff_captures++;
                // Capture History update (Phase 2)
                if ((g_tactical_ordering_mode == 1 || g_tactical_ordering_mode == 3) && undo.captured_piece < 6) {
                    int from_sq = move_from(m);
                    int to_sq = move_to(m);
                    int attacker = moved_piece;
                    int victim = undo.captured_piece;
                    if (attacker < 6 && victim < 6) {
                        int bonus = std::min(300, depth * depth);
                        int cur_c = g_capture_history[attacker][to_sq][victim];
                        g_capture_history[attacker][to_sq][victim] = (int16_t)(cur_c + bonus - (cur_c * std::abs(bonus)) / 16384);
                        g_telemetry_capthist_cutoffs++;
                    }
                }
            }"""

    assert cap_cutoff_target in src, "Failed to find cap_cutoff_target"
    src = src.replace(cap_cutoff_target, cap_cutoff_replacement)

    # TT store exclusion guard
    tt_store_target = """    // Store TT entry with normalized mate scores and depth-preferred replacement
    if (!aborted) {"""

    tt_store_replacement = """    // Store TT entry with normalized mate scores and depth-preferred replacement (Never store during excluded searches)
    if (!aborted && excluded_move == 0) {"""

    assert tt_store_target in src, "Failed to find tt_store_target"
    src = src.replace(tt_store_target, tt_store_replacement)

    # 5. Clear tables in native_search
    clear_target = """    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    std::memset(g_ss, 0, sizeof(g_ss));"""

    clear_replacement = """    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    std::memset(g_ss, 0, sizeof(g_ss));
    if (g_tactical_ordering_mode > 0) {
        std::memset(g_countermove_table, 0, sizeof(g_countermove_table));
    }"""

    assert clear_target in src, "Failed to find clear_target"
    src = src.replace(clear_target, clear_replacement)

    # 6. Add exports
    export_target = """EXPORT void native_get_p12_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_telemetry_conthist_probes;
        out_arr[1] = g_telemetry_conthist_cutoffs;
        out_arr[2] = g_telemetry_dynamic_lmr_reduced;
        out_arr[3] = g_telemetry_dynamic_lmr_researches;
        out_arr[4] = g_telemetry_eval_calls;
    }
}"""

    export_replacement = """EXPORT void native_get_p12_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_telemetry_conthist_probes;
        out_arr[1] = g_telemetry_conthist_cutoffs;
        out_arr[2] = g_telemetry_dynamic_lmr_reduced;
        out_arr[3] = g_telemetry_dynamic_lmr_researches;
        out_arr[4] = g_telemetry_eval_calls;
    }
}

// ============================================================================
// Milestone P1.3 Control & Telemetry Exports
// ============================================================================
EXPORT void native_set_tactical_ordering_mode(int mode) { g_tactical_ordering_mode = mode; }
EXPORT void native_set_singular_extension_mode(int mode) { g_singular_extension_mode = mode; }
EXPORT void native_set_multicut_mode(int mode) { g_multicut_mode = mode; }
EXPORT void native_set_probcut_mode(int mode) { g_probcut_mode = mode; }

EXPORT void native_clear_tactical_tables() {
    std::memset(g_capture_history, 0, sizeof(g_capture_history));
    std::memset(g_countermove_table, 0, sizeof(g_countermove_table));
}

EXPORT void native_reset_p13_telemetry() {
    native_reset_p12_telemetry();
    g_telemetry_capthist_probes = 0;
    g_telemetry_capthist_cutoffs = 0;
    g_telemetry_countermove_probes = 0;
    g_telemetry_countermove_cutoffs = 0;
    g_telemetry_se_probes = 0;
    g_telemetry_se_extended = 0;
    g_telemetry_multicut_cutoffs = 0;
    g_telemetry_probcut_probes = 0;
    g_telemetry_probcut_cutoffs = 0;
}

EXPORT void native_get_p13_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_telemetry_capthist_probes;
        out_arr[1] = g_telemetry_capthist_cutoffs;
        out_arr[2] = g_telemetry_countermove_probes;
        out_arr[3] = g_telemetry_countermove_cutoffs;
        out_arr[4] = g_telemetry_se_probes;
        out_arr[5] = g_telemetry_se_extended;
        out_arr[6] = g_telemetry_multicut_cutoffs;
        out_arr[7] = g_telemetry_probcut_probes;
        out_arr[8] = g_telemetry_probcut_cutoffs;
    }
}"""

    assert export_target in src, "Failed to find export_target"
    src = src.replace(export_target, export_replacement)

    # 7. Update UCI Loop options & telemetry
    uci_id_target = 'std::cout << "id name Janus Classical X (P1.2 Candidate X7)" << std::endl;'
    uci_id_replacement = 'std::cout << "id name Janus Classical X (P1.3 Candidate X8)" << std::endl;'
    assert uci_id_target in src, "Failed to find uci_id_target"
    src = src.replace(uci_id_target, uci_id_replacement)

    uci_opts_target = """            std::cout << "option name UCI_Variant type combo default X7 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7" << std::endl;
            std::cout << "option name UCI_ContinuationHistory type combo default H3 var H0 var H1 var H2 var H3" << std::endl;
            std::cout << "option name UCI_DynamicLMR type combo default L3 var L0 var L1 var L2 var L3" << std::endl;
            std::cout << "option name UCI_ClassicalEval type combo default E5 var E0 var E1 var E2 var E3 var E4 var E5" << std::endl;"""

    uci_opts_replacement = """            std::cout << "option name UCI_Variant type combo default X8 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8" << std::endl;
            std::cout << "option name UCI_ContinuationHistory type combo default H3 var H0 var H1 var H2 var H3" << std::endl;
            std::cout << "option name UCI_DynamicLMR type combo default L3 var L0 var L1 var L2 var L3" << std::endl;
            std::cout << "option name UCI_ClassicalEval type combo default E5 var E0 var E1 var E2 var E3 var E4 var E5" << std::endl;
            std::cout << "option name UCI_TacticalOrdering type combo default M3 var M0 var M1 var M2 var M3" << std::endl;
            std::cout << "option name UCI_SingularExtensions type combo default S1 var S0 var S1 var S2" << std::endl;
            std::cout << "option name UCI_MultiCut type combo default C1 var C0 var C1" << std::endl;
            std::cout << "option name UCI_ProbCut type combo default P1 var P0 var P1 var P2" << std::endl;"""

    assert uci_opts_target in src, "Failed to find uci_opts_target"
    src = src.replace(uci_opts_target, uci_opts_replacement)

    setoption_target = """                } else if (opt_name == "UCI_ClassicalEval" && !opt_val.empty()) {
                    if (opt_val == "E0") g_eval_mode = 0;
                    else if (opt_val == "E1") g_eval_mode = 1;
                    else if (opt_val == "E2") g_eval_mode = 2;
                    else if (opt_val == "E3") g_eval_mode = 3;
                    else if (opt_val == "E4") g_eval_mode = 4;
                    else if (opt_val == "E5") g_eval_mode = 5;
                }"""

    setoption_replacement = """                } else if (opt_name == "UCI_ClassicalEval" && !opt_val.empty()) {
                    if (opt_val == "E0") g_eval_mode = 0;
                    else if (opt_val == "E1") g_eval_mode = 1;
                    else if (opt_val == "E2") g_eval_mode = 2;
                    else if (opt_val == "E3") g_eval_mode = 3;
                    else if (opt_val == "E4") g_eval_mode = 4;
                    else if (opt_val == "E5") g_eval_mode = 5;
                } else if (opt_name == "UCI_TacticalOrdering" && !opt_val.empty()) {
                    if (opt_val == "M0") g_tactical_ordering_mode = 0;
                    else if (opt_val == "M1") g_tactical_ordering_mode = 1;
                    else if (opt_val == "M2") g_tactical_ordering_mode = 2;
                    else if (opt_val == "M3") g_tactical_ordering_mode = 3;
                } else if (opt_name == "UCI_SingularExtensions" && !opt_val.empty()) {
                    if (opt_val == "S0") g_singular_extension_mode = 0;
                    else if (opt_val == "S1") g_singular_extension_mode = 1;
                    else if (opt_val == "S2") g_singular_extension_mode = 2;
                } else if (opt_name == "UCI_MultiCut" && !opt_val.empty()) {
                    if (opt_val == "C0") g_multicut_mode = 0;
                    else if (opt_val == "C1") g_multicut_mode = 1;
                } else if (opt_name == "UCI_ProbCut" && !opt_val.empty()) {
                    if (opt_val == "P0") g_probcut_mode = 0;
                    else if (opt_val == "P1") g_probcut_mode = 1;
                    else if (opt_val == "P2") g_probcut_mode = 2;
                }"""

    assert setoption_target in src, "Failed to find setoption_target"
    src = src.replace(setoption_target, setoption_replacement)

    telemetry_rep_target = """            std::cout << "eval_calls " << g_telemetry_eval_calls << std::endl;
            std::cout << "TELEMETRY_END" << std::endl;"""

    telemetry_rep_replacement = """            std::cout << "eval_calls " << g_telemetry_eval_calls << std::endl;
            std::cout << "tactical_ordering_mode " << g_tactical_ordering_mode << std::endl;
            std::cout << "singular_extension_mode " << g_singular_extension_mode << std::endl;
            std::cout << "multicut_mode " << g_multicut_mode << std::endl;
            std::cout << "probcut_mode " << g_probcut_mode << std::endl;
            std::cout << "capthist_probes " << g_telemetry_capthist_probes << std::endl;
            std::cout << "capthist_cutoffs " << g_telemetry_capthist_cutoffs << std::endl;
            std::cout << "countermove_probes " << g_telemetry_countermove_probes << std::endl;
            std::cout << "countermove_cutoffs " << g_telemetry_countermove_cutoffs << std::endl;
            std::cout << "se_probes " << g_telemetry_se_probes << std::endl;
            std::cout << "se_extended " << g_telemetry_se_extended << std::endl;
            std::cout << "multicut_cutoffs " << g_telemetry_multicut_cutoffs << std::endl;
            std::cout << "probcut_probes " << g_telemetry_probcut_probes << std::endl;
            std::cout << "probcut_cutoffs " << g_telemetry_probcut_cutoffs << std::endl;
            std::cout << "TELEMETRY_END" << std::endl;"""

    assert telemetry_rep_target in src, "Failed to find telemetry_rep_target"
    src = src.replace(telemetry_rep_target, telemetry_rep_replacement)

    ucinewgame_target = """        } else if (cmd == "ucinewgame") {
            native_reset_history();
            native_clear_conthist();"""

    ucinewgame_replacement = """        } else if (cmd == "ucinewgame") {
            native_reset_history();
            native_clear_conthist();
            native_clear_tactical_tables();"""

    assert ucinewgame_target in src, "Failed to find ucinewgame_target"
    src = src.replace(ucinewgame_target, ucinewgame_replacement)

    with open(CPP_PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"Successfully patched {CPP_PATH} ({len(src):,} bytes).")

if __name__ == "__main__":
    patch_engine()

