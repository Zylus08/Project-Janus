#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 2: Handcrafted Evaluation Failure Repair & Controlled Ablations
Compiles ablation engine and evaluates E0, E1, E2, E3, E4 across 120 DEV positions.
"""

import sys
import os
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
TEST_DIR = ROOT / "analysis" / "phase1" / "p1.9" / "tests"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.9" / "raw" / "eval_ablation_matrix_raw.json"
CORPUS_PATH = ROOT / "analysis" / "phase1" / "p1.9" / "corpus" / "generalized_failure_atlas_240.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

ENGINE_SRC = ROOT / "engine" / "classical_x" / "janus_classical_x.cpp"
ABLATION_SRC = TEST_DIR / "engine_eval_ablation.cpp"
ABLATION_EXE = TEST_DIR / "engine_eval_ablation.exe"

VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

def build_ablation_engine():
    print("[1] Authoring ablation engine source...")
    with open(ENGINE_SRC, "r", encoding="utf-8") as f:
        src = f.read()

    # Expand UCI_ClassicalEval options
    old_uci_eval = 'option name UCI_ClassicalEval type combo default E10 var E0 var E1 var E2 var E3 var E4 var E5 var E6 var E7 var E8 var E9 var E10'
    new_uci_eval = 'option name UCI_ClassicalEval type combo default E10 var E0 var E1 var E2 var E3 var E4 var E5 var E6 var E7 var E8 var E9 var E10 var E11 var E12 var E13 var E14'
    assert old_uci_eval in src, "Failed to find old_uci_eval"
    src = src.replace(old_uci_eval, new_uci_eval)

    # Expand UCI setoption handler for E11-E14
    old_opt_handler = 'else if (opt_val == "E10") g_eval_mode = 10;'
    new_opt_handler = """else if (opt_val == "E10") g_eval_mode = 10;
                    else if (opt_val == "E11") g_eval_mode = 11;
                    else if (opt_val == "E12") g_eval_mode = 12;
                    else if (opt_val == "E13") g_eval_mode = 13;
                    else if (opt_val == "E14") g_eval_mode = 14;"""
    assert old_opt_handler in src, "Failed to find old_opt_handler"
    src = src.replace(old_opt_handler, new_opt_handler)

    # Add E11-E14 logic in native_evaluate_internal
    old_eval_call = """        eval_mobility_and_coordination_v2(b, mg_score, eg_score, passed_bb);
        eval_king_safety_v2(b, mg_score, eg_score);
        eval_endgame_positional_v2(b, mg_score, eg_score, passed_bb);
    }"""

    new_eval_call = """        eval_mobility_and_coordination_v2(b, mg_score, eg_score, passed_bb);
        eval_king_safety_v2(b, mg_score, eg_score);
        eval_endgame_positional_v2(b, mg_score, eg_score, passed_bb);
    } else if (emode >= 11 && emode <= 14) { // E11=E1 (Pawn), E12=E2 (King), E13=E3 (Endgame), E14=E4 (Combined)
        bool fix_pawn = (emode == 11 || emode == 14);
        bool fix_king = (emode == 12 || emode == 14);
        bool fix_endgame = (emode == 13 || emode == 14);

        if (g_use_pawn_hash && !fix_pawn) {
            uint64_t p_key = compute_pawn_zobrist(b);
            size_t p_idx = p_key & (PAWN_HASH_SIZE - 1);
            if (g_pawn_table[p_idx].key == p_key) {
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

        // --- E1: Pawn Structure Refinements ---
        if (fix_pawn) {
            for (int c = 0; c < 2; c++) {
                int them = 1 - c;
                uint64_t my_passers = passed_bb[c];
                while (my_passers) {
                    int psq = bitscan_forward(my_passers);
                    my_passers &= my_passers - 1;
                    int stop_sq = (c == WHITE) ? (psq + 8) : (psq - 8);
                    if (stop_sq >= 0 && stop_sq < 64) {
                        // Penalize blockaded passed pawns
                        if ((1ULL << stop_sq) & b->occupancy[them]) {
                            mg_score[c] -= 15; eg_score[c] -= 25;
                        }
                    }
                    // Phalanx passed pawn bonus (adjacent file, same rank)
                    int f = psq % 8;
                    int r = psq / 8;
                    if (f > 0 && ((1ULL << (psq - 1)) & passed_bb[c])) { mg_score[c] += 12; eg_score[c] += 20; }
                    if (f < 7 && ((1ULL << (psq + 1)) & passed_bb[c])) { mg_score[c] += 12; eg_score[c] += 20; }
                }
            }
        }

        eval_mobility_and_coordination_v2(b, mg_score, eg_score, passed_bb);

        // --- E2: King Safety Refinements ---
        eval_king_safety_v2(b, mg_score, eg_score);
        if (fix_king) {
            for (int c = 0; c < 2; c++) {
                uint64_t kbb = b->pieces[c][KING];
                if (!kbb) continue;
                int ksq = bitscan_forward(kbb);
                int kf = ksq % 8;
                int kr = ksq / 8;
                int them = 1 - c;
                int enemy_queens = popcount64(b->pieces[them][QUEEN]);

                // King stranded on central files (c, d, e, f)
                if (kf >= 2 && kf <= 5 && ((c == WHITE && kr <= 1) || (c == BLACK && kr >= 6))) {
                    // Check if open or semi-open file
                    if ((b->pieces[c][PAWN] & FILE_MASKS[kf]) == 0) {
                        mg_score[c] -= (enemy_queens > 0 ? 25 : 12);
                    }
                }
            }
        }

        // --- E3: Endgame Refinements ---
        eval_endgame_positional_v2(b, mg_score, eg_score, passed_bb);
        if (fix_endgame) {
            uint64_t kw = b->pieces[WHITE][KING];
            uint64_t kb = b->pieces[BLACK][KING];
            if (kw && kb) {
                int w_ksq = bitscan_forward(kw);
                int b_ksq = bitscan_forward(kb);
                int w_kf = w_ksq % 8, w_kr = w_ksq / 8;
                int b_kf = b_ksq % 8, b_kr = b_ksq / 8;

                // Direct opposition in pure pawn endgames
                int non_pawns = popcount64(b->occupancy[2] & ~(b->pieces[0][PAWN] | b->pieces[1][PAWN] | kw | kb));
                if (non_pawns == 0) {
                    if (w_kf == b_kf && std::abs(w_kr - b_kr) == 2) {
                        // The player NOT to move holds opposition
                        eg_score[b->side_to_move] -= 18;
                        eg_score[1 - b->side_to_move] += 18;
                    }
                }

                // Tarrasch Rook behind passed pawn
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
                                eg_score[c] += 25; // Friendly rook behind passer
                            }
                        }
                    }
                }
            }
        }
    }"""

    assert old_eval_call in src, "Failed to find old_eval_call in janus_classical_x.cpp"
    src = src.replace(old_eval_call, new_eval_call)

    with open(ABLATION_SRC, "w", encoding="utf-8") as f:
        f.write(src)

    print("[2] Compiling ablation engine binary...")
    build_bat = TEST_DIR / "build_ablation_tmp.bat"
    bat_content = f"""@echo off
call "{VCVARS}" >nul 2>&1
cd /d "{TEST_DIR}"
cl.exe /O2 /Oi /Ot /GL /Gy /std:c++17 /EHsc /MD /arch:AVX2 /DNDEBUG engine_eval_ablation.cpp /Fe:engine_eval_ablation.exe /link /LTCG /OPT:REF /OPT:ICF
"""
    with open(build_bat, "w") as f:
        f.write(bat_content)

    res = subprocess.run(["cmd.exe", "/c", str(build_bat)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if build_bat.exists():
        build_bat.unlink()

    print(res.stdout)
    assert res.returncode == 0, f"Ablation build failed with code {res.returncode}"
    print(f"Successfully compiled {ABLATION_EXE}")

def run_eval_ablation(exe, fen, emode_name, movetime_ms=350):
    cmds = [
        "uci",
        "setoption name Threads value 4",
        f"setoption name UCI_ClassicalEval value {emode_name}",
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ]
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=15)
    dur = time.perf_counter() - t0

    depth = 0
    nodes = 0
    bestmove = None
    score_cp = 0

    for line in out.splitlines():
        if line.startswith("info depth"):
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            m_s = re.search(r'score cp (-?\d+)', line)
            m_m = re.search(r'score mate (-?\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_n: nodes = int(m_n.group(1))
            if m_s: score_cp = int(m_s.group(1))
            elif m_m: score_cp = 10000 if int(m_m.group(1)) > 0 else -10000
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    nps = int(nodes / dur) if dur > 0 else 0
    return {
        "depth": depth,
        "nodes": nodes,
        "score_cp": score_cp,
        "bestmove": bestmove,
        "nps": nps,
        "elapsed_s": round(dur, 4)
    }

def main():
    print("=== PROJECT JANUS P1.9: PHASE 2 EVALUATION ABLATIONS ===")
    build_ablation_engine()

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    dev_positions = corpus["dev_positions"]
    print(f"\nLoaded {len(dev_positions)} DEV positions for controlled ablations.")

    modes = [
        {"id": "E0",  "emode": "E10", "desc": "Frozen X13 baseline (E10 as-is)"},
        {"id": "E1",  "emode": "E11", "desc": "Pawn structure fixes (blockades, open-file backward, phalanx)"},
        {"id": "E2",  "emode": "E12", "desc": "King safety fixes (stranded central king on open files)"},
        {"id": "E3",  "emode": "E13", "desc": "Endgame refinements (opposition, Tarrasch rooks)"},
        {"id": "E4",  "emode": "E14", "desc": "Combined improvements (E1 + E2 + E3 = Refined E10 / E11)"}
    ]

    results = {}
    for m in modes:
        mid = m["id"]
        emode = m["emode"]
        print(f"\nEvaluating {mid} ({m['desc']})...")
        t0 = time.time()
        total_depth = 0
        total_nodes = 0
        total_time = 0.0
        solved_count = 0
        mode_runs = {}

        for pos in dev_positions:
            pid = pos["id"]
            fen = pos["fen"]
            sol = pos.get("solution", None)

            run_res = run_eval_ablation(ABLATION_EXE, fen, emode, movetime_ms=300)
            mode_runs[pid] = run_res

            total_depth += run_res["depth"]
            total_nodes += run_res["nodes"]
            total_time += run_res["elapsed_s"]

            if sol and run_res["bestmove"] == sol:
                solved_count += 1

        avg_depth = round(total_depth / len(dev_positions), 2)
        avg_nps = int(total_nodes / total_time) if total_time > 0 else 0

        results[mid] = {
            "id": mid,
            "emode": emode,
            "desc": m["desc"],
            "avg_depth": avg_depth,
            "avg_nps": avg_nps,
            "tactics_solved": solved_count,
            "elapsed_total": round(time.time() - t0, 2),
            "positions": mode_runs
        }
        print(f"  -> Depth: {avg_depth} plies | NPS: {avg_nps:,} | Tactics Solved: {solved_count} in {results[mid]['elapsed_total']}s")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved ablation matrix to {RAW_OUT}")

if __name__ == "__main__":
    main()

