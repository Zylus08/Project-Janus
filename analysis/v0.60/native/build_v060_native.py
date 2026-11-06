"""Project Janus v0.60 - Script to generate and compile native NNUE engine and DLL."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V56_CPP = ROOT / "analysis" / "v0.56" / "native" / "janus_native.cpp"
V60_DIR = ROOT / "analysis" / "v0.60" / "native"
V60_CPP = V60_DIR / "janus_native.cpp"

with open(V56_CPP, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Include nnue_v1.h at top
code = "#include \"nnue_v1.h\"\n" + code

# 2. Add NNUE State and Helpers right before quiescence
nnue_helpers = """
// ============================================================================
// NNUE Neural Value Evaluation State & Bridge (Project Janus v0.60)
// ============================================================================

static bool g_use_neural_value = false;
static std::string g_neural_value_model_path = "analysis/v0.60/models/janus_nnue_v1_small.jnnue";
static int g_neural_value_blend = 100; // 0 = Pure Classical, 100 = Pure Neural, 50 = 50/50 Blend
static NNUEEvaluator g_nnue;
static Accumulator g_accum_stack[MAX_SEARCH_PLY + 64];

EXPORT void native_set_neural_value_options(bool enabled, const char* model_path, int blend) {
    g_use_neural_value = enabled;
    g_neural_value_blend = std::clamp(blend, 0, 100);
    if (model_path != nullptr && std::strlen(model_path) > 0) {
        g_neural_value_model_path = model_path;
        g_nnue.load_model(g_neural_value_model_path);
    } else if (enabled && !g_nnue.is_loaded()) {
        g_nnue.load_model(g_neural_value_model_path);
    }
}

EXPORT int native_evaluate_neural(const NativeBoard* b) {
    if (!g_nnue.is_loaded()) {
        g_nnue.load_model(g_neural_value_model_path);
    }
    if (!g_nnue.is_loaded()) return native_evaluate(b);
    Accumulator acc;
    g_nnue.full_refresh(b->pieces, b->side_to_move, &acc);
    return g_nnue.evaluate(&acc, b->side_to_move);
}

static inline void update_nnue_acc_for_move(
    const NativeBoard* b_before,
    uint16_t m,
    const UndoInfo* undo,
    int ply
) {
    if (!g_use_neural_value || !g_nnue.is_loaded()) return;
    if (ply >= MAX_SEARCH_PLY + 60) return;

    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);
    int us = b_before->side_to_move;
    int them = 1 - us;

    int piece = NO_PIECE;
    for (int p = 0; p < 6; p++) {
        if (b_before->pieces[us][p] & (1ULL << from)) {
            piece = p;
            break;
        }
    }
    if (piece == NO_PIECE) return;

    Accumulator* next_acc = &g_accum_stack[ply + 1];
    const Accumulator* prev_acc = &g_accum_stack[ply];

    if (flag == 1) { // Castling
        int r_from = 0, r_to = 0;
        if (to == 6) { r_from = 7; r_to = 5; }
        else if (to == 2) { r_from = 0; r_to = 3; }
        else if (to == 62) { r_from = 63; r_to = 61; }
        else if (to == 58) { r_from = 56; r_to = 59; }
        g_nnue.update_castling(next_acc, prev_acc, us, from, to, r_from, r_to, b_before->pieces);
    } else if (flag == 2) { // En Passant
        int ep_cap_sq = (us == WHITE) ? (to - 8) : (to + 8);
        g_nnue.update_en_passant(next_acc, prev_acc, us, from, to, ep_cap_sq, b_before->pieces);
    } else if (flag == 3) { // Promotion
        int promo_piece = promo + 1; // 1=KNIGHT, 2=BISHOP, 3=ROOK, 4=QUEEN
        g_nnue.update_promotion(next_acc, prev_acc, us, from, to, promo_piece,
                                undo->captured_piece != NO_PIECE, them, undo->captured_piece, b_before->pieces);
    } else if (undo->captured_piece != NO_PIECE) { // Capture
        g_nnue.update_capture(next_acc, prev_acc, us, piece, from, to, them, undo->captured_piece, b_before->pieces);
    } else { // Quiet Move
        g_nnue.update_quiet(next_acc, prev_acc, us, piece, from, to, b_before->pieces);
    }
}
"""

pos_q = code.find("static int quiescence(")
code = code[:pos_q] + nnue_helpers + "\n" + code[pos_q:]

# 3. Update quiescence definition to accept ply
old_q_def = """static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted) {"""
new_q_def = """static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted, int ply = 0) {"""
code = code.replace(old_q_def, new_q_def)

# 4. Quiescence evaluation selection (stand_pat)
old_stand_pat = "int stand_pat = native_evaluate(b);"
new_stand_pat = """int stand_pat;
    if (g_use_neural_value && g_nnue.is_loaded()) {
        int nnue_score = g_nnue.evaluate(&g_accum_stack[ply], b->side_to_move);
        if (g_neural_value_blend >= 100) {
            stand_pat = nnue_score;
        } else if (g_neural_value_blend <= 0) {
            stand_pat = native_evaluate(b);
        } else {
            stand_pat = (nnue_score * g_neural_value_blend + native_evaluate(b) * (100 - g_neural_value_blend)) / 100;
        }
    } else {
        stand_pat = native_evaluate(b);
    }"""
code = code.replace(old_stand_pat, new_stand_pat)

# 5. Quiescence recursive make move
old_q_make = """        UndoInfo undo;
        native_make_move(b, m, &undo);
        int score = -quiescence(b, -beta, -alpha, nodes, deadline, aborted);
        native_unmake_move(b, m, &undo);"""

new_q_make = """        UndoInfo undo;
        NativeBoard board_copy = *b;
        native_make_move(b, m, &undo);
        if (g_use_neural_value) {
            update_nnue_acc_for_move(&board_copy, m, &undo, ply);
        }
        int score = -quiescence(b, -beta, -alpha, nodes, deadline, aborted, ply + 1);
        native_unmake_move(b, m, &undo);"""
code = code.replace(old_q_make, new_q_make)

# 6. Negamax leaf call to quiescence
old_negamax_leaf = "return quiescence(b, alpha, beta, nodes, deadline, aborted);"
new_negamax_leaf = "return quiescence(b, alpha, beta, nodes, deadline, aborted, ply);"
code = code.replace(old_negamax_leaf, new_negamax_leaf)

# 7. Negamax make move
old_nega_make = """        UndoInfo undo;
        native_make_move(b, m, &undo);

        int score;"""

new_nega_make = """        UndoInfo undo;
        NativeBoard board_copy = *b;
        native_make_move(b, m, &undo);
        if (g_use_neural_value) {
            update_nnue_acc_for_move(&board_copy, m, &undo, ply);
        }

        int score;"""
code = code.replace(old_nega_make, new_nega_make)

# 8. native_search: root full refresh
old_search_start = """    bool aborted = false;
    g_tt_age++;"""

new_search_start = """    bool aborted = false;
    g_tt_age++;

    if (g_use_neural_value) {
        if (!g_nnue.is_loaded()) {
            g_nnue.load_model(g_neural_value_model_path);
        }
        if (g_nnue.is_loaded()) {
            g_nnue.full_refresh(b->pieces, b->side_to_move, &g_accum_stack[0]);
        }
    }"""
code = code.replace(old_search_start, new_search_start)

# 9. UCI Options output
old_uci_opts = """            std::cout << "option name UseSEEInQuiescence type check default false" << std::endl;
            std::cout << "uciok" << std::endl;"""

new_uci_opts = """            std::cout << "option name UseSEEInQuiescence type check default false" << std::endl;
            std::cout << "option name UseNeuralValue type check default false" << std::endl;
            std::cout << "option name NeuralValueModelPath type string default analysis/v0.60/models/janus_nnue_v1_small.jnnue" << std::endl;
            std::cout << "option name NeuralValueBlend type spin default 100 min 0 max 100" << std::endl;
            std::cout << "uciok" << std::endl;"""
code = code.replace(old_uci_opts, new_uci_opts)

# 10. UCI setoption parsing
old_setopt = """                } else if (opt_name == "useseeinquiescence") {
                    g_use_see_in_quiescence = (opt_val == "true");
                }"""

new_setopt = """                } else if (opt_name == "useseeinquiescence") {
                    g_use_see_in_quiescence = (opt_val == "true");
                } else if (opt_name == "useneuralvalue") {
                    g_use_neural_value = (opt_val == "true");
                    if (g_use_neural_value && !g_nnue.is_loaded()) {
                        g_nnue.load_model(g_neural_value_model_path);
                    }
                } else if (opt_name == "neuralvaluemodelpath") {
                    g_neural_value_model_path = opt_val;
                    g_nnue.load_model(g_neural_value_model_path);
                } else if (opt_name == "neuralvalueblend") {
                    try { g_neural_value_blend = std::stoi(opt_val); } catch (...) {}
                }"""
code = code.replace(old_setopt, new_setopt)

with open(V60_CPP, "w", encoding="utf-8") as f:
    f.write(code)

print(f"Generated {V60_CPP} ({len(code):,} characters, {len(code.splitlines())} lines).")
