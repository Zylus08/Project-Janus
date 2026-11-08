#!/usr/bin/env python3
"""Project Janus v0.61 - Native Build & Compilation Pipeline for NNUE-V2.

Generates janus_native.cpp for v0.61 with NNUE-V2 and AVX2 SIMD integration,
compiling both standalone executable and shared DLL with MSVC.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V56_CPP = ROOT / "analysis" / "v0.56" / "native" / "janus_native.cpp"
V61_DIR = ROOT / "analysis" / "v0.61" / "native"
V61_CPP = V61_DIR / "janus_native.cpp"


def generate_v061_cpp():
    print(f"Generating {V61_CPP.name} from C1 Baseline...")
    with open(V56_CPP, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Include nnue_v2.h at top
    code = "#include \"nnue_v2.h\"\n" + code

    # 2. Add NNUE-V2 State and Helpers right before quiescence
    nnue_v2_helpers = """
// ============================================================================
// NNUE-V2 Neural Value Evaluation State & Bridge (Project Janus v0.61)
// ============================================================================

static bool g_use_neural_value = false;
static std::string g_neural_value_model_path = "analysis/v0.61/models/janus_nnue_v2_small.jnnue";
static int g_neural_value_blend = 100; // 0 = Pure Classical, 100 = Pure Neural, 50 = 50/50 Blend
static bool g_neural_use_avx2 = true;
static nnue_v2::NNUEEvaluatorV2 g_nnue;
static nnue_v2::Accumulator g_accum_stack[MAX_SEARCH_PLY + 64];

EXPORT void native_set_neural_value_options(bool enabled, const char* model_path, int blend, bool use_avx2) {
    g_use_neural_value = enabled;
    g_neural_value_blend = std::clamp(blend, 0, 100);
    g_neural_use_avx2 = use_avx2;
    g_nnue.set_use_avx2(use_avx2);
    if (model_path != nullptr && std::strlen(model_path) > 0) {
        g_neural_value_model_path = model_path;
        if (enabled) {
            g_nnue.load_model(g_neural_value_model_path);
        }
    } else if (enabled && !g_nnue.is_loaded()) {
        g_nnue.load_model(g_neural_value_model_path);
    }
}

EXPORT int native_evaluate_neural(const NativeBoard* b) {
    if (!g_nnue.is_loaded()) {
        g_nnue.load_model(g_neural_value_model_path);
    }
    if (!g_nnue.is_loaded()) return native_evaluate(b);
    nnue_v2::Accumulator acc;
    g_nnue.full_refresh(b->pieces, b->side_to_move, &acc);
    return g_nnue.evaluate(&acc, b->side_to_move);
}

static inline void update_nnue_acc_for_move(
    const NativeBoard* b_before,
    const NativeBoard* b_after,
    uint16_t m,
    const UndoInfo* undo,
    int ply
) {
    if (!g_use_neural_value || !g_nnue.is_loaded()) return;
    if (ply >= MAX_SEARCH_PLY + 60) return;

    int flag = move_flag(m);
    nnue_v2::Accumulator* next_acc = &g_accum_stack[ply + 1];
    const nnue_v2::Accumulator* prev_acc = &g_accum_stack[ply];

    if (flag != 0) {
        // Special moves (castling, en-passant, promotion): robust full refresh on the child position
        g_nnue.full_refresh(b_after->pieces, b_after->side_to_move, next_acc);
        return;
    }

    int from = move_from(m);
    int to = move_to(m);
    int us = b_before->side_to_move;
    int them = 1 - us;

    int piece = NO_PIECE;
    for (int p = 0; p < 6; p++) {
        if (b_before->pieces[us][p] & (1ULL << from)) {
            piece = p;
            break;
        }
    }
    if (piece == NO_PIECE) {
        g_nnue.full_refresh(b_after->pieces, b_after->side_to_move, next_acc);
        return;
    }

    if (undo->captured_piece != NO_PIECE) {
        g_nnue.update_capture(next_acc, prev_acc, us, piece, from, to, them, undo->captured_piece, b_before->pieces);
    } else {
        g_nnue.update_quiet(next_acc, prev_acc, us, piece, from, to, b_before->pieces);
    }
}
"""

    pos_q = code.find("static int quiescence(")
    assert pos_q != -1, "quiescence function not found"
    code = code[:pos_q] + nnue_v2_helpers + "\n" + code[pos_q:]

    # 3. Update quiescence definition to accept ply
    old_q_def = "static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted) {"
    new_q_def = "static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted, int ply = 0) {"
    assert old_q_def in code, "old_q_def not found"
    code = code.replace(old_q_def, new_q_def)

    # 4. Quiescence evaluation selection (stand_pat)
    old_stand_pat = "    int stand_pat = native_evaluate(b);"
    new_stand_pat = """    int stand_pat;
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
    assert old_stand_pat in code, "old_stand_pat not found"
    code = code.replace(old_stand_pat, new_stand_pat)

    # 5. Quiescence recursive make move
    old_q_make = """    for (int i = 0; i < n_caps; i++) {
        if (!native_make_move(b, caps[i].m, &undo)) continue;
        int score = -quiescence(b, -beta, -alpha, nodes, deadline, aborted);
        native_unmake_move(b, caps[i].m, &undo);"""

    new_q_make = """    for (int i = 0; i < n_caps; i++) {
        NativeBoard board_copy = *b;
        if (!native_make_move(b, caps[i].m, &undo)) continue;
        if (g_use_neural_value) {
            update_nnue_acc_for_move(&board_copy, b, caps[i].m, &undo, ply);
        }
        int score = -quiescence(b, -beta, -alpha, nodes, deadline, aborted, ply + 1);
        native_unmake_move(b, caps[i].m, &undo);"""
    assert old_q_make in code, "old_q_make not found"
    code = code.replace(old_q_make, new_q_make)

    # 6. Negamax leaf call to quiescence
    old_negamax_leaf = "return quiescence(b, alpha, beta, nodes, deadline, aborted);"
    new_negamax_leaf = "return quiescence(b, alpha, beta, nodes, deadline, aborted, ply);"
    assert old_negamax_leaf in code, "old_negamax_leaf not found"
    code = code.replace(old_negamax_leaf, new_negamax_leaf)

    # 7. Negamax make move
    old_nega_make = """    for (int i = 0; i < n; i++) {
        uint16_t m = scored_moves[i].m;
        if (!native_make_move(b, m, &undo)) continue;

        moves_searched++;"""

    new_nega_make = """    for (int i = 0; i < n; i++) {
        uint16_t m = scored_moves[i].m;
        NativeBoard board_copy = *b;
        if (!native_make_move(b, m, &undo)) continue;
        if (g_use_neural_value) {
            update_nnue_acc_for_move(&board_copy, b, m, &undo, ply);
        }

        moves_searched++;"""
    assert old_nega_make in code, "old_nega_make not found"
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
    assert old_search_start in code, "old_search_start not found"
    code = code.replace(old_search_start, new_search_start)

    # 9. UCI Options output
    old_uci_opts = """            std::cout << "option name UseSEEInQuiescence type check default false" << std::endl;
            std::cout << "uciok" << std::endl;"""

    new_uci_opts = """            std::cout << "option name UseSEEInQuiescence type check default false" << std::endl;
            std::cout << "option name UseNeuralValue type check default false" << std::endl;
            std::cout << "option name NeuralValueModelPath type string default analysis/v0.61/models/janus_nnue_v2_small.jnnue" << std::endl;
            std::cout << "option name NeuralValueBlend type spin default 100 min 0 max 100" << std::endl;
            std::cout << "option name NeuralValueUseAVX2 type check default true" << std::endl;
            std::cout << "uciok" << std::endl;"""
    assert old_uci_opts in code, "old_uci_opts not found"
    code = code.replace(old_uci_opts, new_uci_opts)

    # 10. UCI setoption parsing
    old_setopt = """                } else if (opt_name == "UseSEEInQuiescence") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_see_in_quiescence = true;
                    } else {
                        g_use_see_in_quiescence = false;
                    }"""

    new_setopt = """                } else if (opt_name == "UseSEEInQuiescence") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_see_in_quiescence = true;
                    } else {
                        g_use_see_in_quiescence = false;
                    }
                } else if (opt_name == "UseNeuralValue") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_neural_value = true;
                        if (!g_nnue.is_loaded()) {
                            g_nnue.load_model(g_neural_value_model_path);
                        }
                    } else {
                        g_use_neural_value = false;
                    }
                } else if (opt_name == "NeuralValueModelPath" && !opt_val.empty()) {
                    g_neural_value_model_path = opt_val;
                    g_nnue.load_model(g_neural_value_model_path);
                } else if (opt_name == "NeuralValueBlend" && !opt_val.empty()) {
                    try { g_neural_value_blend = std::stoi(opt_val); } catch (...) {}
                } else if (opt_name == "NeuralValueUseAVX2") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_neural_use_avx2 = true;
                    } else {
                        g_neural_use_avx2 = false;
                    }
                    g_nnue.set_use_avx2(g_neural_use_avx2);"""
    assert old_setopt in code, "old_setopt not found"
    code = code.replace(old_setopt, new_setopt)

    with open(V61_CPP, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"Successfully generated {V61_CPP} ({len(code):,} characters, {len(code.splitlines())} lines).")


if __name__ == "__main__":
    generate_v061_cpp()
