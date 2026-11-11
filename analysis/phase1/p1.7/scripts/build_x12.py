#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Build Candidate X12 and Stage Control Artifacts
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
ENGINE_DIR = ROOT / "engine" / "classical_x"
CONTROL_DIR = ROOT / "analysis" / "phase1" / "p1.7" / "control"
CONTROL_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_W4 = ROOT / "analysis" / "phase1" / "p1.7" / "tests" / "engine_w4.cpp"
TARGET_CPP = ENGINE_DIR / "janus_classical_x.cpp"
CONTROL_CPP = CONTROL_DIR / "janus_classical_x12.cpp"

VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

def main():
    print("[1] Reading verified W4 prototype source...")
    with open(SOURCE_W4, "r", encoding="utf-8") as f:
        src = f.read()

    # Update UCI id name
    old_id = 'std::cout << "id name Janus Classical X (P1.6 Candidate X11)" << std::endl;'
    new_id = 'std::cout << "id name Janus Classical X (P1.7 Candidate X12)" << std::endl;'
    assert old_id in src, "Failed to find UCI ID string"
    src = src.replace(old_id, new_id)

    # Update default variant variable
    old_var_init = 'static std::string g_search_variant = "X7";'
    new_var_init = 'static std::string g_search_variant = "X12";'
    assert old_var_init in src, "Failed to find g_search_variant initialization"
    src = src.replace(old_var_init, new_var_init)

    # Update parallel TT usage checks to include X12
    old_tt_check = 'if (g_search_variant == "X11" || g_num_threads > 1)'
    new_tt_check = 'if (g_search_variant == "X11" || g_search_variant == "X12" || g_num_threads > 1)'
    assert old_tt_check in src, "Failed to find TT variant check"
    src = src.replace(old_tt_check, new_tt_check)

    # Update UCI variant option string
    old_opt = 'std::cout << "option name UCI_Variant type combo default X11 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11" << std::endl;'
    new_opt = 'std::cout << "option name UCI_Variant type combo default X12 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11 var X12" << std::endl;'
    assert old_opt in src, "Failed to find UCI_Variant option string"
    src = src.replace(old_opt, new_opt)

    # Add X12 handler in native_apply_search_variant
    x11_block = """    } else if (var == "X11") { // P1.6 Candidate: Lazy SMP Multithreading & Safe Late Move Pruning
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3
        g_dynamic_lmr_mode = 3; // L3 Calibrated
        g_eval_mode = 10; // E10 Enhanced Classical Evaluation
        g_tactical_ordering_mode = 2; // M2 Countermove Heuristic
        g_singular_extension_mode = 0; // S0 Off
        g_multicut_mode = 0; // C0 Off
        g_probcut_mode = 0; // P0 Off
        g_use_pawn_hash = true; // 64K entry Pawn Hash Table
        g_dynamic_time_mgmt = true; // Dynamic Time Management
        g_use_lmp = true; // Safe Late Move Pruning
        g_lmp_mode = 1; // L1: Conservative Quadratic LMP
        g_lmp_max_depth = 4;
    }"""

    x12_block = """    } else if (var == "X11") { // P1.6 Candidate: Lazy SMP Multithreading & Safe Late Move Pruning
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3
        g_dynamic_lmr_mode = 3; // L3 Calibrated
        g_eval_mode = 10; // E10 Enhanced Classical Evaluation
        g_tactical_ordering_mode = 2; // M2 Countermove Heuristic
        g_singular_extension_mode = 0; // S0 Off
        g_multicut_mode = 0; // C0 Off
        g_probcut_mode = 0; // P0 Off
        g_use_pawn_hash = true; // 64K entry Pawn Hash Table
        g_dynamic_time_mgmt = true; // Dynamic Time Management
        g_use_lmp = true; // Safe Late Move Pruning
        g_lmp_mode = 1; // L1: Conservative Quadratic LMP
        g_lmp_max_depth = 4;
    } else if (var == "X12") { // P1.7 Candidate: 64B Packed Shared TT, Smart Eviction, Warm History & Root Arbitration
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3
        g_dynamic_lmr_mode = 3; // L3 Calibrated
        g_eval_mode = 10; // E10 Enhanced Classical Evaluation
        g_tactical_ordering_mode = 2; // M2 Countermove Heuristic
        g_singular_extension_mode = 0; // S0 Off
        g_multicut_mode = 0; // C0 Off
        g_probcut_mode = 0; // P0 Off
        g_use_pawn_hash = true; // 64K entry Pawn Hash Table
        g_dynamic_time_mgmt = true; // Dynamic Time Management
        g_use_lmp = true; // Safe Late Move Pruning
        g_lmp_mode = 1; // L1: Conservative Quadratic LMP
        g_lmp_max_depth = 4;
    }"""
    assert x11_block in src, "Failed to find X11 block in native_apply_search_variant"
    src = src.replace(x11_block, x12_block)

    # In native_init, call native_apply_search_variant("X12")
    old_init = """EXPORT int native_init() {
    init_attacks();
    std::memset(g_tt, 0, sizeof(g_tt));
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    std::memset(g_history_table, 0, sizeof(g_history_table));
    g_game_history_len = 0;
    return 1;
}"""
    new_init = """EXPORT int native_init() {
    init_attacks();
    std::memset(g_tt, 0, sizeof(g_tt));
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    std::memset(g_history_table, 0, sizeof(g_history_table));
    g_game_history_len = 0;
    native_apply_search_variant("X12");
    return 1;
}"""
    assert old_init in src, "Failed to find native_init"
    src = src.replace(old_init, new_init)

    print(f"[2] Writing updated engine to {TARGET_CPP} and {CONTROL_CPP}...")
    with open(TARGET_CPP, "w", encoding="utf-8") as f:
        f.write(src)
    with open(CONTROL_CPP, "w", encoding="utf-8") as f:
        f.write(src)

    print("[3] Compiling standalone executable and DLL...")
    build_bat = ENGINE_DIR / "build_x12_tmp.bat"
    bat_content = f"""@echo off
call "{VCVARS}" >nul 2>&1
cd /d "{ENGINE_DIR}"
cl.exe /O2 /Oi /Ot /GL /Gy /std:c++17 /EHsc /MD /arch:AVX2 /DNDEBUG janus_classical_x.cpp /Fe:janus_classical_x.exe /link /LTCG /OPT:REF /OPT:ICF
cl.exe /O2 /Oi /Ot /GL /Gy /std:c++17 /EHsc /MD /arch:AVX2 /DNDEBUG /LD janus_classical_x.cpp /Fe:janus_classical_x.dll /link /LTCG /OPT:REF /OPT:ICF
"""
    with open(build_bat, "w") as f:
        f.write(bat_content)

    res = subprocess.run(["cmd.exe", "/c", str(build_bat)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if build_bat.exists():
        build_bat.unlink()

    print(res.stdout)
    assert res.returncode == 0, "Compilation failed!"

    print("[4] Staging binaries to control directory...")
    shutil.copy2(ENGINE_DIR / "janus_classical_x.exe", CONTROL_DIR / "janus_classical_x12.exe")
    shutil.copy2(ENGINE_DIR / "janus_classical_x.dll", CONTROL_DIR / "janus_classical_x12.dll")

    print("[5] Verifying candidate X12 UCI identification...")
    p = subprocess.Popen([str(CONTROL_DIR / "janus_classical_x12.exe")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("uci\nquit\n")
    print(out)
    assert "Janus Classical X (P1.7 Candidate X12)" in out, "Identification check failed!"
    print("=== CANDIDATE X12 BUILD & CONTROL STAGING SUCCESSFUL ===")

if __name__ == "__main__":
    main()
