#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.8
Build Candidate X13 and Stage Control Artifacts
"""

import os
import sys
import shutil
import hashlib
import subprocess
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
ENGINE_DIR = ROOT / "engine" / "classical_x"
CONTROL_DIR = ROOT / "analysis" / "phase1" / "p1.8" / "control"
CONTROL_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CPP = ENGINE_DIR / "janus_classical_x.cpp"
CONTROL_CPP = CONTROL_DIR / "janus_classical_x13.cpp"

VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=== PROJECT JANUS P1.8: BUILDING CANDIDATE X13 ===")
    print("[1] Reading current engine source...")
    with open(TARGET_CPP, "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Update UCI id name and author
    old_id = 'std::cout << "id name Janus Classical X (P1.7 Candidate X12)" << std::endl;\n            std::cout << "id author Project Janus Team" << std::endl;'
    new_id = 'std::cout << "id name Janus Classical X (P1.8 Candidate X13)" << std::endl;\n            std::cout << "id author Project Janus Developers" << std::endl;'
    assert old_id in src, f"Failed to find UCI ID string:\n{old_id}"
    src = src.replace(old_id, new_id)

    # 2. Update default variant variable
    old_var_init = 'static std::string g_search_variant = "X12";'
    new_var_init = 'static std::string g_search_variant = "X13";'
    assert old_var_init in src, "Failed to find g_search_variant initialization"
    src = src.replace(old_var_init, new_var_init)

    # 3. Update parallel TT usage checks to include X13
    old_tt_check = 'if (g_search_variant == "X11" || g_search_variant == "X12" || g_num_threads > 1)'
    new_tt_check = 'if (g_search_variant == "X11" || g_search_variant == "X12" || g_search_variant == "X13" || g_num_threads > 1)'
    assert old_tt_check in src, "Failed to find TT variant check"
    src = src.replace(old_tt_check, new_tt_check)

    # 4. Update UCI variant option string
    old_opt = 'std::cout << "option name UCI_Variant type combo default X12 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11 var X12" << std::endl;'
    new_opt = 'std::cout << "option name UCI_Variant type combo default X13 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11 var X12 var X13" << std::endl;'
    assert old_opt in src, "Failed to find UCI_Variant option string"
    src = src.replace(old_opt, new_opt)

    # 5. Add X13 handler in native_apply_search_variant
    x12_tail = """        g_use_lmp = true; // Safe Late Move Pruning
        g_lmp_mode = 1; // L1: Conservative Quadratic LMP
        g_lmp_max_depth = 4;
    }"""
    
    x13_addition = """        g_use_lmp = true; // Safe Late Move Pruning
        g_lmp_mode = 1; // L1: Conservative Quadratic LMP
        g_lmp_max_depth = 4;
    } else if (var == "X13") { // P1.8 Candidate: Full Co-Design (Packed 64B TT + E10 Eval + Thread-Local Pawn Hash + Safe LMP)
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
        g_use_pawn_hash = true; // Thread-local Pawn Hash Table
        g_dynamic_time_mgmt = true; // Dynamic Time Management
        g_use_lmp = true; // Safe Late Move Pruning
        g_lmp_mode = 1; // L1: Conservative Quadratic LMP
        g_lmp_max_depth = 4;
    }"""
    assert x12_tail in src, "Failed to find X12 tail in native_apply_search_variant"
    src = src.replace(x12_tail, x13_addition, 1)

    # 6. In native_init, call native_apply_search_variant("X13")
    old_init_call = 'native_apply_search_variant("X12");'
    new_init_call = 'native_apply_search_variant("X13");'
    assert old_init_call in src, "Failed to find native_init variant call"
    src = src.replace(old_init_call, new_init_call)

    # 7. Ensure PAWN_HASH_SIZE is 16384 (512 KB per thread, 100% L2 resident)
    old_hash_size = 'constexpr size_t PAWN_HASH_SIZE = 65536;'
    new_hash_size = 'constexpr size_t PAWN_HASH_SIZE = 16384; // 16K entries * 32B = 512 KB (100% L2 cache resident)'
    if old_hash_size in src:
        src = src.replace(old_hash_size, new_hash_size)

    print(f"[2] Writing updated engine to {TARGET_CPP} and {CONTROL_CPP}...")
    with open(TARGET_CPP, "w", encoding="utf-8") as f:
        f.write(src)
    with open(CONTROL_CPP, "w", encoding="utf-8") as f:
        f.write(src)

    print("[3] Compiling standalone executable and DLL...")
    build_bat = ENGINE_DIR / "build_x13_tmp.bat"
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
    exe_dst = CONTROL_DIR / "janus_classical_x13.exe"
    dll_dst = CONTROL_DIR / "janus_classical_x13.dll"
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

    print("\n[5] Verifying candidate X13 UCI identification...")
    p = subprocess.Popen([str(exe_dst)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("uci\nquit\n")
    print(out)
    assert "id name Janus Classical X (P1.8 Candidate X13)" in out, "Identification check failed!"
    assert "default X13" in out, "Default variant check failed!"
    print("=== CANDIDATE X13 BUILD & CONTROL STAGING SUCCESSFUL ===")

if __name__ == "__main__":
    main()

