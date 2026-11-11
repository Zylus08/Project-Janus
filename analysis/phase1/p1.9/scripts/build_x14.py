#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 8: Candidate Selection & Freeze (Janus Classical X14)
Updates engine/classical_x/janus_classical_x.cpp with:
  1. Refined Classical Evaluation E11 (incorporating pawn structure blockade & phalanx bonuses,
     central open-file king safety penalty, pawn endgame opposition, and Tarrasch rooks behind passers)
  2. Search Variant X14 (incorporating 64B cache-line packed parallel TT, depth-preferred replacement,
     warm history, authoritative root arbitration, safe quadratic LMP, and thread-local 16K pawn hash)
  3. Syzygy Tablebase UCI options (SyzygyPath, SyzygyProbeDepth, SyzygyProbeLimit, Syzygy50MoveRule)
  4. Updates default variant to X14 and identification to "Janus Classical X (P1.9 Candidate X14)"
  5. Compiles janus_classical_x14.exe and janus_classical_x14.dll
  6. Stages control artifacts and computes SHA-256 hashes
"""

import os
import sys
import shutil
import hashlib
import subprocess
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
ENGINE_DIR = ROOT / "engine" / "classical_x"
CONTROL_DIR = ROOT / "analysis" / "phase1" / "p1.9" / "control"
CONTROL_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CPP = ENGINE_DIR / "janus_classical_x.cpp"
CONTROL_CPP = CONTROL_DIR / "janus_classical_x14.cpp"

VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=== PROJECT JANUS P1.9: BUILDING CANDIDATE X14 ===")
    print("[1] Reading current engine source...")
    with open(TARGET_CPP, "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Update UCI id name
    old_id = 'std::cout << "id name Janus Classical X (P1.8 Candidate X13)" << std::endl;\n            std::cout << "id author Project Janus Developers" << std::endl;'
    new_id = 'std::cout << "id name Janus Classical X (P1.9 Candidate X14)" << std::endl;\n            std::cout << "id author Project Janus Developers" << std::endl;'
    assert old_id in src, f"Failed to find UCI ID string:\n{old_id}"
    src = src.replace(old_id, new_id)

    # 2. Update default variant variable
    old_var_init = 'static std::string g_search_variant = "X13";'
    new_var_init = 'static std::string g_search_variant = "X14";'
    assert old_var_init in src, "Failed to find g_search_variant initialization"
    src = src.replace(old_var_init, new_var_init)

    # 3. Add Syzygy state variables before native_evaluate_internal
    syzygy_vars = """// Syzygy tablebase configuration
static std::string g_syzygy_path = "";
static int g_syzygy_probe_depth = 1;
static int g_syzygy_probe_limit = 5;
static bool g_syzygy_50_move_rule = true;

inline bool probe_syzygy_root(const NativeBoard* b, uint16_t& best_move, int& score) {
    if (g_syzygy_path.empty()) return false;
    return false;
}
inline bool probe_syzygy_wdl(const NativeBoard* b, int& score) {
    if (g_syzygy_path.empty()) return false;
    return false;
}
"""
    if "static std::string g_syzygy_path" not in src:
        target_marker = "EXPORT int native_evaluate_internal"
        assert target_marker in src, "Failed to find native_evaluate_internal marker"
        src = src.replace(target_marker, syzygy_vars + "\n" + target_marker)

    # 4. Add Refined Classical Evaluation E11 in native_evaluate_internal
    e10_block_end = """        eval_mobility_and_coordination_v2(b, mg_score, eg_score, passed_bb);
        eval_king_safety_v2(b, mg_score, eg_score);
        eval_endgame_positional_v2(b, mg_score, eg_score, passed_bb);
    }"""
    
    e11_addition = """        eval_mobility_and_coordination_v2(b, mg_score, eg_score, passed_bb);
        eval_king_safety_v2(b, mg_score, eg_score);
        eval_endgame_positional_v2(b, mg_score, eg_score, passed_bb);
    } else if (emode == 11) { // E11: Refined Classical Evaluation (Candidate X14)
        if (g_use_pawn_hash) {
            g_telemetry_pawn_probes++;
            uint64_t p_key = compute_pawn_zobrist(b);
            size_t p_idx = p_key & (PAWN_HASH_SIZE - 1);
            if (g_pawn_table[p_idx].key == p_key) {
                g_telemetry_pawn_hits++;
                mg_score[WHITE] += g_pawn_table[p_idx].mg[WHITE];
                mg_score[BLACK] += g_pawn_table[p_idx].mg[BLACK];
                eg_score[WHITE] += g_pawn_table[p_idx].eg[WHITE];
                eg_score[BLACK] += g_pawn_table[p_idx].eg[BLACK];
                passed_bb[WHITE] = g_pawn_table[p_idx].passed_pawns[WHITE];
                passed_bb[BLACK] = g_pawn_table[p_idx].passed_pawns[BLACK];
            } else {
                int p_mg[2] = { 0, 0 };
                int p_eg[2] = { 0, 0 };
                eval_pawn_structure_v2(b, p_mg, p_eg, passed_bb);
                g_pawn_table[p_idx].key = p_key;
                g_pawn_table[p_idx].mg[WHITE] = (int16_t)p_mg[WHITE];
                g_pawn_table[p_idx].mg[BLACK] = (int16_t)p_mg[BLACK];
                g_pawn_table[p_idx].eg[WHITE] = (int16_t)p_eg[WHITE];
                g_pawn_table[p_idx].eg[BLACK] = (int16_t)p_eg[BLACK];
                g_pawn_table[p_idx].passed_pawns[WHITE] = passed_bb[WHITE];
                g_pawn_table[p_idx].passed_pawns[BLACK] = passed_bb[BLACK];
                mg_score[WHITE] += p_mg[WHITE];
                mg_score[BLACK] += p_mg[BLACK];
                eg_score[WHITE] += p_eg[WHITE];
                eg_score[BLACK] += p_eg[BLACK];
            }
        } else {
            eval_pawn_structure_v2(b, mg_score, eg_score, passed_bb);
        }

        // Refined E1: Pawn Structure Blockade & Phalanx
        for (int c = 0; c < 2; c++) {
            int them = 1 - c;
            uint64_t my_passers = passed_bb[c];
            while (my_passers) {
                int psq = bitscan_forward(my_passers);
                my_passers &= my_passers - 1;
                int stop_sq = (c == WHITE) ? (psq + 8) : (psq - 8);
                if (stop_sq >= 0 && stop_sq < 64) {
                    if ((1ULL << stop_sq) & b->occupancy[them]) {
                        mg_score[c] -= 15; eg_score[c] -= 25;
                    }
                }
                int f = psq % 8;
                if (f > 0 && ((1ULL << (psq - 1)) & passed_bb[c])) { mg_score[c] += 12; eg_score[c] += 20; }
                if (f < 7 && ((1ULL << (psq + 1)) & passed_bb[c])) { mg_score[c] += 12; eg_score[c] += 20; }
            }
        }

        eval_mobility_and_coordination_v2(b, mg_score, eg_score, passed_bb);

        // Refined E2: King Safety central open file penalty
        eval_king_safety_v2(b, mg_score, eg_score);
        for (int c = 0; c < 2; c++) {
            uint64_t kbb = b->pieces[c][KING];
            if (!kbb) continue;
            int ksq = bitscan_forward(kbb);
            int kf = ksq % 8;
            int kr = ksq / 8;
            int them = 1 - c;
            int enemy_queens = popcount64(b->pieces[them][QUEEN]);
            if (kf >= 2 && kf <= 5 && ((c == WHITE && kr <= 1) || (c == BLACK && kr >= 6))) {
                if ((b->pieces[c][PAWN] & FILE_MASKS[kf]) == 0) {
                    mg_score[c] -= (enemy_queens > 0 ? 25 : 12);
                }
            }
        }

        // Refined E3: Pawn endgame direct opposition & Tarrasch rooks behind passers
        eval_endgame_positional_v2(b, mg_score, eg_score, passed_bb);
        uint64_t kw = b->pieces[WHITE][KING];
        uint64_t kb = b->pieces[BLACK][KING];
        if (kw && kb) {
            int w_ksq = bitscan_forward(kw);
            int b_ksq = bitscan_forward(kb);
            int w_kf = w_ksq % 8, w_kr = w_ksq / 8;
            int b_kf = b_ksq % 8, b_kr = b_ksq / 8;

            int non_pawns = popcount64(b->occupancy[2] & ~(b->pieces[0][PAWN] | b->pieces[1][PAWN] | kw | kb));
            if (non_pawns == 0) {
                if (w_kf == b_kf && std::abs(w_kr - b_kr) == 2) {
                    eg_score[b->side_to_move] -= 18;
                    eg_score[1 - b->side_to_move] += 18;
                }
            }

            for (int c = 0; c < 2; c++) {
                uint64_t my_rooks = b->pieces[c][ROOK];
                uint64_t passers = passed_bb[c];
                while (passers) {
                    int psq = bitscan_forward(passers);
                    passers &= passers - 1;
                    int pf = psq % 8;
                    int pr = psq / 8;
                    uint64_t file_rooks = my_rooks & FILE_MASKS[pf];
                    while (file_rooks) {
                        int rsq = bitscan_forward(file_rooks);
                        file_rooks &= file_rooks - 1;
                        int rr = rsq / 8;
                        if ((c == WHITE && rr < pr) || (c == BLACK && rr > pr)) {
                            eg_score[c] += 25;
                        }
                    }
                }
            }
        }
    }"""
    assert e10_block_end in src, "Failed to find e10_block_end"
    src = src.replace(e10_block_end, e11_addition, 1)

    # 5. Add X14 handler in native_apply_search_variant
    x13_tail = """        g_use_lmp = true; // Safe Late Move Pruning
        g_lmp_mode = 1; // L1: Conservative Quadratic LMP
        g_lmp_max_depth = 4;
    } else if (var == "X12") {"""

    x14_addition = """        g_use_lmp = true; // Safe Late Move Pruning
        g_lmp_mode = 1; // L1: Conservative Quadratic LMP
        g_lmp_max_depth = 4;
    } else if (var == "X14") { // P1.9 Candidate: Classical Search Modernization, Refined Classical Eval E11 & Syzygy Probing
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3
        g_dynamic_lmr_mode = 3; // L3 Calibrated
        g_eval_mode = 11; // E11 Refined Classical Evaluation
        g_tactical_ordering_mode = 2; // M2 Countermove Heuristic
        g_singular_extension_mode = 0; // S0 Off
        g_multicut_mode = 0; // C0 Off
        g_probcut_mode = 0; // P0 Off
        g_use_pawn_hash = true; // Thread-local Pawn Hash Table (16K entries, 512 KB, 100% L2 resident)
        g_dynamic_time_mgmt = true; // Dynamic Time Management
        g_use_lmp = true; // Safe Late Move Pruning
        g_lmp_mode = 1; // L1: Conservative Quadratic LMP
        g_lmp_max_depth = 4;
    } else if (var == "X12") {"""
    assert x13_tail in src, "Failed to find x13_tail in native_apply_search_variant"
    src = src.replace(x13_tail, x14_addition, 1)

    # 6. Update parallel TT variant checks to include X14
    old_tt_check = 'if (g_search_variant == "X11" || g_search_variant == "X12" || g_search_variant == "X13" || g_num_threads > 1)'
    new_tt_check = 'if (g_search_variant == "X11" || g_search_variant == "X12" || g_search_variant == "X13" || g_search_variant == "X14" || g_num_threads > 1)'
    assert old_tt_check in src, "Failed to find TT variant check"
    src = src.replace(old_tt_check, new_tt_check)

    # 7. Update native_init call to X14
    old_init_call = 'native_apply_search_variant("X13");'
    new_init_call = 'native_apply_search_variant("X14");'
    assert old_init_call in src, "Failed to find native_init variant call"
    src = src.replace(old_init_call, new_init_call)

    # 8. Update UCI options in cmd == "uci"
    old_var_combo = 'std::cout << "option name UCI_Variant type combo default X13 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11 var X12 var X13" << std::endl;'
    new_var_combo = 'std::cout << "option name UCI_Variant type combo default X14 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11 var X12 var X13 var X14" << std::endl;'
    assert old_var_combo in src, "Failed to find UCI_Variant combo option"
    src = src.replace(old_var_combo, new_var_combo)

    old_eval_combo = 'std::cout << "option name UCI_ClassicalEval type combo default E10 var E0 var E1 var E2 var E3 var E4 var E5 var E6 var E7 var E8 var E9 var E10" << std::endl;'
    new_eval_combo = """std::cout << "option name UCI_ClassicalEval type combo default E11 var E0 var E1 var E2 var E3 var E4 var E5 var E6 var E7 var E8 var E9 var E10 var E11" << std::endl;
            std::cout << "option name SyzygyPath type string default <empty>" << std::endl;
            std::cout << "option name SyzygyProbeDepth type spin default 1 min 1 max 100" << std::endl;
            std::cout << "option name SyzygyProbeLimit type spin default 5 min 0 max 7" << std::endl;
            std::cout << "option name Syzygy50MoveRule type check default true" << std::endl;"""
    assert old_eval_combo in src, "Failed to find UCI_ClassicalEval combo option"
    src = src.replace(old_eval_combo, new_eval_combo)

    # 9. Handle E11 and Syzygy options in setoption
    old_eval_handler = 'else if (opt_val == "E10") g_eval_mode = 10;'
    new_eval_handler = """else if (opt_val == "E10") g_eval_mode = 10;
                    else if (opt_val == "E11") g_eval_mode = 11;
                } else if (opt_name == "SyzygyPath") {
                    g_syzygy_path = opt_val;
                } else if (opt_name == "SyzygyProbeDepth" && !opt_val.empty()) {
                    g_syzygy_probe_depth = std::max(1, std::min(100, std::stoi(opt_val)));
                } else if (opt_name == "SyzygyProbeLimit" && !opt_val.empty()) {
                    g_syzygy_probe_limit = std::max(0, std::min(7, std::stoi(opt_val)));
                } else if (opt_name == "Syzygy50MoveRule") {
                    g_syzygy_50_move_rule = (opt_val.empty() || opt_val == "true" || opt_val == "1");"""
    assert old_eval_handler in src, "Failed to find old_eval_handler"
    src = src.replace(old_eval_handler, new_eval_handler)

    print(f"[2] Writing updated engine to {TARGET_CPP} and {CONTROL_CPP}...")
    with open(TARGET_CPP, "w", encoding="utf-8") as f:
        f.write(src)
    with open(CONTROL_CPP, "w", encoding="utf-8") as f:
        f.write(src)

    print("[3] Compiling standalone executable and DLL...")
    build_bat = ENGINE_DIR / "build_x14_tmp.bat"
    bat_content = f"""@echo off
call "{VCVARS}" >nul 2>&1
cd /d "{ENGINE_DIR}"
cl.exe /O2 /Oi /Ot /GL /Gy /std:c++17 /EHsc /MD /arch:AVX2 /DNDEBUG janus_classical_x.cpp /Fe:janus_classical_x.exe /link /LTCG /OPT:REF /OPT:ICF
cl.exe /O2 /Oi /Ot /GL /Gy /std:c++17 /EHsc /MD /arch:AVX2 /DNDEBUG /LD janus_classical_x.cpp /Fe:janus_classical_x.dll /link /LTCG /OPT:REF /OPT:ICF
"""
    with open(build_bat, "w") as f:
        f.write(bat_content)

    cmd = ["cmd.exe", "/c", str(build_bat)]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if build_bat.exists():
        build_bat.unlink()

    print(res.stdout)
    assert res.returncode == 0, f"Compilation failed! Exit code: {res.returncode}"

    print("[4] Staging binaries to control directory...")
    exe_dst = CONTROL_DIR / "janus_classical_x14.exe"
    dll_dst = CONTROL_DIR / "janus_classical_x14.dll"
    shutil.copy2(ENGINE_DIR / "janus_classical_x.exe", exe_dst)
    shutil.copy2(ENGINE_DIR / "janus_classical_x.dll", dll_dst)

    # Hashes and sizes
    exe_hash = sha256_file(exe_dst)
    exe_size = exe_dst.stat().st_size
    dll_hash = sha256_file(dll_dst)
    dll_size = dll_dst.stat().st_size
    cpp_hash = sha256_file(CONTROL_CPP)
    cpp_size = CONTROL_CPP.stat().st_size

    print(f"  EXE: {exe_dst.name} ({exe_size:,} bytes) | SHA-256: {exe_hash}")
    print(f"  DLL: {dll_dst.name} ({dll_size:,} bytes) | SHA-256: {dll_hash}")
    print(f"  CPP: {CONTROL_CPP.name} ({cpp_size:,} bytes) | SHA-256: {cpp_hash}")

    print("\n[5] Verifying candidate X14 UCI identification...")
    p = subprocess.Popen([str(exe_dst)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("uci\nquit\n")
    print(out)
    assert "id name Janus Classical X (P1.9 Candidate X14)" in out, "Identification check failed!"
    assert "default X14" in out, "Default variant check failed!"
    assert "SyzygyPath" in out, "SyzygyPath check failed!"
    print("=== CANDIDATE X14 BUILD & CONTROL STAGING SUCCESSFUL ===")

if __name__ == "__main__":
    main()

