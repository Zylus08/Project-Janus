import os
import re

X23_SRC = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.18\control\janus_classical_x23.cpp"
TARGET_SRC = r"E:\ChessXML\project-janus-phase1\engine\classical_x\janus_classical_x.cpp"

with open(X23_SRC, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Default variant
code = code.replace(
    'static std::string g_search_variant = "X23";',
    'static std::string g_search_variant = "X24";'
)

# 2. native_init default variant
code = code.replace(
    'native_apply_search_variant("X23");',
    'native_apply_search_variant("X24");'
)

# 3. Add X24 block to native_apply_search_variant
x24_block = """    } else if (var == "X24") { // P1.19 Candidate: Track A Isolated (Backward Pawns + True Outposts + 64K Pawn Hash, Zero King File Exposure)
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3
        g_dynamic_lmr_mode = 3; // L3 Calibrated LMR
        g_use_pruning_safety = false;
        g_movepicker_stage_reform = true;
        g_adaptive_capture_mode = 1; // C1 Near-Even Capture Promotion
        g_qsearch_mode = 1; // Q1 Corrected Quiescence Search
        g_use_true_outposts = 1; // True Outposts with Pawn Immunity
        g_use_backward_pawns = 1; // Track A: Classical Backward Pawn Detection Enabled
        g_use_king_file_exposure = 0; // Track B: King File Exposure Penalty Permanently DISABLED
        if (g_num_threads == 1) { // Track S: X24-S (1T)
            g_eval_mode = 5; // E5 Combined Classical Eval
            g_tactical_ordering_mode = 2; // Enable Countermove table for staging
            g_singular_extension_mode = 0; // S0 Off
            g_multicut_mode = 0; // C0 Off
            g_probcut_mode = 0; // P0 Off
            g_use_pawn_hash = true; // 64K entry Pawn Hash Table
            g_dynamic_time_mgmt = false;
            g_use_lmp = false;
            g_lmp_mode = 0;
            g_rfp_margin_per_depth = 120;
        } else { // Track P: X24-P (4T)
            g_eval_mode = 10; // E10 Enhanced Classical Evaluation
            g_tactical_ordering_mode = 2; // M2 Countermove Heuristic
            g_singular_extension_mode = 0; // S0 Off
            g_multicut_mode = 0; // C0 Off
            g_probcut_mode = 0; // P0 Off
            g_use_pawn_hash = true; // 64K entry Pawn Hash Table
            g_dynamic_time_mgmt = true;
            g_use_lmp = true; // Safe Late Move Pruning
            g_lmp_mode = 1; // Conservative Quadratic LMP
            g_lmp_max_depth = 4;
            g_rfp_margin_per_depth = 90;
        }
"""

target_marker = '    } else if (var == "X23") {'
code = code.replace(target_marker, x24_block + target_marker)

# 4. Pure pawn endgame LMR check
old_lmr = 'g_search_variant == "X23"'
new_lmr = 'g_search_variant == "X23" || g_search_variant == "X24"'
code = code.replace(old_lmr, new_lmr)

# 5. UCI identification
code = code.replace(
    'std::cout << "id name Janus Classical X (P1.18 Candidate X23)" << std::endl;',
    'std::cout << "id name Janus Classical X (P1.19 Candidate X24)" << std::endl;'
)

# 6. UCI_Variant combo option
old_combo = 'default X23 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11 var X12 var X13 var X14 var X15 var X16 var X17 var X18 var X19 var X20 var X21 var X22 var X23'
new_combo = 'default X24 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11 var X12 var X13 var X14 var X15 var X16 var X17 var X18 var X19 var X20 var X21 var X22 var X23 var X24'
code = code.replace(old_combo, new_combo)

with open(TARGET_SRC, "w", encoding="utf-8") as f:
    f.write(code)

print("X24 source generated successfully at:", TARGET_SRC)
