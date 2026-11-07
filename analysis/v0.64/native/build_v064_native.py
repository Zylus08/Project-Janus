#!/usr/bin/env python3
"""Project Janus v0.64 - Native Build & Compilation Pipeline for NNUE-V3.

Generates janus_native.cpp for v0.64 with NNUE-V3, SEF integration,
and Phase-Tapered Adaptive Blending. Compiles standalone UCI engine and shared DLL.
"""

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
V56_CPP = ROOT / "analysis" / "v0.56" / "native" / "janus_native.cpp"
V64_DIR = ROOT / "analysis" / "v0.64" / "native"
V64_CPP = V64_DIR / "janus_native.cpp"
VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"


def generate_v064_cpp():
    print(f"Generating {V64_CPP.name} from C1 Baseline...")
    with open(V56_CPP, "r", encoding="utf-8") as f:
        code = f.read().replace("\r\n", "\n")

    # 1. Include nnue_v3.h and sef_features.h at top
    code = "#include \"nnue_v3.h\"\n#include \"sef_features.h\"\n" + code

    # 2. Add NNUE-V3 State and Helpers right before quiescence
    nnue_v3_helpers = """
// ============================================================================
// NNUE-V3 Neural Value Evaluation State & Bridge (Project Janus v0.64)
// ============================================================================

static bool g_use_neural_value = false;
static std::string g_neural_value_model_path = "analysis/v0.64/models/janus_nnue_v3.jnnue";
static int g_neural_value_blend = 50; // 50/50 base blend
static bool g_neural_value_adaptive = true; // Phase-Tapered Adaptive Blending
static bool g_neural_use_avx2 = true;
static janus::nnue_v3::NNUEEvaluatorV3 g_nnue;
static janus::nnue_v3::AccumulatorV3 g_accum_stack[MAX_SEARCH_PLY + 64];

EXPORT void native_set_neural_value_options(bool enabled, const char* model_path, int blend, bool use_avx2, bool adaptive = true) {
    g_use_neural_value = enabled;
    g_neural_value_blend = std::clamp(blend, 0, 100);
    g_neural_use_avx2 = use_avx2;
    g_neural_value_adaptive = adaptive;
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

static inline janus::nnue::BoardBitboards make_bitboards(const NativeBoard* b) {
    janus::nnue::BoardBitboards bb;
    bb.w_pawns = b->pieces[0][0]; bb.b_pawns = b->pieces[1][0];
    bb.w_knights = b->pieces[0][1]; bb.b_knights = b->pieces[1][1];
    bb.w_bishops = b->pieces[0][2]; bb.b_bishops = b->pieces[1][2];
    bb.w_rooks = b->pieces[0][3]; bb.b_rooks = b->pieces[1][3];
    bb.w_queens = b->pieces[0][4]; bb.b_queens = b->pieces[1][4];
    bb.w_king_sq = (b->pieces[0][5] != 0ULL) ? TZCNT64(b->pieces[0][5]) : 4;
    bb.b_king_sq = (b->pieces[1][5] != 0ULL) ? TZCNT64(b->pieces[1][5]) : 60;
    bb.white_to_move = (b->side_to_move == 0);
    return bb;
}

EXPORT int native_evaluate_neural(const NativeBoard* b) {
    if (!g_nnue.is_loaded()) {
        g_nnue.load_model(g_neural_value_model_path);
    }
    if (!g_nnue.is_loaded()) return native_evaluate(b);
    janus::nnue_v3::AccumulatorV3 acc;
    g_nnue.full_refresh(b->pieces, b->side_to_move, &acc);
    janus::nnue::BoardBitboards bb = make_bitboards(b);
    return g_nnue.evaluate(&acc, bb, b->side_to_move);
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
    janus::nnue_v3::AccumulatorV3* next_acc = &g_accum_stack[ply + 1];
    const janus::nnue_v3::AccumulatorV3* prev_acc = &g_accum_stack[ply];

    if (flag != 0) {
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

    quiescence_marker = "static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted) {"
    quiescence_replacement = "static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted, int ply = 0) {"
    assert quiescence_marker in code, "quiescence_marker not found"
    code = code.replace(quiescence_marker, nnue_v3_helpers + "\n" + quiescence_replacement)

    # 3. Quiescence stand_pat blending
    old_stand_pat = "    int stand_pat = native_evaluate(b);"
    new_stand_pat = """    int stand_pat = 0;
    if (g_use_neural_value && g_nnue.is_loaded()) {
        janus::nnue::BoardBitboards b_bits = make_bitboards(b);
        int nnue_score = g_nnue.evaluate(&g_accum_stack[ply], b_bits, b->side_to_move);
        int classical_score = native_evaluate(b);
        if (g_neural_value_adaptive) {
            int phase = 1 * (POPCOUNT64(b->pieces[0][1] | b->pieces[1][1]) +
                             POPCOUNT64(b->pieces[0][2] | b->pieces[1][2])) +
                        2 * (POPCOUNT64(b->pieces[0][3] | b->pieces[1][3])) +
                        4 * (POPCOUNT64(b->pieces[0][4] | b->pieces[1][4]));
            phase = std::clamp(phase, 0, 24);
            int effective_blend = (g_neural_value_blend * phase) / 24;
            stand_pat = (nnue_score * effective_blend + classical_score * (100 - effective_blend)) / 100;
        } else {
            stand_pat = (nnue_score * g_neural_value_blend + classical_score * (100 - g_neural_value_blend)) / 100;
        }
    } else {
        stand_pat = native_evaluate(b);
    }"""
    assert old_stand_pat in code, "old_stand_pat not found"
    code = code.replace(old_stand_pat, new_stand_pat)

    # 4. Quiescence recursive make move
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

    # 5. Negamax leaf call to quiescence
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
            std::cout << "option name NeuralValueModelPath type string default analysis/v0.64/models/janus_nnue_v3.jnnue" << std::endl;
            std::cout << "option name NeuralValueBlend type spin default 50 min 0 max 100" << std::endl;
            std::cout << "option name NeuralValueAdaptiveBlend type check default true" << std::endl;
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
                } else if (opt_name == "NeuralValueAdaptiveBlend") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_neural_value_adaptive = true;
                    } else {
                        g_neural_value_adaptive = false;
                    }
                } else if (opt_name == "NeuralValueUseAVX2") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_neural_use_avx2 = true;
                    } else {
                        g_neural_use_avx2 = false;
                    }
                    g_nnue.set_use_avx2(g_neural_use_avx2);"""
    assert old_setopt in code, "old_setopt not found"
    code = code.replace(old_setopt, new_setopt)

    with open(V64_CPP, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"Successfully generated {V64_CPP} ({len(code):,} characters, {len(code.splitlines())} lines).")


def run_msvc_cmd(cmd: str):
    full_cmd = f'cmd.exe /c ""{VCVARS}" && {cmd}""'
    print(f"\n[BUILD] Running: {cmd}")
    res = subprocess.run(
        full_cmd,
        cwd=str(V64_DIR),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print("[BUILD] STDOUT:\n", res.stdout)
        print("[BUILD] STDERR:\n", res.stderr)
        raise RuntimeError(f"Build command failed with code {res.returncode}")
    else:
        print(f"[BUILD] Success! {res.stdout.strip().splitlines()[-1] if res.stdout.strip() else 'OK'}")


def main():
    print("=" * 70)
    print("PROJECT JANUS v0.64 — NATIVE C++17 / AVX2 BUILD PIPELINE")
    print("=" * 70)

    # 1. Generate janus_native.cpp
    generate_v064_cpp()

    # 2. Compile test_nnue_v3_native.exe
    run_msvc_cmd("cl /O2 /W4 /std:c++17 /EHsc /arch:AVX2 test_nnue_v3_native.cpp nnue_v3.cpp /Fe:test_nnue_v3_native.exe")

    # 3. Compile janus_native.dll (Shared DLL)
    run_msvc_cmd("cl /O2 /W4 /std:c++17 /EHsc /arch:AVX2 /LD janus_native.cpp nnue_v3.cpp /Fe:janus_native.dll")

    # 4. Compile janus_native_engine.exe (Standalone UCI Engine)
    run_msvc_cmd("cl /O2 /W4 /std:c++17 /EHsc /arch:AVX2 janus_native.cpp nnue_v3.cpp /Fe:janus_native_engine.exe")

    print("\nAll v0.64 native binaries built successfully!")


if __name__ == "__main__":
    main()
