#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.6
Build script for Janus Classical X11 Candidate:
Integrates Lazy SMP Multithreading, Thread-Safe Transposition Table, and Safe Late Move Pruning.
"""

import sys
import subprocess
import shutil
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
BASE_CPP = ROOT / "engine" / "classical_x" / "janus_classical_x.cpp"
TARGET_DIR = ROOT / "analysis" / "phase1" / "p1.6" / "control"
TARGET_CPP = TARGET_DIR / "janus_classical_x11.cpp"
TARGET_EXE = TARGET_DIR / "janus_classical_x11.exe"
TARGET_DLL = TARGET_DIR / "janus_classical_x11.dll"
VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

def generate_x11_source():
    with open(BASE_CPP, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Add headers
    old_headers = '#include <vector>'
    new_headers = '#include <vector>\n#include <thread>\n#include <atomic>\n#include <immintrin.h>'
    assert old_headers in code, "Could not find headers"
    code = code.replace(old_headers, new_headers, 1)

    # 2. Add ParallelTranspositionTable after score_from_tt
    target_score_from = '''inline int score_from_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_SEARCH_PLY) return score - ply;
    if (score <= -MATE_SCORE + MAX_SEARCH_PLY) return score + ply;
    return score;
}'''

    parallel_tt_code = '''inline int score_from_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_SEARCH_PLY) return score - ply;
    if (score <= -MATE_SCORE + MAX_SEARCH_PLY) return score + ply;
    return score;
}

struct alignas(64) TTCluster {
    std::atomic_flag lock;
    TTEntry entries[4];
};

constexpr size_t NUM_TT_CLUSTERS = 262144; // 1,048,576 entries (32 MB)

class ParallelTranspositionTable {
public:
    TTCluster* clusters{nullptr};
    std::atomic<uint8_t> current_age{0};

    ParallelTranspositionTable() {
        clusters = new TTCluster[NUM_TT_CLUSTERS];
        clear();
    }

    ~ParallelTranspositionTable() {
        delete[] clusters;
    }

    void clear() {
        if (!clusters) return;
        for (size_t i = 0; i < NUM_TT_CLUSTERS; ++i) {
            clusters[i].lock.clear();
            std::memset(clusters[i].entries, 0, sizeof(clusters[i].entries));
        }
    }

    bool probe(uint64_t key, int depth, int ply, int alpha, int beta, int& out_score, uint16_t& out_move, bool allow_cutoff) {
        size_t c_idx = (key ^ (key >> 32)) % NUM_TT_CLUSTERS;
        TTCluster& c = clusters[c_idx];

        while (c.lock.test_and_set(std::memory_order_acquire)) {
            _mm_pause();
        }

        bool hit = false;
        out_move = 0;

        for (int i = 0; i < 4; ++i) {
            if (c.entries[i].key == key) {
                out_move = c.entries[i].best_move;
                if (allow_cutoff && c.entries[i].depth >= depth) {
                    int tt_score = score_from_tt(c.entries[i].score, ply);
                    uint8_t flag = c.entries[i].flag;
                    if (flag == TT_EXACT) {
                        out_score = tt_score;
                        hit = true;
                    } else if (flag == TT_LOWER && tt_score >= beta) {
                        out_score = tt_score;
                        hit = true;
                    } else if (flag == TT_UPPER && tt_score <= alpha) {
                        out_score = tt_score;
                        hit = true;
                    }
                }
                break;
            }
        }

        c.lock.clear(std::memory_order_release);
        return hit;
    }

    void store(uint64_t key, int score, int8_t depth, uint8_t flag, int ply, uint16_t best_move) {
        size_t c_idx = (key ^ (key >> 32)) % NUM_TT_CLUSTERS;
        TTCluster& c = clusters[c_idx];
        uint8_t age = current_age.load(std::memory_order_relaxed);

        while (c.lock.test_and_set(std::memory_order_acquire)) {
            _mm_pause();
        }

        int replace_idx = -1;
        int lowest_depth = 999;
        int oldest_age_diff = -1;

        for (int i = 0; i < 4; ++i) {
            if (c.entries[i].key == key) {
                replace_idx = i;
                break;
            }
            if (c.entries[i].key == 0) {
                replace_idx = i;
                break;
            }
            int age_diff = (int)age - (int)c.entries[i].age;
            if (age_diff > oldest_age_diff) {
                oldest_age_diff = age_diff;
                replace_idx = i;
            } else if (age_diff == oldest_age_diff && c.entries[i].depth < lowest_depth) {
                lowest_depth = c.entries[i].depth;
                replace_idx = i;
            }
        }

        if (replace_idx >= 0) {
            c.entries[replace_idx].key = key;
            c.entries[replace_idx].score = score_to_tt(score, ply);
            c.entries[replace_idx].depth = depth;
            c.entries[replace_idx].flag = flag;
            c.entries[replace_idx].age = age;
            if (best_move != 0 || c.entries[replace_idx].best_move == 0) {
                c.entries[replace_idx].best_move = best_move;
            }
        }

        c.lock.clear(std::memory_order_release);
    }
};

static ParallelTranspositionTable g_parallel_tt;'''
    assert target_score_from in code, "Could not find score_from_tt"
    code = code.replace(target_score_from, parallel_tt_code, 1)

    # 3. Thread-local game history and PV table
    old_hist_pv = '''static uint64_t g_game_history[MAX_GAME_HISTORY];
static int g_game_history_len = 0;

// PV Table (Phase C)
static uint16_t g_pv_table[MAX_SEARCH_PLY][MAX_SEARCH_PLY];
static int g_pv_len[MAX_SEARCH_PLY];'''

    new_hist_pv = '''thread_local uint64_t g_game_history[MAX_GAME_HISTORY];
thread_local int g_game_history_len = 0;
static uint64_t g_master_game_history[MAX_GAME_HISTORY];
static int g_master_game_history_len = 0;

// PV Table (Phase C)
thread_local uint16_t g_pv_table[MAX_SEARCH_PLY][MAX_SEARCH_PLY];
thread_local int g_pv_len[MAX_SEARCH_PLY];'''
    assert old_hist_pv in code, "Could not find old_hist_pv"
    code = code.replace(old_hist_pv, new_hist_pv, 1)

    # 4. Threading globals and thread-local search stack
    old_time_stack = '''static bool g_use_pawn_hash = false;   // P1.5: 64K entry Pawn Hash Table
static bool g_dynamic_time_mgmt = false; // P1.5: Dynamic Time Management with stability & hard limits
static bool g_stop_search = false;
static std::chrono::steady_clock::time_point g_hard_deadline;
static uint64_t g_telemetry_pawn_probes = 0;
static uint64_t g_telemetry_pawn_hits = 0;
            // 0=E0 (Base), 1=E1 (Pawn), 2=E2 (Mobility), 3=E3 (King), 4=E4 (Endgame), 5=E5 (Combined)

// Search stack for continuation history tracking
struct SearchStackEntry {
    uint16_t current_move;
    int piece;
};
static SearchStackEntry g_ss[MAX_SEARCH_PLY];

// Continuation History tables: [prev_piece 0..5][prev_to 0..63][curr_piece 0..5][curr_to 0..63]
static int16_t g_conthist_1ply[6][64][6][64];
static int16_t g_conthist_2ply[6][64][6][64];'''

    new_time_stack = '''static bool g_use_pawn_hash = false;   // P1.5: 64K entry Pawn Hash Table
static bool g_dynamic_time_mgmt = false; // P1.5: Dynamic Time Management with stability & hard limits
static std::chrono::steady_clock::time_point g_hard_deadline;
static std::chrono::steady_clock::time_point g_search_start_time;
static uint64_t g_telemetry_pawn_probes = 0;
static uint64_t g_telemetry_pawn_hits = 0;

// Milestone P1.6: Lazy SMP Multithreading & Safe Late Move Pruning
static int g_num_threads = 1;
static std::atomic<bool> g_stop_search{false};
static bool g_use_lmp = false;
static int g_lmp_mode = 1; // 0=L0 (Off), 1=L1 (Conservative quadratic), 2=L2 (History-aware), 3=L3 (Integrated)
static int g_lmp_max_depth = 4;
static uint64_t g_telemetry_lmp_pruned = 0;
static uint64_t g_telemetry_tt_hits = 0;

// Search stack for continuation history tracking
struct SearchStackEntry {
    uint16_t current_move;
    int piece;
};
thread_local SearchStackEntry g_ss[MAX_SEARCH_PLY];
thread_local int16_t g_conthist_1ply[6][64][6][64];
thread_local int16_t g_conthist_2ply[6][64][6][64];
thread_local int t_thread_id = 0;'''
    assert old_time_stack in code, "Could not find old_time_stack"
    code = code.replace(old_time_stack, new_time_stack, 1)

    # 5. Thread-local countermove table
    old_cm = 'static uint16_t g_countermove_table[64][64];'
    new_cm = 'thread_local uint16_t g_countermove_table[64][64];'
    assert old_cm in code, "Could not find old_cm"
    code = code.replace(old_cm, new_cm, 1)

    # 6. Thread-local killers and history
    old_kh = '''constexpr int MAX_PLY = 64;
constexpr int KILLER_SLOTS = 2;
static uint16_t g_killer_moves[MAX_PLY][KILLER_SLOTS];

constexpr int SIDES = 2;
constexpr int SQUARES = 64;
constexpr int MAX_HISTORY_SCORE = 70000;
static int g_history_table[SIDES][SQUARES][SQUARES];'''

    new_kh = '''constexpr int MAX_PLY = 64;
constexpr int KILLER_SLOTS = 2;
thread_local uint16_t g_killer_moves[MAX_PLY][KILLER_SLOTS];

constexpr int SIDES = 2;
constexpr int SQUARES = 64;
constexpr int MAX_HISTORY_SCORE = 70000;
thread_local int g_history_table[SIDES][SQUARES][SQUARES];'''
    assert old_kh in code, "Could not find old_kh"
    code = code.replace(old_kh, new_kh, 1)

    # 7. Thread-local pawn table
    old_pt = 'static PawnHashEntry g_pawn_table[PAWN_HASH_SIZE];'
    new_pt = 'thread_local PawnHashEntry g_pawn_table[PAWN_HASH_SIZE];'
    assert old_pt in code, "Could not find old_pt"
    code = code.replace(old_pt, new_pt, 1)

    # 8. Synchronize native_reset_history and native_push_history
    old_h_funcs = '''EXPORT void native_reset_history() {
    g_game_history_len = 0;
}

EXPORT void native_push_history(uint64_t key) {
    if (g_game_history_len < MAX_GAME_HISTORY) {
        g_game_history[g_game_history_len++] = key;
    }
}'''

    new_h_funcs = '''EXPORT void native_reset_history() {
    g_game_history_len = 0;
    g_master_game_history_len = 0;
}

EXPORT void native_push_history(uint64_t key) {
    if (g_game_history_len < MAX_GAME_HISTORY) {
        g_game_history[g_game_history_len++] = key;
    }
    if (t_thread_id == 0 && g_master_game_history_len < MAX_GAME_HISTORY) {
        g_master_game_history[g_master_game_history_len++] = key;
    }
}'''
    assert old_h_funcs in code, "Could not find old_h_funcs"
    code = code.replace(old_h_funcs, new_h_funcs, 1)

    # 9. Add X11 in native_apply_search_variant
    old_var_x10 = '''        g_use_pawn_hash = true; // 64K entry Pawn Hash Table
        g_dynamic_time_mgmt = true; // Dynamic Time Management
    }
}'''

    new_var_x10 = '''        g_use_pawn_hash = true; // 64K entry Pawn Hash Table
        g_dynamic_time_mgmt = true; // Dynamic Time Management
        g_use_lmp = false;
    } else if (var == "X11") { // P1.6 Candidate: Lazy SMP Multithreading & Safe Late Move Pruning
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
    }
}'''
    assert old_var_x10 in code, "Could not find old_var_x10"
    code = code.replace(old_var_x10, new_var_x10, 1)

    # 10. Update negamax: periodic 2048 check and TT probe
    old_negamax_top = '''    if ((nodes & 2047) == 0) {
        if (std::chrono::steady_clock::now() >= deadline) {
            aborted = true;
            return 0;
        }
    }

    g_pv_len[ply] = 0;

    // Draw Adjudication in Search Tree (Phase B)
    if (ply > 0) {
        // 1. Fifty-move rule
        if (b->halfmove_clock >= 100) return 0;

        // 2. Insufficient material
        if (native_is_insufficient_material(b)) return 0;

        // 3. Repetition in tree: if the current position already occurred in game history or search path
        if (native_is_repetition(b, 2)) return 0;
    }

    // Leaf evaluation
    if (depth <= 0 || ply >= MAX_SEARCH_PLY - 1) {
        return quiescence(b, alpha, beta, nodes, deadline, aborted);
    }

    // TT Probe
    uint64_t key = b->zobrist_key;
    size_t tt_idx = key % TT_SIZE;
    TTEntry& entry = g_tt[tt_idx];
    uint16_t tt_move = 0;

    if (entry.key == key) {
        tt_move = entry.best_move;
        if (entry.depth >= depth && ply > 0 && excluded_move == 0) {
            int tt_score = score_from_tt(entry.score, ply);
            if (entry.flag == TT_EXACT) return tt_score;
            if (entry.flag == TT_LOWER && tt_score >= beta) return tt_score;
            if (entry.flag == TT_UPPER && tt_score <= alpha) return tt_score;
        }
    }'''

    new_negamax_top = '''    if ((nodes & 2047) == 0) {
        if (g_stop_search.load(std::memory_order_relaxed) || (t_thread_id == 0 && std::chrono::steady_clock::now() >= deadline)) {
            g_stop_search.store(true, std::memory_order_relaxed);
            aborted = true;
            return 0;
        }
    }

    g_pv_len[ply] = 0;

    // Draw Adjudication in Search Tree (Phase B)
    if (ply > 0) {
        // 1. Fifty-move rule
        if (b->halfmove_clock >= 100) return 0;

        // 2. Insufficient material
        if (native_is_insufficient_material(b)) return 0;

        // 3. Repetition in tree: if the current position already occurred in game history or search path
        if (native_is_repetition(b, 2)) return 0;
    }

    // Leaf evaluation
    if (depth <= 0 || ply >= MAX_SEARCH_PLY - 1) {
        return quiescence(b, alpha, beta, nodes, deadline, aborted);
    }

    // TT Probe
    uint64_t key = b->zobrist_key;
    uint16_t tt_move = 0;
    TTEntry entry{};
    bool has_entry = false;

    if (g_search_variant == "X11" || g_num_threads > 1) {
        int tt_score = 0;
        bool allow_cutoff = (ply > 0 && excluded_move == 0);
        if (g_parallel_tt.probe(key, depth, ply, alpha, beta, tt_score, tt_move, allow_cutoff)) {
            g_telemetry_tt_hits++;
            return tt_score;
        }
    } else {
        size_t tt_idx = key % TT_SIZE;
        entry = g_tt[tt_idx];
        if (entry.key == key) {
            has_entry = true;
            tt_move = entry.best_move;
            if (entry.depth >= depth && ply > 0 && excluded_move == 0) {
                int tt_score = score_from_tt(entry.score, ply);
                if (entry.flag == TT_EXACT) return tt_score;
                if (entry.flag == TT_LOWER && tt_score >= beta) return tt_score;
                if (entry.flag == TT_UPPER && tt_score <= alpha) return tt_score;
            }
        }
    }'''
    assert old_negamax_top in code, "Could not find old_negamax_top"
    code = code.replace(old_negamax_top, new_negamax_top, 1)

    # 11. Add LMP in negamax move loop before native_make_move
    old_make_move = '''        // Query moved piece BEFORE make_move modifies bitboards
        int move_from_sq = move_from(m);
        int moved_piece = NO_PIECE;
        for (int p = 0; p < 6; p++) {
            if (b->pieces[us_side][p] & (1ULL << move_from_sq)) {
                moved_piece = p;
                break;
            }
        }

        if (!native_make_move(b, m, &undo)) continue;'''

    new_make_move = '''        // Query moved piece BEFORE make_move modifies bitboards
        int move_from_sq = move_from(m);
        int moved_piece = NO_PIECE;
        for (int p = 0; p < 6; p++) {
            if (b->pieces[us_side][p] & (1ULL << move_from_sq)) {
                moved_piece = p;
                break;
            }
        }

        // ========================================================================
        // Late Move Pruning (LMP, Phase 5)
        // ========================================================================
        if (g_use_lmp && depth <= g_lmp_max_depth && ply > 0 && !in_check && (beta - alpha == 1)) {
            if (moves_searched > 0 && std::abs(alpha) < MATE_SCORE - 100 && std::abs(beta) < MATE_SCORE - 100) {
                int to_sq = move_to(m);
                int them_side = 1 - us_side;
                bool is_capture = (move_flag(m) == 2) || ((b->occupancy[them_side] & (1ULL << to_sq)) != 0);
                bool is_prom = (move_flag(m) == 3);
                if (!is_capture && !is_prom && m != tt_move && m != g_killer_moves[ply][0] && m != g_killer_moves[ply][1]) {
                    int lmp_thresh = 3 + 3 * depth * depth;
                    if (g_lmp_mode == 2) {
                        int h = g_history_table[us_side][move_from(m)][to_sq];
                        if (h < -1000 * depth || moves_searched >= lmp_thresh) {
                            g_telemetry_lmp_pruned++;
                            continue;
                        }
                    } else if (moves_searched >= lmp_thresh) {
                        g_telemetry_lmp_pruned++;
                        continue;
                    }
                }
            }
        }

        if (!native_make_move(b, m, &undo)) continue;'''
    assert old_make_move in code, "Could not find old_make_move"
    code = code.replace(old_make_move, new_make_move, 1)

    # 12. Update TT Store at bottom of negamax
    old_tt_store = '''        // Depth-preferred replacement with aging
        if (entry.key != key || depth >= entry.depth || entry.age != g_tt_age) {
            entry.key = key;
            entry.score = (int16_t)score_to_tt(best_score, ply);
            entry.depth = (int8_t)depth;
            entry.flag = flag;
            entry.age = g_tt_age;
            entry.best_move = best_move;
        }'''

    new_tt_store = '''        if (g_search_variant == "X11" || g_num_threads > 1) {
            g_parallel_tt.store(key, best_score, (int8_t)depth, flag, ply, best_move);
        } else {
            size_t tt_idx = key % TT_SIZE;
            TTEntry& entry_ref = g_tt[tt_idx];
            if (entry_ref.key != key || depth >= entry_ref.depth || entry_ref.age != g_tt_age) {
                entry_ref.key = key;
                entry_ref.score = (int16_t)score_to_tt(best_score, ply);
                entry_ref.depth = (int8_t)depth;
                entry_ref.flag = flag;
                entry_ref.age = g_tt_age;
                entry_ref.best_move = best_move;
            }
        }'''
    assert old_tt_store in code, "Could not find old_tt_store"
    code = code.replace(old_tt_store, new_tt_store, 1)

    # 13. Replace native_search with multithreaded Lazy SMP runner
    old_search_block = '''EXPORT int native_search(
    NativeBoard* b,
    int max_depth,
    double time_limit_sec,
    NativeSearchResult* out_res
) {
    init_attacks();
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    std::memset(g_ss, 0, sizeof(g_ss));
    if (g_tactical_ordering_mode > 0) {
        std::memset(g_countermove_table, 0, sizeof(g_countermove_table));
    }
    if (g_use_history_ordering) {
        for (int s = 0; s < SIDES; s++) {
            for (int f = 0; f < SQUARES; f++) {
                for (int t = 0; t < SQUARES; t++) {
                    g_history_table[s][f][t] /= 2;
                }
            }
        }
        if (g_conthist_mode > 0) {
            for (int p1 = 0; p1 < 6; p1++) {
                for (int s1 = 0; s1 < 64; s1++) {
                    for (int p2 = 0; p2 < 6; p2++) {
                        for (int s2 = 0; s2 < 64; s2++) {
                            g_conthist_1ply[p1][s1][p2][s2] /= 2;
                            g_conthist_2ply[p1][s1][p2][s2] /= 2;
                        }
                    }
                }
            }
        }
    }

    auto start_time = std::chrono::steady_clock::now();
    double current_time_limit_sec = time_limit_sec;
    auto soft_deadline = start_time + std::chrono::milliseconds(static_cast<int64_t>(current_time_limit_sec * 1000.0));
    auto deadline = soft_deadline;
    g_hard_deadline = start_time + std::chrono::milliseconds(static_cast<int64_t>(current_time_limit_sec * 2200.0));
    g_stop_search = false;

    uint64_t total_nodes = 0;
    uint16_t prev_root_move = 0;
    uint16_t prev_prev_root_move = 0;
    int stable_move_count = 0;
    int prev_iteration_score = 0;
    out_res->depth = 0;
    out_res->nodes = 0;
    out_res->score = 0;
    out_res->best_move = 0;
    out_res->elapsed_seconds = 0.0;
    out_res->pv_length = 0;

    bool aborted = false;
    g_tt_age++;

    for (int d = 1; d <= max_depth; d++) {
        uint16_t iter_best_move = 0;
        int score = 0;

        if (g_use_aspiration_window && d >= 4) {
            int prev_score = out_res->score;
            int asp_alpha = prev_score - g_aspiration_delta;
            int asp_beta = prev_score + g_aspiration_delta;
            int delta = g_aspiration_delta;

            while (true) {
                score = negamax(b, d, asp_alpha, asp_beta, 0, total_nodes, deadline, aborted, &iter_best_move);
                if (aborted) break;

                if (score <= asp_alpha) {
                    g_telemetry_aspiration_researches++;
                    asp_alpha = std::max(-INF, asp_alpha - delta * 2);
                    delta *= 2;
                } else if (score >= asp_beta) {
                    g_telemetry_aspiration_researches++;
                    asp_beta = std::min(INF, asp_beta + delta * 2);
                    delta *= 2;
                } else {
                    break; // Inside window!
                }
                if (asp_alpha <= -INF && asp_beta >= INF) {
                    break;
                }
            }
        } else {
            score = negamax(b, d, -INF, INF, 0, total_nodes, deadline, aborted, &iter_best_move);
        }

        if (aborted) break;

        auto now = std::chrono::steady_clock::now();
        std::chrono::duration<double> dur = now - start_time;

        out_res->depth = d;
        out_res->best_move = iter_best_move;
        out_res->score = score;
        out_res->nodes = total_nodes;
        out_res->elapsed_seconds = dur.count();

        // Copy PV
        out_res->pv_length = g_pv_len[0];
        for (int i = 0; i < g_pv_len[0]; i++) {
            out_res->pv[i] = g_pv_table[0][i];
        }

        if (dur.count() >= time_limit_sec) break;
    }

    auto final_time = std::chrono::steady_clock::now();
    std::chrono::duration<double> total_dur = final_time - start_time;
    out_res->elapsed_seconds = total_dur.count();
    out_res->nodes = total_nodes;

    return 1;
}'''

    new_search_block = '''struct WorkerSearchResult {
    int depth{0};
    int score{0};
    uint16_t best_move{0};
    uint64_t nodes{0};
    uint16_t pv[MAX_SEARCH_PLY];
    int pv_length{0};
};

static void run_worker_search(
    int thread_id,
    NativeBoard root_board,
    int max_depth,
    double time_limit_sec,
    std::chrono::steady_clock::time_point deadline,
    WorkerSearchResult* out_wres
) {
    t_thread_id = thread_id;
    g_game_history_len = g_master_game_history_len;
    for (int i = 0; i < g_master_game_history_len; ++i) {
        g_game_history[i] = g_master_game_history[i];
    }
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    std::memset(g_ss, 0, sizeof(g_ss));
    if (g_tactical_ordering_mode > 0) {
        std::memset(g_countermove_table, 0, sizeof(g_countermove_table));
    }

    int start_depth = (thread_id == 2) ? 2 : 1;
    int asp_delta = (thread_id == 1) ? (g_aspiration_delta * 2) : g_aspiration_delta;
    uint64_t worker_nodes = 0;
    bool aborted = false;

    for (int d = start_depth; d <= max_depth; ++d) {
        if (g_stop_search.load(std::memory_order_relaxed)) break;

        uint16_t iter_best_move = 0;
        int score = 0;

        if (g_use_aspiration_window && d >= 4) {
            int prev_score = out_wres->score;
            int asp_alpha = prev_score - asp_delta;
            int asp_beta = prev_score + asp_delta;
            int delta = asp_delta;

            while (true) {
                score = negamax(&root_board, d, asp_alpha, asp_beta, 0, worker_nodes, deadline, aborted, &iter_best_move);
                if (aborted || g_stop_search.load(std::memory_order_relaxed)) break;

                if (score <= asp_alpha) {
                    asp_alpha = std::max(-INF, asp_alpha - delta * 2);
                    delta *= 2;
                } else if (score >= asp_beta) {
                    asp_beta = std::min(INF, asp_beta + delta * 2);
                    delta *= 2;
                } else {
                    break;
                }
                if (asp_alpha <= -INF && asp_beta >= INF) break;
            }
        } else {
            score = negamax(&root_board, d, -INF, INF, 0, worker_nodes, deadline, aborted, &iter_best_move);
        }

        if (aborted || g_stop_search.load(std::memory_order_relaxed)) break;

        out_wres->depth = d;
        out_wres->score = score;
        if (iter_best_move != 0) {
            out_wres->best_move = iter_best_move;
        }
        out_wres->pv_length = g_pv_len[0];
        for (int i = 0; i < g_pv_len[0]; ++i) {
            out_wres->pv[i] = g_pv_table[0][i];
        }
        out_wres->nodes = worker_nodes;

        if (thread_id == 0) {
            auto now = std::chrono::steady_clock::now();
            double elapsed = std::chrono::duration<double>(now - g_search_start_time).count();
            if (elapsed >= time_limit_sec) {
                g_stop_search.store(true, std::memory_order_relaxed);
                break;
            }
        }
    }
    out_wres->nodes = worker_nodes;
}

EXPORT int native_search(
    NativeBoard* b,
    int max_depth,
    double time_limit_sec,
    NativeSearchResult* out_res
) {
    init_attacks();
    auto start_time = std::chrono::steady_clock::now();
    g_search_start_time = start_time;
    g_stop_search.store(false, std::memory_order_relaxed);

    double current_time_limit_sec = time_limit_sec;
    auto soft_deadline = start_time + std::chrono::milliseconds(static_cast<int64_t>(current_time_limit_sec * 1000.0));
    auto deadline = soft_deadline;
    g_hard_deadline = start_time + std::chrono::milliseconds(static_cast<int64_t>(current_time_limit_sec * 2200.0));

    g_tt_age++;
    g_parallel_tt.current_age.fetch_add(1, std::memory_order_relaxed);

    g_master_game_history_len = g_game_history_len;
    for (int i = 0; i < g_game_history_len; ++i) {
        g_master_game_history[i] = g_game_history[i];
    }

    int n_threads = std::max(1, g_num_threads);
    std::vector<WorkerSearchResult> w_res(n_threads);

    if (n_threads == 1) {
        run_worker_search(0, *b, max_depth, time_limit_sec, deadline, &w_res[0]);
    } else {
        std::vector<std::thread> helpers;
        for (int t = 1; t < n_threads; ++t) {
            helpers.emplace_back(run_worker_search, t, *b, max_depth, time_limit_sec, deadline, &w_res[t]);
        }
        run_worker_search(0, *b, max_depth, time_limit_sec, deadline, &w_res[0]);

        g_stop_search.store(true, std::memory_order_relaxed);
        for (auto& th : helpers) {
            if (th.joinable()) th.join();
        }
    }

    uint64_t agg_nodes = 0;
    for (int t = 0; t < n_threads; ++t) {
        agg_nodes += w_res[t].nodes;
    }

    int best_worker = 0;
    for (int t = 1; t < n_threads; ++t) {
        if (w_res[t].depth > w_res[best_worker].depth && w_res[t].best_move != 0) {
            best_worker = t;
        }
    }

    auto final_time = std::chrono::steady_clock::now();
    double total_dur = std::chrono::duration<double>(final_time - start_time).count();

    out_res->depth = w_res[best_worker].depth;
    out_res->best_move = w_res[best_worker].best_move;
    out_res->score = w_res[best_worker].score;
    out_res->nodes = agg_nodes;
    out_res->elapsed_seconds = total_dur;
    out_res->pv_length = w_res[best_worker].pv_length;
    for (int i = 0; i < w_res[best_worker].pv_length; ++i) {
        out_res->pv[i] = w_res[best_worker].pv[i];
    }

    if (out_res->best_move == 0) {
        uint16_t lmoves[MAX_MOVES];
        int ln = native_generate_legal_moves(b, lmoves);
        if (ln > 0) out_res->best_move = lmoves[0];
    }

    return 1;
}'''
    assert old_search_block in code, "Could not find old_search_block"
    code = code.replace(old_search_block, new_search_block, 1)

    # 14. Update UCI loop options
    old_uci_opts = '''            std::cout << "id name Janus Classical X (P1.5 Candidate X10)" << std::endl;
            std::cout << "id author Project Janus Team" << std::endl;'''

    new_uci_opts = '''            std::cout << "id name Janus Classical X (P1.6 Candidate X11)" << std::endl;
            std::cout << "id author Project Janus Team" << std::endl;
            std::cout << "option name Threads type spin default 1 min 1 max 16" << std::endl;
            std::cout << "option name UCI_LMP type combo default L1 var L0 var L1 var L2 var L3" << std::endl;'''
    assert old_uci_opts in code, "Could not find old_uci_opts"
    code = code.replace(old_uci_opts, new_uci_opts, 1)

    # 15. Update UCI variant options list
    old_var_combo = 'default X10 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10'
    new_var_combo = 'default X11 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11'
    assert old_var_combo in code, "Could not find old_var_combo"
    code = code.replace(old_var_combo, new_var_combo, 1)

    # 16. Update UCI setoption parser
    old_setopt = '''                if (opt_name == "UseKillerOrdering") {'''
    new_setopt = '''                if (opt_name == "Threads" && !opt_val.empty()) {
                    g_num_threads = std::max(1, std::min(16, std::stoi(opt_val)));
                } else if (opt_name == "UCI_LMP" && !opt_val.empty()) {
                    if (opt_val == "L0") { g_use_lmp = false; g_lmp_mode = 0; }
                    else if (opt_val == "L1") { g_use_lmp = true; g_lmp_mode = 1; }
                    else if (opt_val == "L2") { g_use_lmp = true; g_lmp_mode = 2; }
                    else if (opt_val == "L3") { g_use_lmp = true; g_lmp_mode = 3; }
                } else if (opt_name == "UseKillerOrdering") {'''
    assert old_setopt in code, "Could not find old_setopt"
    code = code.replace(old_setopt, new_setopt, 1)

    # 17. Update ucinewgame to clear g_parallel_tt
    old_newgame = '''            native_reset_ordering_telemetry();
            std::memset(g_tt, 0, sizeof(g_tt));
            native_reset_lmr_telemetry();'''

    new_newgame = '''            native_reset_ordering_telemetry();
            std::memset(g_tt, 0, sizeof(g_tt));
            g_parallel_tt.clear();
            native_reset_lmr_telemetry();'''
    assert old_newgame in code, "Could not find old_newgame"
    code = code.replace(old_newgame, new_newgame, 1)

    # 18. Handle 'stop' command in uci_loop
    old_quit = '} else if (cmd == "quit") {'
    new_quit = '''} else if (cmd == "stop") {
            g_stop_search.store(true, std::memory_order_relaxed);
        } else if (cmd == "quit") {
            g_stop_search.store(true, std::memory_order_relaxed);'''
    assert old_quit in code, "Could not find old_quit"
    code = code.replace(old_quit, new_quit, 1)

    # Write target files
    with open(TARGET_CPP, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Generated {TARGET_CPP} ({len(code):,} bytes).")

    # Also update engine/classical_x/janus_classical_x.cpp
    with open(BASE_CPP, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Updated {BASE_CPP} ({len(code):,} bytes).")

def compile_x11():
    print("\n[COMPILING] Building Janus Classical X11 EXE and DLL...")
    cwd = str(ROOT / "engine" / "classical_x")
    cmd_exe = f'cmd.exe /c ""{VCVARS}" && cl /O2 /Ot /Oi /std:c++17 /EHsc janus_classical_x.cpp /Fe:janus_classical_x.exe"'
    res_exe = subprocess.run(cmd_exe, cwd=cwd, shell=True, capture_output=True, text=True)
    if res_exe.returncode != 0:
        print("EXE BUILD FAILED:\n", res_exe.stdout, res_exe.stderr)
        sys.exit(1)
    print("[COMPILING] janus_classical_x.exe built successfully.")

    cmd_dll = f'cmd.exe /c ""{VCVARS}" && cl /O2 /Ot /Oi /std:c++17 /EHsc /LD janus_classical_x.cpp /Fe:janus_classical_x.dll"'
    res_dll = subprocess.run(cmd_dll, cwd=cwd, shell=True, capture_output=True, text=True)
    if res_dll.returncode != 0:
        print("DLL BUILD FAILED:\n", res_dll.stdout, res_dll.stderr)
        sys.exit(1)
    print("[COMPILING] janus_classical_x.dll built successfully.")

    # Copy to control directory
    shutil.copy2(ROOT / "engine" / "classical_x" / "janus_classical_x.exe", TARGET_EXE)
    shutil.copy2(ROOT / "engine" / "classical_x" / "janus_classical_x.dll", TARGET_DLL)
    print(f"[CONTROL] Copied binaries to {TARGET_DIR}")

def main():
    generate_x11_source()
    compile_x11()

if __name__ == "__main__":
    main()
