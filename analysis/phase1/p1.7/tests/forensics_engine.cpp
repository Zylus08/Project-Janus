/*
 * Project Janus v0.51 - Native Search Core & Standalone UCI Engine (Candidate N2)
 *
 * Full C++17 native chess engine implementing:
 * - 64-bit bitboard state representation (pieces, occupancies, castling, EP)
 * - Polyglot-compatible 64-bit Zobrist hashing with incremental make/unmake
 * - FIDE Legal Move Generation (pins, checks, double checks, castling, en passant, promotions)
 * - FIDE Draw & Repetition History: 1,024-ply game history stack
 * - Explicit distinction between Claimable Draws (Threefold, 50-move) and Automatic Draws (Fivefold, 75-move, Insufficient Material)
 * - Intended-move draw claim detection
 * - Alpha-Beta Negamax search with Iterative Deepening
 * - 1M-entry Transposition Table with depth-preferred aging and normalized mate scores
 * - Quiescence Search with delta pruning and MVV-LVA capture ordering
 * - Triangular PV Table for exact principal variation tracking
 * - Standalone UCI Protocol loop (uci, isready, ucinewgame, position, go, stop, quit)
 * - Time management with Fischer increment support and safety margins
 */

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <thread>
#include <atomic>
#include <immintrin.h>

#ifdef _MSC_VER
#include <intrin.h>
#define EXPORT extern "C" __declspec(dllexport)
#else
#define EXPORT extern "C"
#endif

// ============================================================================
// Constants & Configuration
// ============================================================================

constexpr int WHITE = 0;
constexpr int BLACK = 1;
constexpr int NO_COLOR = 2;

constexpr int PAWN = 0;
constexpr int KNIGHT = 1;
constexpr int BISHOP = 2;
constexpr int ROOK = 3;
constexpr int QUEEN = 4;
constexpr int KING = 5;
constexpr int NO_PIECE = 6;

constexpr int INF = 30000;
constexpr int MATE_SCORE = 29000;
constexpr int MATE_THRESHOLD = 28000;

constexpr uint8_t CASTLE_W_OO = 1;
constexpr uint8_t CASTLE_W_OOO = 2;
constexpr uint8_t CASTLE_B_OO = 4;
constexpr uint8_t CASTLE_B_OOO = 8;

constexpr int MAX_SEARCH_PLY = 128;
constexpr int MAX_MOVES = 256;
constexpr int MAX_GAME_HISTORY = 1024;

// Move encoding (uint16_t):
// bits 0..5: from
// bits 6..11: to
// bits 12..13: flag (0=normal, 1=castle, 2=ep, 3=promo)
// bits 14..15: promo piece (0=N, 1=B, 2=R, 3=Q)
inline uint16_t encode_move(int from, int to, int flag = 0, int promo = 0) {
    return (from & 0x3F) | ((to & 0x3F) << 6) | ((flag & 3) << 12) | ((promo & 3) << 14);
}
inline int move_from(uint16_t m) { return m & 0x3F; }
inline int move_to(uint16_t m) { return (m >> 6) & 0x3F; }
inline int move_flag(uint16_t m) { return (m >> 12) & 3; }
inline int move_promo(uint16_t m) { return (m >> 14) & 3; }

// ============================================================================
// Core Structs
// ============================================================================

struct NativeBoard {
    uint64_t pieces[2][6];    // [color][piece]
    uint64_t occupancy[3];    // 0=white, 1=black, 2=both
    uint8_t side_to_move;     // 0=white, 1=black
    uint8_t castling_rights;  // 4-bit mask
    uint8_t ep_square;        // 0..63, or 64 if none
    uint16_t halfmove_clock;
    uint16_t fullmove_number;
    uint64_t zobrist_key;
};

struct UndoInfo {
    uint8_t captured_piece;   // 0..5, or 6 if none
    uint8_t castling_rights;
    uint8_t ep_square;
    uint16_t halfmove_clock;
    uint64_t zobrist_key;
};

struct NativeSearchResult {
    uint16_t best_move;
    int score;
    int depth;
    uint64_t nodes;
    double elapsed_seconds;
    int pv_length;
    uint16_t pv[MAX_SEARCH_PLY];
};

// ============================================================================
// Transposition Table Layout & Mate Normalization
// ============================================================================

constexpr uint8_t TT_EXACT = 0;
constexpr uint8_t TT_LOWER = 1;
constexpr uint8_t TT_UPPER = 2;

struct TTEntry {
    uint64_t key;
    int16_t score;
    int8_t depth;
    uint8_t flag;
    uint8_t age;
    uint16_t best_move;
};

constexpr size_t TT_SIZE = 1 << 20; // 1,048,576 entries (~24 MB)
static TTEntry g_tt[TT_SIZE];
static uint8_t g_tt_age = 0;

inline int score_to_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_SEARCH_PLY) return score + ply;
    if (score <= -MATE_SCORE + MAX_SEARCH_PLY) return score - ply;
    return score;
}

inline int score_from_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_SEARCH_PLY) return score - ply;
    if (score <= -MATE_SCORE + MAX_SEARCH_PLY) return score + ply;
    return score;
}


struct TTTelemetry {
    std::atomic<uint64_t> probes{0};
    std::atomic<uint64_t> hits{0};
    std::atomic<uint64_t> cutoffs{0};
    std::atomic<uint64_t> stores{0};
    std::atomic<uint64_t> same_key_overwrites{0};
    std::atomic<uint64_t> shallower_overwrites{0};
    std::atomic<uint64_t> cross_key_evictions{0};
    std::atomic<uint64_t> lock_spins{0};

    void reset() {
        probes.store(0);
        hits.store(0);
        cutoffs.store(0);
        stores.store(0);
        same_key_overwrites.store(0);
        shallower_overwrites.store(0);
        cross_key_evictions.store(0);
        lock_spins.store(0);
    }
};

static TTTelemetry g_tt_telemetry;
EXPORT void native_move_to_uci(uint16_t m, char* out_str);

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

        g_tt_telemetry.probes.fetch_add(1, std::memory_order_relaxed);
        while (c.lock.test_and_set(std::memory_order_acquire)) {
            g_tt_telemetry.lock_spins.fetch_add(1, std::memory_order_relaxed);
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
                    g_tt_telemetry.hits.fetch_add(1, std::memory_order_relaxed);
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
                    if (hit) g_tt_telemetry.cutoffs.fetch_add(1, std::memory_order_relaxed);
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

        g_tt_telemetry.stores.fetch_add(1, std::memory_order_relaxed);
        while (c.lock.test_and_set(std::memory_order_acquire)) {
            g_tt_telemetry.lock_spins.fetch_add(1, std::memory_order_relaxed);
            _mm_pause();
        }

        int replace_idx = -1;
        int lowest_depth = 999;
        int oldest_age_diff = -1;

        for (int i = 0; i < 4; ++i) {
            if (c.entries[i].key == key) {
                replace_idx = i;
                g_tt_telemetry.same_key_overwrites.fetch_add(1, std::memory_order_relaxed);
                if (depth < c.entries[i].depth) {
                    g_tt_telemetry.shallower_overwrites.fetch_add(1, std::memory_order_relaxed);
                }
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
            if (c.entries[replace_idx].key != 0 && c.entries[replace_idx].key != key) {
                g_tt_telemetry.cross_key_evictions.fetch_add(1, std::memory_order_relaxed);
            }
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

static ParallelTranspositionTable g_parallel_tt;

// ============================================================================
// Game History & Repetition Stack (Phase B)
// ============================================================================

thread_local uint64_t g_game_history[MAX_GAME_HISTORY];
thread_local int g_game_history_len = 0;
static uint64_t g_master_game_history[MAX_GAME_HISTORY];
static int g_master_game_history_len = 0;

// PV Table (Phase C)
thread_local uint16_t g_pv_table[MAX_SEARCH_PLY][MAX_SEARCH_PLY];
thread_local int g_pv_len[MAX_SEARCH_PLY];

// LMR Configuration & Telemetry (Phase 3 v0.52 - Category A Promoted)
static bool g_use_lmr = true;
static int g_lmr_min_depth = 3;
static int g_lmr_move_threshold = 4;
static int g_lmr_base_reduction = 1;

static uint64_t g_lmr_eligible_moves = 0;
static uint64_t g_lmr_reduced_moves = 0;
static uint64_t g_lmr_researches = 0;
static uint64_t g_lmr_cutoffs = 0;

// PVS Configuration & Telemetry (Phase 3 v0.53)
static bool g_use_pvs = false;

static uint64_t g_pvs_full_window_searches = 0;
static uint64_t g_pvs_null_window_searches = 0;
static uint64_t g_pvs_researches = 0;
static uint64_t g_pvs_cutoffs = 0;

// Move Ordering Configuration & Telemetry (Phase 2 & 3 v0.54)
static bool g_use_killer_ordering = true;
static bool g_use_history_ordering = true;

// SEE Configuration & Telemetry (Phase 4 v0.56)
static bool g_use_see_ordering = false;
static bool g_use_see_in_quiescence = false;

static uint64_t g_see_total_evaluations = 0;
static uint64_t g_see_positive_captures = 0;
static uint64_t g_see_neutral_captures = 0;
static uint64_t g_see_negative_captures = 0;
static uint64_t g_see_ordering_inversions = 0;

// ============================================================================
// Search Modernization Configuration Options (Milestone P1.1)
// ============================================================================
static bool g_use_staged_movegen = true;       // Phase 1: Staged move generation / MovePicker
static int  g_quiescence_see_mode = 2;         // Phase 2: 0=Q0 (Off), 1=Q1 (Ordering only), 2=Q2 (Prune SEE < 0), 3=Q3 (Prune SEE < -50)
static bool g_use_null_move_pruning = true;    // Phase 3: Null-Move Pruning (R=3, zugzwang protection)
static int  g_nmp_reduction = 3;               // Base NMP reduction R=3
static bool g_use_reverse_futility = true;     // Phase 4: Reverse Futility Pruning (d <= 3, margin = 80 * d)
static int  g_rfp_margin_per_depth = 80;       // Margin per ply
static bool g_use_aspiration_window = true;    // Phase 5: Aspiration Windows (delta = 25 cp)
static int  g_aspiration_delta = 25;           // Aspiration delta
static std::string g_search_variant = "X7";    // Active variant identifier (Default Candidate X7)

// ============================================================================
// Search Modernization & Positional Evaluation Options (Milestone P1.2)
// ============================================================================
static int g_conthist_mode = 3;       // 0=H0 (Off), 1=H1 (1-ply), 2=H2 (2-ply), 3=H3 (1-ply+2-ply)
static int g_dynamic_lmr_mode = 3;     // 0=L0 (Static base), 1=L1 (Log table), 2=L2 (Hist mod), 3=L3 (Conthist mod)
static int g_eval_mode = 5;            // 0=E0..5=E5 (X7), 6=E6..10=E10 (X10)
static bool g_use_pawn_hash = false;   // P1.5: 64K entry Pawn Hash Table
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
thread_local int t_thread_id = 0;

// Dynamic Logarithmic LMR table: [depth][move_count]
static int g_lmr_table[MAX_SEARCH_PLY][MAX_MOVES];

// Precomputed passed pawn masks
static uint64_t white_passed_pawn_mask[64];
static uint64_t black_passed_pawn_mask[64];

// P1.2 Telemetry Counters
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
thread_local uint16_t g_countermove_table[64][64];

// P1.3 Telemetry Counters
static uint64_t g_telemetry_capthist_probes = 0;
static uint64_t g_telemetry_capthist_cutoffs = 0;
static uint64_t g_telemetry_countermove_probes = 0;
static uint64_t g_telemetry_countermove_cutoffs = 0;
static uint64_t g_telemetry_se_probes = 0;
static uint64_t g_telemetry_se_extended = 0;
static uint64_t g_telemetry_multicut_cutoffs = 0;
static uint64_t g_telemetry_probcut_probes = 0;
static uint64_t g_telemetry_probcut_cutoffs = 0;

// P1.1 Telemetry Counters
static uint64_t g_telemetry_movegen_calls = 0;
static uint64_t g_telemetry_captures_gen = 0;
static uint64_t g_telemetry_quiets_gen = 0;
static uint64_t g_telemetry_moves_scored = 0;
static uint64_t g_telemetry_moves_searched = 0;
static uint64_t g_telemetry_first_move_cutoffs = 0;
static uint64_t g_telemetry_total_cutoffs = 0;
static uint64_t g_telemetry_nmp_probes = 0;
static uint64_t g_telemetry_nmp_cutoffs = 0;
static uint64_t g_telemetry_rfp_probes = 0;
static uint64_t g_telemetry_rfp_cutoffs = 0;
static uint64_t g_telemetry_aspiration_researches = 0;
static uint64_t g_telemetry_qmoves_pruned = 0;

EXPORT void native_apply_search_variant(const char* var_str) {
    if (!var_str) return;
    std::string var(var_str);
    g_search_variant = var;
    if (var == "X0") { // C1 Frozen Baseline Equivalent
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = false;
        g_use_aspiration_window = false;
    } else if (var == "X1") { // Staged Movegen Only
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = false;
        g_use_aspiration_window = false;
    } else if (var == "X2") { // Quiescence SEE Only
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = false;
        g_use_aspiration_window = false;
    } else if (var == "X3") { // NMP Only
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = false;
        g_use_aspiration_window = false;
    } else if (var == "X4") { // RFP Only
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = true;
        g_use_aspiration_window = false;
    } else if (var == "X5") { // Aspiration Windows Only
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = false;
        g_use_aspiration_window = true;
    } else if (var == "X6") { // P1.1 Integrated Baseline (Strict Bit-Exact Invariant)
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 0; // H0 Off
        g_dynamic_lmr_mode = 0; // L0 Static Base
        g_eval_mode = 0; // E0 Base Classical Eval
    } else if (var == "X7") { // P1.2 Frozen Baseline (Strict Bit-Exact Invariant)
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
    } else if (var == "X9") { // P1.4 Qualified Candidate (Countermove Modernization & Depth Maximization)
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3
        g_dynamic_lmr_mode = 3; // L3 Calibrated
        g_eval_mode = 5; // E5
        g_tactical_ordering_mode = 2; // M2: Countermove Heuristic Only (Depth Dividend +0.3 plies)
        g_singular_extension_mode = 0; // S0: Off (Eliminates verification search depth tax)
        g_multicut_mode = 0; // C0: Off
        g_probcut_mode = 0; // P0: Off
        g_use_pawn_hash = false;
        g_dynamic_time_mgmt = false;
    } else if (var == "X10") { // P1.5 Candidate: Evaluation Expressiveness, Pawn Hash & Dynamic Time Management
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
}

EXPORT void native_reset_p11_telemetry() {
    g_telemetry_movegen_calls = 0;
    g_telemetry_captures_gen = 0;
    g_telemetry_quiets_gen = 0;
    g_telemetry_moves_scored = 0;
    g_telemetry_moves_searched = 0;
    g_telemetry_first_move_cutoffs = 0;
    g_telemetry_total_cutoffs = 0;
    g_telemetry_nmp_probes = 0;
    g_telemetry_nmp_cutoffs = 0;
    g_telemetry_rfp_probes = 0;
    g_telemetry_rfp_cutoffs = 0;
    g_telemetry_aspiration_researches = 0;
    g_telemetry_qmoves_pruned = 0;
}


constexpr int MAX_PLY = 64;
constexpr int KILLER_SLOTS = 2;
thread_local uint16_t g_killer_moves[MAX_PLY][KILLER_SLOTS];

constexpr int SIDES = 2;
constexpr int SQUARES = 64;
constexpr int MAX_HISTORY_SCORE = 70000;
thread_local int g_history_table[SIDES][SQUARES][SQUARES];

static uint64_t g_ordering_total_cutoffs = 0;
static uint64_t g_ordering_sum_cutoff_index = 0;
static uint64_t g_ordering_cutoff_move_1 = 0;
static uint64_t g_ordering_cutoff_move_2 = 0;
static uint64_t g_ordering_cutoff_move_3 = 0;
static uint64_t g_ordering_cutoff_move_4plus = 0;
static uint64_t g_ordering_cutoff_tt = 0;
static uint64_t g_ordering_cutoff_killer1 = 0;
static uint64_t g_ordering_cutoff_killer2 = 0;
static uint64_t g_ordering_cutoff_history = 0;
static uint64_t g_ordering_cutoff_captures = 0;
static uint64_t g_ordering_cutoff_quiet = 0;

// ============================================================================
// Attack Tables and Zobrist Keys
// ============================================================================

static uint64_t knight_attacks[64];
static uint64_t king_attacks[64];
static uint64_t pawn_attacks[2][64];

static uint64_t zobrist_pieces[2][6][64];
static uint64_t zobrist_castling[16];
static uint64_t zobrist_ep[65];
static uint64_t zobrist_side;
static bool tables_initialized = false;

// PRNG for Zobrist (Polyglot compatible LCG)
static uint64_t lcg_rand64() {
    static uint64_t seed = 1070372;
    seed = seed * 6364136223846793005ULL + 1442695040888963407ULL;
    return seed;
}

// Bit manipulation primitives
inline int popcount64(uint64_t b) {
#ifdef _MSC_VER
    return (int)__popcnt64(b);
#else
    return __builtin_popcountll(b);
#endif
}

inline int bitscan_forward(uint64_t b) {
#ifdef _MSC_VER
    unsigned long idx;
    _BitScanForward64(&idx, b);
    return (int)idx;
#else
    return __builtin_ctzll(b);
#endif
}

inline int bitscan_reverse(uint64_t b) {
#ifdef _MSC_VER
    unsigned long idx;
    _BitScanReverse64(&idx, b);
    return (int)idx;
#else
    return 63 - __builtin_clzll(b);
#endif
}

// Ray-casting sliding attacks
static uint64_t rook_attacks_bb(int sq, uint64_t occ) {
    uint64_t att = 0;
    int r = sq / 8, f = sq % 8;
    for (int i = r + 1; i <= 7; i++) { int s = i * 8 + f; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int i = r - 1; i >= 0; i--) { int s = i * 8 + f; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int j = f + 1; j <= 7; j++) { int s = r * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int j = f - 1; j >= 0; j--) { int s = r * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    return att;
}

static uint64_t bishop_attacks_bb(int sq, uint64_t occ) {
    uint64_t att = 0;
    int r = sq / 8, f = sq % 8;
    for (int i = r + 1, j = f + 1; i <= 7 && j <= 7; i++, j++) { int s = i * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int i = r + 1, j = f - 1; i <= 7 && j >= 0; i++, j--) { int s = i * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int i = r - 1, j = f + 1; i >= 0 && j <= 7; i--, j++) { int s = i * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int i = r - 1, j = f - 1; i >= 0 && j >= 0; i--, j--) { int s = i * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    return att;
}

inline uint64_t queen_attacks_bb(int sq, uint64_t occ) {
    return rook_attacks_bb(sq, occ) | bishop_attacks_bb(sq, occ);
}

static void init_attacks() {
    if (tables_initialized) return;

    for (int sq = 0; sq < 64; sq++) {
        int r = sq / 8, f = sq % 8;
        // Knight
        uint64_t b = 0;
        int dr[8] = { 2, 1, -1, -2, -2, -1, 1, 2 };
        int df[8] = { 1, 2, 2, 1, -1, -2, -2, -1 };
        for (int i = 0; i < 8; i++) {
            int nr = r + dr[i], nf = f + df[i];
            if (nr >= 0 && nr < 8 && nf >= 0 && nf < 8) b |= (1ULL << (nr * 8 + nf));
        }
        knight_attacks[sq] = b;

        // King
        b = 0;
        int kr[8] = { 1, 1, 1, 0, 0, -1, -1, -1 };
        int kf[8] = { -1, 0, 1, -1, 1, -1, 0, 1 };
        for (int i = 0; i < 8; i++) {
            int nr = r + kr[i], nf = f + kf[i];
            if (nr >= 0 && nr < 8 && nf >= 0 && nf < 8) b |= (1ULL << (nr * 8 + nf));
        }
        king_attacks[sq] = b;

        // White Pawn Attacks (moves up: +7, +9)
        uint64_t wp = 0;
        if (r < 7 && f > 0) wp |= (1ULL << ((r + 1) * 8 + f - 1));
        if (r < 7 && f < 7) wp |= (1ULL << ((r + 1) * 8 + f + 1));
        pawn_attacks[WHITE][sq] = wp;

        // Black Pawn Attacks (moves down: -9, -7)
        uint64_t bp = 0;
        if (r > 0 && f > 0) bp |= (1ULL << ((r - 1) * 8 + f - 1));
        if (r > 0 && f < 7) bp |= (1ULL << ((r - 1) * 8 + f + 1));
        pawn_attacks[BLACK][sq] = bp;

        // Passed pawn masks (P1.2 Handcrafted Eval)
        uint64_t w_mask = 0;
        for (int rr = r + 1; rr <= 7; rr++) {
            for (int ff = std::max(0, f - 1); ff <= std::min(7, f + 1); ff++) {
                w_mask |= (1ULL << (rr * 8 + ff));
            }
        }
        white_passed_pawn_mask[sq] = w_mask;

        uint64_t b_mask = 0;
        for (int rr = 0; rr < r; rr++) {
            for (int ff = std::max(0, f - 1); ff <= std::min(7, f + 1); ff++) {
                b_mask |= (1ULL << (rr * 8 + ff));
            }
        }
        black_passed_pawn_mask[sq] = b_mask;
    }

    // Dynamic LMR logarithmic table initialization
    for (int d = 0; d < MAX_SEARCH_PLY; d++) {
        for (int m = 0; m < MAX_MOVES; m++) {
            if (d >= 1 && m >= 1) {
                double r_val = 0.75 + std::log((double)d) * std::log((double)m) / 2.25;
                g_lmr_table[d][m] = (int)r_val;
            } else {
                g_lmr_table[d][m] = 0;
            }
        }
    }

    // Zobrist initialization
    for (int c = 0; c < 2; c++) {
        for (int p = 0; p < 6; p++) {
            for (int s = 0; s < 64; s++) {
                zobrist_pieces[c][p][s] = lcg_rand64();
            }
        }
    }
    for (int i = 0; i < 16; i++) zobrist_castling[i] = lcg_rand64();
    for (int i = 0; i < 65; i++) zobrist_ep[i] = lcg_rand64();
    zobrist_side = lcg_rand64();

    tables_initialized = true;
}

// Compute 64-bit Zobrist key from scratch
static uint64_t compute_zobrist(const NativeBoard* b) {
    uint64_t key = 0;
    for (int c = 0; c < 2; c++) {
        for (int p = 0; p < 6; p++) {
            uint64_t bb = b->pieces[c][p];
            while (bb) {
                int sq = bitscan_forward(bb);
                key ^= zobrist_pieces[c][p][sq];
                bb &= bb - 1;
            }
        }
    }
    key ^= zobrist_castling[b->castling_rights & 15];
    key ^= zobrist_ep[b->ep_square <= 63 ? b->ep_square : 64];
    if (b->side_to_move == BLACK) key ^= zobrist_side;
    return key;
}

// Square attacked query
static bool is_square_attacked(const NativeBoard* b, int sq, int attacker_color) {
    uint64_t occ = b->occupancy[2];
    int defender_color = 1 - attacker_color;

    if (pawn_attacks[defender_color][sq] & b->pieces[attacker_color][PAWN]) return true;
    if (knight_attacks[sq] & b->pieces[attacker_color][KNIGHT]) return true;
    if (king_attacks[sq] & b->pieces[attacker_color][KING]) return true;
    if (bishop_attacks_bb(sq, occ) & (b->pieces[attacker_color][BISHOP] | b->pieces[attacker_color][QUEEN])) return true;
    if (rook_attacks_bb(sq, occ) & (b->pieces[attacker_color][ROOK] | b->pieces[attacker_color][QUEEN])) return true;

    return false;
}

EXPORT int native_is_check(const NativeBoard* b) {
    int k_sq = bitscan_forward(b->pieces[b->side_to_move][KING]);
    return is_square_attacked(b, k_sq, 1 - b->side_to_move) ? 1 : 0;
}

// ============================================================================
// FEN Parsing and Export
// ============================================================================

EXPORT int native_init() {
    init_attacks();
    std::memset(g_tt, 0, sizeof(g_tt));
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    std::memset(g_history_table, 0, sizeof(g_history_table));
    g_game_history_len = 0;
    return 1;
}

EXPORT int native_set_fen(const char* fen, NativeBoard* out_b) {
    init_attacks();
    std::memset(out_b, 0, sizeof(NativeBoard));
    out_b->ep_square = 64;

    int r = 7, f = 0;
    int idx = 0;

    // 1. Piece placement
    while (fen[idx] && fen[idx] != ' ') {
        char c = fen[idx++];
        if (c == '/') {
            r--;
            f = 0;
            if (r < 0) return 0;
        } else if (c >= '1' && c <= '8') {
            f += (c - '0');
        } else {
            int color = (c >= 'a' && c <= 'z') ? BLACK : WHITE;
            char upper = (color == BLACK) ? (c - 32) : c;
            int piece = NO_PIECE;
            switch (upper) {
                case 'P': piece = PAWN; break;
                case 'N': piece = KNIGHT; break;
                case 'B': piece = BISHOP; break;
                case 'R': piece = ROOK; break;
                case 'Q': piece = QUEEN; break;
                case 'K': piece = KING; break;
                default: return 0; // Malformed char
            }
            if (f > 7 || r < 0) return 0;
            int sq = r * 8 + f;
            out_b->pieces[color][piece] |= (1ULL << sq);
            f++;
        }
    }

    // Validation: Exactly 1 king per side
    if (popcount64(out_b->pieces[WHITE][KING]) != 1 || popcount64(out_b->pieces[BLACK][KING]) != 1) {
        return 0;
    }

    out_b->occupancy[WHITE] = 0;
    out_b->occupancy[BLACK] = 0;
    for (int p = 0; p < 6; p++) {
        out_b->occupancy[WHITE] |= out_b->pieces[WHITE][p];
        out_b->occupancy[BLACK] |= out_b->pieces[BLACK][p];
    }
    out_b->occupancy[2] = out_b->occupancy[WHITE] | out_b->occupancy[BLACK];

    if (!fen[idx]) return 0;
    idx++; // Skip space

    // 2. Side to move
    if (fen[idx] == 'w') out_b->side_to_move = WHITE;
    else if (fen[idx] == 'b') out_b->side_to_move = BLACK;
    else return 0;
    idx++;

    if (!fen[idx]) return 0;
    idx++; // Skip space

    // 3. Castling rights
    out_b->castling_rights = 0;
    if (fen[idx] == '-') {
        idx++;
    } else {
        while (fen[idx] && fen[idx] != ' ') {
            if (fen[idx] == 'K') out_b->castling_rights |= CASTLE_W_OO;
            else if (fen[idx] == 'Q') out_b->castling_rights |= CASTLE_W_OOO;
            else if (fen[idx] == 'k') out_b->castling_rights |= CASTLE_B_OO;
            else if (fen[idx] == 'q') out_b->castling_rights |= CASTLE_B_OOO;
            idx++;
        }
    }

    if (!fen[idx]) return 0;
    idx++; // Skip space

    // 4. En passant square
    if (fen[idx] == '-') {
        out_b->ep_square = 64;
        idx++;
    } else {
        char f_char = fen[idx++];
        char r_char = fen[idx++];
        int ep_f = f_char - 'a';
        int ep_r = r_char - '1';
        if (ep_f >= 0 && ep_f <= 7 && (ep_r == 2 || ep_r == 5)) {
            out_b->ep_square = (uint8_t)(ep_r * 8 + ep_f);
        } else {
            return 0; // Malformed en passant square
        }
    }

    // 5. Halfmove clock
    out_b->halfmove_clock = 0;
    if (fen[idx] == ' ') {
        idx++;
        char* end;
        out_b->halfmove_clock = (uint16_t)std::strtol(fen + idx, &end, 10);
        idx = (int)(end - fen);
    }

    // 6. Fullmove number
    out_b->fullmove_number = 1;
    if (fen[idx] == ' ') {
        idx++;
        char* end;
        out_b->fullmove_number = (uint16_t)std::strtol(fen + idx, &end, 10);
    }

    out_b->zobrist_key = compute_zobrist(out_b);
    return 1;
}

EXPORT void native_get_fen(const NativeBoard* b, char* out_fen) {
    int idx = 0;
    const char piece_chars[2][6] = {
        { 'P', 'N', 'B', 'R', 'Q', 'K' },
        { 'p', 'n', 'b', 'r', 'q', 'k' }
    };

    for (int r = 7; r >= 0; r--) {
        int empty = 0;
        for (int f = 0; f < 8; f++) {
            int sq = r * 8 + f;
            int found_piece = NO_PIECE;
            int found_color = NO_COLOR;

            for (int c = 0; c < 2; c++) {
                for (int p = 0; p < 6; p++) {
                    if (b->pieces[c][p] & (1ULL << sq)) {
                        found_piece = p;
                        found_color = c;
                        break;
                    }
                }
                if (found_piece != NO_PIECE) break;
            }

            if (found_piece == NO_PIECE) {
                empty++;
            } else {
                if (empty > 0) {
                    out_fen[idx++] = '0' + empty;
                    empty = 0;
                }
                out_fen[idx++] = piece_chars[found_color][found_piece];
            }
        }
        if (empty > 0) out_fen[idx++] = '0' + empty;
        if (r > 0) out_fen[idx++] = '/';
    }

    out_fen[idx++] = ' ';
    out_fen[idx++] = (b->side_to_move == WHITE) ? 'w' : 'b';
    out_fen[idx++] = ' ';

    if (b->castling_rights == 0) {
        out_fen[idx++] = '-';
    } else {
        if (b->castling_rights & CASTLE_W_OO) out_fen[idx++] = 'K';
        if (b->castling_rights & CASTLE_W_OOO) out_fen[idx++] = 'Q';
        if (b->castling_rights & CASTLE_B_OO) out_fen[idx++] = 'k';
        if (b->castling_rights & CASTLE_B_OOO) out_fen[idx++] = 'q';
    }

    out_fen[idx++] = ' ';
    if (b->ep_square > 63) {
        out_fen[idx++] = '-';
    } else {
        out_fen[idx++] = 'a' + (b->ep_square % 8);
        out_fen[idx++] = '1' + (b->ep_square / 8);
    }

    std::sprintf(out_fen + idx, " %u %u", b->halfmove_clock, b->fullmove_number);
}

// ============================================================================
// State Transitions: Make / Unmake Move
// ============================================================================

EXPORT int native_make_move(NativeBoard* b, uint16_t m, UndoInfo* undo) {
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);

    int us = b->side_to_move;
    int them = 1 - us;

    undo->captured_piece = NO_PIECE;
    undo->castling_rights = b->castling_rights;
    undo->ep_square = b->ep_square;
    undo->halfmove_clock = b->halfmove_clock;
    undo->zobrist_key = b->zobrist_key;

    // Identify moving piece
    int piece = NO_PIECE;
    for (int p = 0; p < 6; p++) {
        if (b->pieces[us][p] & (1ULL << from)) {
            piece = p;
            break;
        }
    }
    if (piece == NO_PIECE) return 0; // Illegal: no piece on from sq

    // Identify captured piece
    if (flag == 2) { // En Passant
        undo->captured_piece = PAWN;
        int cap_sq = (us == WHITE) ? (to - 8) : (to + 8);
        b->pieces[them][PAWN] &= ~(1ULL << cap_sq);
        b->occupancy[them] &= ~(1ULL << cap_sq);
        b->zobrist_key ^= zobrist_pieces[them][PAWN][cap_sq];
    } else {
        for (int p = 0; p < 6; p++) {
            if (b->pieces[them][p] & (1ULL << to)) {
                undo->captured_piece = p;
                b->pieces[them][p] &= ~(1ULL << to);
                b->occupancy[them] &= ~(1ULL << to);
                b->zobrist_key ^= zobrist_pieces[them][p][to];
                break;
            }
        }
    }

    // Move piece from -> to
    b->pieces[us][piece] &= ~(1ULL << from);
    b->zobrist_key ^= zobrist_pieces[us][piece][from];

    int place_piece = piece;
    if (flag == 3) { // Promotion
        place_piece = promo + 1; // 0=N(1), 1=B(2), 2=R(3), 3=Q(4)
    }

    b->pieces[us][place_piece] |= (1ULL << to);
    b->zobrist_key ^= zobrist_pieces[us][place_piece][to];

    // Castling move: shift rook
    if (flag == 1) {
        if (to == 6) { // White O-O
            b->pieces[WHITE][ROOK] &= ~(1ULL << 7);
            b->pieces[WHITE][ROOK] |= (1ULL << 5);
            b->zobrist_key ^= zobrist_pieces[WHITE][ROOK][7] ^ zobrist_pieces[WHITE][ROOK][5];
        } else if (to == 2) { // White O-O-O
            b->pieces[WHITE][ROOK] &= ~(1ULL << 0);
            b->pieces[WHITE][ROOK] |= (1ULL << 3);
            b->zobrist_key ^= zobrist_pieces[WHITE][ROOK][0] ^ zobrist_pieces[WHITE][ROOK][3];
        } else if (to == 62) { // Black O-O
            b->pieces[BLACK][ROOK] &= ~(1ULL << 63);
            b->pieces[BLACK][ROOK] |= (1ULL << 61);
            b->zobrist_key ^= zobrist_pieces[BLACK][ROOK][63] ^ zobrist_pieces[BLACK][ROOK][61];
        } else if (to == 58) { // Black O-O-O
            b->pieces[BLACK][ROOK] &= ~(1ULL << 56);
            b->pieces[BLACK][ROOK] |= (1ULL << 59);
            b->zobrist_key ^= zobrist_pieces[BLACK][ROOK][56] ^ zobrist_pieces[BLACK][ROOK][59];
        }
    }

    // Rebuild occupancies
    b->occupancy[WHITE] = 0;
    b->occupancy[BLACK] = 0;
    for (int p = 0; p < 6; p++) {
        b->occupancy[WHITE] |= b->pieces[WHITE][p];
        b->occupancy[BLACK] |= b->pieces[BLACK][p];
    }
    b->occupancy[2] = b->occupancy[WHITE] | b->occupancy[BLACK];

    // Invalidate castling rights if king or rook moved / captured
    b->zobrist_key ^= zobrist_castling[b->castling_rights & 15];
    if (piece == KING) {
        if (us == WHITE) b->castling_rights &= ~(CASTLE_W_OO | CASTLE_W_OOO);
        else b->castling_rights &= ~(CASTLE_B_OO | CASTLE_B_OOO);
    }
    if (from == 0 || to == 0) b->castling_rights &= ~CASTLE_W_OOO;
    if (from == 7 || to == 7) b->castling_rights &= ~CASTLE_W_OO;
    if (from == 56 || to == 56) b->castling_rights &= ~CASTLE_B_OOO;
    if (from == 63 || to == 63) b->castling_rights &= ~CASTLE_B_OO;
    b->zobrist_key ^= zobrist_castling[b->castling_rights & 15];

    // Reset EP square in hash
    b->zobrist_key ^= zobrist_ep[b->ep_square <= 63 ? b->ep_square : 64];
    b->ep_square = 64;
    if (piece == PAWN && std::abs(to - from) == 16) {
        b->ep_square = (uint8_t)((from + to) / 2);
    }
    b->zobrist_key ^= zobrist_ep[b->ep_square <= 63 ? b->ep_square : 64];

    // Update halfmove clock
    b->halfmove_clock++;
    if (piece == PAWN || undo->captured_piece != NO_PIECE) {
        b->halfmove_clock = 0;
    }

    if (us == BLACK) b->fullmove_number++;
    b->side_to_move = them;
    b->zobrist_key ^= zobrist_side;

    return 1;
}

EXPORT void native_unmake_move(NativeBoard* b, uint16_t m, const UndoInfo* undo) {
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);

    int them = b->side_to_move;
    int us = 1 - them;

    b->side_to_move = us;
    if (us == BLACK) b->fullmove_number--;

    int placed_piece = NO_PIECE;
    if (flag == 3) {
        placed_piece = promo + 1;
    } else {
        for (int p = 0; p < 6; p++) {
            if (b->pieces[us][p] & (1ULL << to)) {
                placed_piece = p;
                break;
            }
        }
    }

    b->pieces[us][placed_piece] &= ~(1ULL << to);
    int orig_piece = (flag == 3) ? PAWN : placed_piece;
    b->pieces[us][orig_piece] |= (1ULL << from);

    // Restore captured piece
    if (flag == 2) { // En Passant
        int cap_sq = (us == WHITE) ? (to - 8) : (to + 8);
        b->pieces[them][PAWN] |= (1ULL << cap_sq);
    } else if (undo->captured_piece != NO_PIECE) {
        b->pieces[them][undo->captured_piece] |= (1ULL << to);
    }

    // Unmake castling move: restore rook
    if (flag == 1) {
        if (to == 6) {
            b->pieces[WHITE][ROOK] &= ~(1ULL << 5);
            b->pieces[WHITE][ROOK] |= (1ULL << 7);
        } else if (to == 2) {
            b->pieces[WHITE][ROOK] &= ~(1ULL << 3);
            b->pieces[WHITE][ROOK] |= (1ULL << 0);
        } else if (to == 62) {
            b->pieces[BLACK][ROOK] &= ~(1ULL << 61);
            b->pieces[BLACK][ROOK] |= (1ULL << 63);
        } else if (to == 58) {
            b->pieces[BLACK][ROOK] &= ~(1ULL << 59);
            b->pieces[BLACK][ROOK] |= (1ULL << 56);
        }
    }

    b->castling_rights = undo->castling_rights;
    b->ep_square = undo->ep_square;
    b->halfmove_clock = undo->halfmove_clock;
    b->zobrist_key = undo->zobrist_key;

    b->occupancy[WHITE] = 0;
    b->occupancy[BLACK] = 0;
    for (int p = 0; p < 6; p++) {
        b->occupancy[WHITE] |= b->pieces[WHITE][p];
        b->occupancy[BLACK] |= b->pieces[BLACK][p];
    }
    b->occupancy[2] = b->occupancy[WHITE] | b->occupancy[BLACK];
}

// ============================================================================
// Legal Move Generation
// ============================================================================

EXPORT int native_generate_legal_moves(NativeBoard* b, uint16_t* out_moves) {
    uint16_t pseudo_moves[MAX_MOVES];
    int p_count = 0;

    int us = b->side_to_move;
    int them = 1 - us;
    uint64_t occ = b->occupancy[2];
    uint64_t enemies = b->occupancy[them];
    uint64_t empty = ~occ;

    // 1. Pawn Moves
    uint64_t pawns = b->pieces[us][PAWN];
    int forward = (us == WHITE) ? 8 : -8;
    int start_rank = (us == WHITE) ? 1 : 6;
    int promo_rank = (us == WHITE) ? 7 : 0;

    while (pawns) {
        int sq = bitscan_forward(pawns);
        pawns &= pawns - 1;
        int r = sq / 8;

        // Single push
        int to = sq + forward;
        if (to >= 0 && to < 64 && !(occ & (1ULL << to))) {
            if (to / 8 == promo_rank) {
                for (int pr = 0; pr < 4; pr++) pseudo_moves[p_count++] = encode_move(sq, to, 3, pr);
            } else {
                pseudo_moves[p_count++] = encode_move(sq, to, 0);
                // Double push
                if (r == start_rank) {
                    int to2 = to + forward;
                    if (!(occ & (1ULL << to2))) {
                        pseudo_moves[p_count++] = encode_move(sq, to2, 0);
                    }
                }
            }
        }

        // Captures
        uint64_t att = pawn_attacks[us][sq];
        uint64_t caps = att & enemies;
        while (caps) {
            int cap_to = bitscan_forward(caps);
            caps &= caps - 1;
            if (cap_to / 8 == promo_rank) {
                for (int pr = 0; pr < 4; pr++) pseudo_moves[p_count++] = encode_move(sq, cap_to, 3, pr);
            } else {
                pseudo_moves[p_count++] = encode_move(sq, cap_to, 0);
            }
        }

        // En Passant
        if (b->ep_square <= 63 && (att & (1ULL << b->ep_square))) {
            pseudo_moves[p_count++] = encode_move(sq, b->ep_square, 2);
        }
    }

    // 2. Knights
    uint64_t knights = b->pieces[us][KNIGHT];
    while (knights) {
        int sq = bitscan_forward(knights);
        knights &= knights - 1;
        uint64_t att = knight_attacks[sq] & ~b->occupancy[us];
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 3. Bishops / Queens diagonal
    uint64_t diags = b->pieces[us][BISHOP] | b->pieces[us][QUEEN];
    while (diags) {
        int sq = bitscan_forward(diags);
        diags &= diags - 1;
        uint64_t att = bishop_attacks_bb(sq, occ) & ~b->occupancy[us];
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 4. Rooks / Queens straight
    uint64_t straights = b->pieces[us][ROOK] | b->pieces[us][QUEEN];
    while (straights) {
        int sq = bitscan_forward(straights);
        straights &= straights - 1;
        uint64_t att = rook_attacks_bb(sq, occ) & ~b->occupancy[us];
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 5. King
    int k_sq = bitscan_forward(b->pieces[us][KING]);
    uint64_t k_att = king_attacks[k_sq] & ~b->occupancy[us];
    while (k_att) {
        int to = bitscan_forward(k_att);
        k_att &= k_att - 1;
        pseudo_moves[p_count++] = encode_move(k_sq, to);
    }

    // 6. Castling
    if (us == WHITE) {
        if ((b->castling_rights & CASTLE_W_OO) && !(occ & (1ULL << 5)) && !(occ & (1ULL << 6))) {
            if (!is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 5, BLACK) && !is_square_attacked(b, 6, BLACK)) {
                pseudo_moves[p_count++] = encode_move(4, 6, 1);
            }
        }
        if ((b->castling_rights & CASTLE_W_OOO) && !(occ & (1ULL << 1)) && !(occ & (1ULL << 2)) && !(occ & (1ULL << 3))) {
            if (!is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 3, BLACK) && !is_square_attacked(b, 2, BLACK)) {
                pseudo_moves[p_count++] = encode_move(4, 2, 1);
            }
        }
    } else {
        if ((b->castling_rights & CASTLE_B_OO) && !(occ & (1ULL << 61)) && !(occ & (1ULL << 62))) {
            if (!is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 61, WHITE) && !is_square_attacked(b, 62, WHITE)) {
                pseudo_moves[p_count++] = encode_move(60, 62, 1);
            }
        }
        if ((b->castling_rights & CASTLE_B_OOO) && !(occ & (1ULL << 57)) && !(occ & (1ULL << 58)) && !(occ & (1ULL << 59))) {
            if (!is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 59, WHITE) && !is_square_attacked(b, 58, WHITE)) {
                pseudo_moves[p_count++] = encode_move(60, 58, 1);
            }
        }
    }

    // 7. Legality filter (ensure moving king is not in check)
    int legal_count = 0;
    UndoInfo undo;
    for (int i = 0; i < p_count; i++) {
        uint16_t m = pseudo_moves[i];
        if (!native_make_move(b, m, &undo)) continue;

        int king_sq = bitscan_forward(b->pieces[us][KING]);
        bool in_check = is_square_attacked(b, king_sq, them);
        native_unmake_move(b, m, &undo);

        if (!in_check) {
            out_moves[legal_count++] = m;
        }
    }

    return legal_count;
}

// Perft function for qualification
EXPORT uint64_t native_perft(NativeBoard* b, int depth) {
    if (depth <= 0) return 1ULL;

    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);
    if (depth == 1) return (uint64_t)n;

    uint64_t nodes = 0;
    UndoInfo undo;
    for (int i = 0; i < n; i++) {
        native_make_move(b, moves[i], &undo);
        nodes += native_perft(b, depth - 1);
        native_unmake_move(b, moves[i], &undo);
    }
    return nodes;
}

// ============================================================================
// FIDE Draw Semantics & Repetition Implementation (Phase B)
// ============================================================================

EXPORT void native_reset_history() {
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
}

EXPORT void native_pop_history() {
    if (g_game_history_len > 0) {
        g_game_history_len--;
    }
}

EXPORT int native_get_history_len() {
    return g_game_history_len;
}

EXPORT uint64_t native_get_history_key(int idx) {
    if (idx >= 0 && idx < g_game_history_len) {
        return g_game_history[idx];
    }
    return 0;
}

// Count occurrences of position b in history (including current)
static int count_repetition_occurrences(const NativeBoard* b) {
    uint64_t target_key = b->zobrist_key;
    int count = 0;

    // In chess, repetition can only occur back to the last irreversible move
    int lookback = std::min(g_game_history_len, (int)b->halfmove_clock + 1);
    for (int i = g_game_history_len - 1; i >= g_game_history_len - lookback; i--) {
        if (i >= 0 && g_game_history[i] == target_key) {
            count++;
        }
    }

    // If current board is not yet in history (e.g. before push_history), count current
    if (g_game_history_len == 0 || g_game_history[g_game_history_len - 1] != target_key) {
        count++;
    }

    return count;
}

EXPORT int native_is_repetition(const NativeBoard* b, int required_count) {
    return (count_repetition_occurrences(b) >= required_count) ? 1 : 0;
}

EXPORT int native_is_fivefold_repetition(const NativeBoard* b) {
    return (count_repetition_occurrences(b) >= 5) ? 1 : 0;
}

EXPORT int native_can_claim_threefold_repetition(NativeBoard* b) {
    // 1. Current position already occurred >= 3 times
    if (count_repetition_occurrences(b) >= 3) return 1;

    // 2. Intended move: player has a legal move that brings about the 3rd occurrence
    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);
    UndoInfo undo;

    for (int i = 0; i < n; i++) {
        native_make_move(b, moves[i], &undo);
        int child_count = count_repetition_occurrences(b);
        native_unmake_move(b, moves[i], &undo);

        if (child_count >= 3) {
            return 1;
        }
    }
    return 0;
}

EXPORT int native_can_claim_fifty_moves(NativeBoard* b) {
    if (b->halfmove_clock >= 100) return 1;

    // Intended move: if halfmove_clock == 99, any legal non-capture non-pawn move produces 100
    if (b->halfmove_clock >= 99) {
        uint16_t moves[MAX_MOVES];
        int n = native_generate_legal_moves(b, moves);
        UndoInfo undo;
        for (int i = 0; i < n; i++) {
            native_make_move(b, moves[i], &undo);
            int child_hmc = b->halfmove_clock;
            native_unmake_move(b, moves[i], &undo);
            if (child_hmc >= 100) return 1;
        }
    }
    return 0;
}

EXPORT int native_is_seventyfive_moves(const NativeBoard* b) {
    return (b->halfmove_clock >= 150) ? 1 : 0;
}

EXPORT int native_is_insufficient_material(const NativeBoard* b) {
    // If pawns, rooks, or queens exist, checkmate is possible
    if (b->pieces[WHITE][PAWN] || b->pieces[BLACK][PAWN] ||
        b->pieces[WHITE][ROOK] || b->pieces[BLACK][ROOK] ||
        b->pieces[WHITE][QUEEN] || b->pieces[BLACK][QUEEN]) {
        return 0;
    }

    int w_knights = popcount64(b->pieces[WHITE][KNIGHT]);
    int b_knights = popcount64(b->pieces[BLACK][KNIGHT]);
    int w_bishops = popcount64(b->pieces[WHITE][BISHOP]);
    int b_bishops = popcount64(b->pieces[BLACK][BISHOP]);

    // Bare kings (K vs K)
    if (w_knights + b_knights + w_bishops + b_bishops == 0) return 1;

    // King + minor vs King (K+N vs K, K+B vs K)
    if (w_knights + w_bishops == 1 && b_knights + b_bishops == 0) return 1;
    if (b_knights + b_bishops == 1 && w_knights + w_bishops == 0) return 1;

    // King + Bishop vs King + Bishop on the same color
    if (w_knights == 0 && b_knights == 0 && w_bishops == 1 && b_bishops == 1) {
        constexpr uint64_t DARK_SQUARES = 0xAA55AA55AA55AA55ULL;
        bool w_dark = (b->pieces[WHITE][BISHOP] & DARK_SQUARES) != 0;
        bool b_dark = (b->pieces[BLACK][BISHOP] & DARK_SQUARES) != 0;
        if (w_dark == b_dark) return 1; // Same square color: automatic draw
    }

    return 0;
}

EXPORT int native_is_claimable_draw(NativeBoard* b) {
    return (native_can_claim_threefold_repetition(b) || native_can_claim_fifty_moves(b)) ? 1 : 0;
}

EXPORT int native_is_automatic_draw(const NativeBoard* b) {
    return (native_is_fivefold_repetition(b) || native_is_seventyfive_moves(b) || native_is_insufficient_material(b)) ? 1 : 0;
}

// ============================================================================
// Static Evaluation Function (Matching Python Janus Baseline)
// ============================================================================

static const int MG_PIECE_VALUES[6] = { 100, 320, 330, 500, 900, 20000 };
static const int EG_PIECE_VALUES[6] = { 100, 320, 330, 500, 900, 20000 };

static const int MG_PAWN_TABLE[64] = {
      0,   0,   0,   0,   0,   0,   0,   0,
     50,  50,  50,  50,  50,  50,  50,  50,
     10,  10,  20,  30,  30,  20,  10,  10,
      5,   5,  10,  25,  25,  10,   5,   5,
      0,   0,   0,  20,  20,   0,   0,   0,
      5,  -5, -10,   0,   0, -10,  -5,   5,
      5,  10,  10, -20, -20,  10,  10,   5,
      0,   0,   0,   0,   0,   0,   0,   0
};

static const int MG_KNIGHT_TABLE[64] = {
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50
};

static const int MG_BISHOP_TABLE[64] = {
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20
};

static const int MG_ROOK_TABLE[64] = {
      0,   0,   0,   0,   0,   0,   0,   0,
      5,  10,  10,  10,  10,  10,  10,   5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
      0,   0,   0,   5,   5,   0,   0,   0
};

static const int MG_QUEEN_TABLE[64] = {
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,   5,   5,   5,   0, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,  -5,
    -10,   5,   5,   5,   5,   5,   0, -10,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20
};

static const int MG_KING_TABLE[64] = {
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20
};

static inline int mirror_sq(int sq) {
    return (7 - (sq / 8)) * 8 + (sq % 8);
}

// ============================================================================
// Handcrafted Positional Evaluation Modules (Milestone P1.2)
// Strictly Non-ML Handcrafted Terms with Middle-Game and Endgame Tapering
// ============================================================================

constexpr uint64_t FILE_A_MASK = 0x0101010101010101ULL;
constexpr uint64_t FILE_MASKS[8] = {
    FILE_A_MASK, FILE_A_MASK << 1, FILE_A_MASK << 2, FILE_A_MASK << 3,
    FILE_A_MASK << 4, FILE_A_MASK << 5, FILE_A_MASK << 6, FILE_A_MASK << 7
};

constexpr uint64_t RANK_1_MASK = 0x00000000000000FFULL;

// ============================================================================
// Phase 4: Pawn Hash Table Architecture (P1.5)
// ============================================================================
struct PawnHashEntry {
    uint64_t key;
    int16_t mg[2];
    int16_t eg[2];
    uint64_t passed_pawns[2];
};
constexpr size_t PAWN_HASH_SIZE = 65536; // 64K entries * 32 bytes = 2.0 MB (L3 resident)
thread_local PawnHashEntry g_pawn_table[PAWN_HASH_SIZE];

static void clear_pawn_table() {
    std::memset(g_pawn_table, 0, sizeof(g_pawn_table));
}

static inline uint64_t compute_pawn_zobrist(const NativeBoard* b) {
    uint64_t key = 0;
    uint64_t wp = b->pieces[WHITE][PAWN];
    while (wp) {
        int sq = bitscan_forward(wp);
        wp &= wp - 1;
        key ^= zobrist_pieces[WHITE][PAWN][sq];
    }
    uint64_t bp = b->pieces[BLACK][PAWN];
    while (bp) {
        int sq = bitscan_forward(bp);
        bp &= bp - 1;
        key ^= zobrist_pieces[BLACK][PAWN][sq];
    }
    return key;
}

constexpr uint64_t RANK_MASKS[8] = {
    RANK_1_MASK, RANK_1_MASK << 8, RANK_1_MASK << 16, RANK_1_MASK << 24,
    RANK_1_MASK << 32, RANK_1_MASK << 40, RANK_1_MASK << 48, RANK_1_MASK << 56
};

inline uint64_t adjacent_files_mask(int f) {
    uint64_t m = 0;
    if (f > 0) m |= FILE_MASKS[f - 1];
    if (f < 7) m |= FILE_MASKS[f + 1];
    return m;
}

static const int PASSED_PAWN_BONUS_MG[8] = { 0, 5, 10, 20, 35, 60, 100, 0 };
static const int PASSED_PAWN_BONUS_EG[8] = { 0, 10, 20, 35, 60, 100, 150, 0 };

static void eval_pawn_structure(const NativeBoard* b, int mg[2], int eg[2]) {
    for (int c = 0; c < 2; c++) {
        uint64_t my_pawns = b->pieces[c][PAWN];
        uint64_t enemy_pawns = b->pieces[1 - c][PAWN];

        // 1. Passed Pawns
        uint64_t p = my_pawns;
        while (p) {
            int sq = bitscan_forward(p);
            p &= p - 1;
            int f = sq % 8;
            int r = (c == WHITE) ? (sq / 8) : (7 - (sq / 8));
            bool is_passed = (c == WHITE) ? ((enemy_pawns & white_passed_pawn_mask[sq]) == 0)
                                          : ((enemy_pawns & black_passed_pawn_mask[sq]) == 0);
            if (is_passed) {
                mg[c] += PASSED_PAWN_BONUS_MG[r];
                eg[c] += PASSED_PAWN_BONUS_EG[r];

                // Connected passer bonus: friendly pawn on adjacent file within +/- 1 rank
                uint64_t adj = my_pawns & adjacent_files_mask(f);
                int act_r = sq / 8;
                uint64_t near_ranks = RANK_MASKS[act_r] | (act_r > 0 ? RANK_MASKS[act_r - 1] : 0) | (act_r < 7 ? RANK_MASKS[act_r + 1] : 0);
                if (adj & near_ranks) {
                    mg[c] += 15;
                    eg[c] += 25;
                }

                // Supported passer bonus
                uint64_t defenders = (c == WHITE) ? pawn_attacks[BLACK][sq] : pawn_attacks[WHITE][sq];
                if (defenders & my_pawns) {
                    mg[c] += 10;
                    eg[c] += 20;
                }
            }
        }

        // 2. Isolated & Doubled Pawns
        for (int f = 0; f < 8; f++) {
            uint64_t f_pawns = my_pawns & FILE_MASKS[f];
            if (f_pawns) {
                // Isolated
                if ((my_pawns & adjacent_files_mask(f)) == 0) {
                    mg[c] -= 12;
                    eg[c] -= 20;
                }
                // Doubled
                int cnt = popcount64(f_pawns);
                if (cnt > 1) {
                    mg[c] -= 15 * (cnt - 1);
                    eg[c] -= 25 * (cnt - 1);
                }
            }
        }
    }
}

static void eval_mobility_and_coordination(const NativeBoard* b, int mg[2], int eg[2]) {
    for (int c = 0; c < 2; c++) {
        // Bishop pair
        if (popcount64(b->pieces[c][BISHOP]) >= 2) {
            mg[c] += 30;
            eg[c] += 50;
        }

        // Rooks on open & semi-open files, 7th rank
        uint64_t rooks = b->pieces[c][ROOK];
        int seventh = (c == WHITE) ? 6 : 1;
        while (rooks) {
            int sq = bitscan_forward(rooks);
            rooks &= rooks - 1;
            int f = sq % 8;
            int r = sq / 8;
            bool my_p = (b->pieces[c][PAWN] & FILE_MASKS[f]) != 0;
            bool en_p = (b->pieces[1 - c][PAWN] & FILE_MASKS[f]) != 0;
            if (!my_p && !en_p) {
                mg[c] += 20; eg[c] += 25;
            } else if (!my_p && en_p) {
                mg[c] += 10; eg[c] += 15;
            }
            if (r == seventh) {
                mg[c] += 20; eg[c] += 35;
            }
        }

        // Knight outposts
        uint64_t knights = b->pieces[c][KNIGHT];
        while (knights) {
            int sq = bitscan_forward(knights);
            knights &= knights - 1;
            int r = (c == WHITE) ? (sq / 8) : (7 - (sq / 8));
            if (r >= 3 && r <= 5) {
                uint64_t def = (c == WHITE) ? pawn_attacks[BLACK][sq] : pawn_attacks[WHITE][sq];
                if (def & b->pieces[c][PAWN]) {
                    mg[c] += 15; eg[c] += 10;
                }
            }
        }

        // Safe Mobility
        uint64_t enemy_pawn_attacks_bb = 0;
        uint64_t ep = b->pieces[1 - c][PAWN];
        while (ep) {
            int sq = bitscan_forward(ep);
            ep &= ep - 1;
            enemy_pawn_attacks_bb |= pawn_attacks[1 - c][sq];
        }
        uint64_t safe_mask = ~(b->occupancy[c] | enemy_pawn_attacks_bb);

        // Knights
        uint64_t kn = b->pieces[c][KNIGHT];
        while (kn) {
            int sq = bitscan_forward(kn);
            kn &= kn - 1;
            int mob = popcount64(knight_attacks[sq] & safe_mask);
            mg[c] += (mob - 4) * 4;
            eg[c] += (mob - 4) * 4;
        }
        // Bishops
        uint64_t bi = b->pieces[c][BISHOP];
        while (bi) {
            int sq = bitscan_forward(bi);
            bi &= bi - 1;
            int mob = popcount64(bishop_attacks_bb(sq, b->occupancy[2]) & safe_mask);
            mg[c] += (mob - 7) * 4;
            eg[c] += (mob - 7) * 4;
        }
        // Rooks
        uint64_t ro = b->pieces[c][ROOK];
        while (ro) {
            int sq = bitscan_forward(ro);
            ro &= ro - 1;
            int mob = popcount64(rook_attacks_bb(sq, b->occupancy[2]) & safe_mask);
            mg[c] += (mob - 7) * 2;
            eg[c] += (mob - 7) * 2;
        }
    }
}

static void eval_king_safety(const NativeBoard* b, int mg[2], int eg[2]) {
    for (int c = 0; c < 2; c++) {
        uint64_t kbb = b->pieces[c][KING];
        if (!kbb) continue;
        int ksq = bitscan_forward(kbb);
        int kf = ksq % 8;
        int kr = ksq / 8;

        // Pawn shield
        int shield_missing = 0;
        for (int f = std::max(0, kf - 1); f <= std::min(7, kf + 1); f++) {
            uint64_t f_pawns = b->pieces[c][PAWN] & FILE_MASKS[f];
            if (!f_pawns) {
                shield_missing++;
            } else {
                if (c == WHITE) {
                    int psq = bitscan_forward(f_pawns);
                    if (psq / 8 > kr + 2) shield_missing++;
                } else {
                    int psq = bitscan_reverse(f_pawns);
                    if (psq / 8 < kr - 2) shield_missing++;
                }
            }
        }
        mg[c] -= shield_missing * 15;

        // King ring enemy attackers
        uint64_t king_ring = king_attacks[ksq];
        int them = 1 - c;
        int attack_units = 0;
        int attackers = 0;

        uint64_t att_kn = b->pieces[them][KNIGHT];
        while (att_kn) {
            int sq = bitscan_forward(att_kn);
            att_kn &= att_kn - 1;
            if (knight_attacks[sq] & king_ring) { attack_units += 2; attackers++; }
        }
        uint64_t att_bi = b->pieces[them][BISHOP];
        while (att_bi) {
            int sq = bitscan_forward(att_bi);
            att_bi &= att_bi - 1;
            if (bishop_attacks_bb(sq, b->occupancy[2]) & king_ring) { attack_units += 2; attackers++; }
        }
        uint64_t att_ro = b->pieces[them][ROOK];
        while (att_ro) {
            int sq = bitscan_forward(att_ro);
            att_ro &= att_ro - 1;
            if (rook_attacks_bb(sq, b->occupancy[2]) & king_ring) { attack_units += 3; attackers++; }
        }
        uint64_t att_qu = b->pieces[them][QUEEN];
        while (att_qu) {
            int sq = bitscan_forward(att_qu);
            att_qu &= att_qu - 1;
            if (queen_attacks_bb(sq, b->occupancy[2]) & king_ring) { attack_units += 5; attackers++; }
        }
        if (attackers >= 2) {
            int danger = attack_units * attack_units;
            mg[c] -= std::min(200, danger * 2);
        }
    }
}

static void eval_endgame_positional(const NativeBoard* b, int mg[2], int eg[2]) {
    uint64_t kw = b->pieces[WHITE][KING];
    uint64_t kb = b->pieces[BLACK][KING];
    if (!kw || !kb) return;
    int w_ksq = bitscan_forward(kw);
    int b_ksq = bitscan_forward(kb);

    for (int c = 0; c < 2; c++) {
        int my_ksq = (c == WHITE) ? w_ksq : b_ksq;
        int en_ksq = (c == WHITE) ? b_ksq : w_ksq;
        int kr = my_ksq / 8;
        int kf = my_ksq % 8;
        int en_kr = en_ksq / 8;
        int en_kf = en_ksq % 8;

        // King centralization
        int center_dist = std::abs(2 * kr - 7) + std::abs(2 * kf - 7);
        eg[c] += (14 - center_dist) * 2;

        // Passed pawn escort
        uint64_t pawns = b->pieces[c][PAWN];
        uint64_t en_pawns = b->pieces[1 - c][PAWN];
        while (pawns) {
            int psq = bitscan_forward(pawns);
            pawns &= pawns - 1;
            bool is_passed = (c == WHITE) ? ((en_pawns & white_passed_pawn_mask[psq]) == 0)
                                          : ((en_pawns & black_passed_pawn_mask[psq]) == 0);
            if (is_passed) {
                int pr = psq / 8;
                int pf = psq % 8;
                int my_dist = std::max(std::abs(kr - pr), std::abs(kf - pf));
                int en_dist = std::max(std::abs(en_kr - pr), std::abs(en_kf - pf));
                eg[c] += (en_dist - my_dist) * 6;
            }
        }
    }
}


// ============================================================================
// Phase 3: Enhanced Classical Evaluation Modules (Milestone P1.5 - E1'..E5')
// Strictly Non-ML Handcrafted Terms
// ============================================================================

static void eval_pawn_structure_v2(const NativeBoard* b, int mg[2], int eg[2], uint64_t passed_bb[2]) {
    passed_bb[WHITE] = 0;
    passed_bb[BLACK] = 0;

    for (int c = 0; c < 2; c++) {
        uint64_t my_pawns = b->pieces[c][PAWN];
        uint64_t enemy_pawns = b->pieces[1 - c][PAWN];

        // 1. Passed Pawns & Candidate Passers
        uint64_t p = my_pawns;
        while (p) {
            int sq = bitscan_forward(p);
            p &= p - 1;
            int f = sq % 8;
            int r = (c == WHITE) ? (sq / 8) : (7 - (sq / 8));
            bool is_passed = (c == WHITE) ? ((enemy_pawns & white_passed_pawn_mask[sq]) == 0)
                                          : ((enemy_pawns & black_passed_pawn_mask[sq]) == 0);
            if (is_passed) {
                passed_bb[c] |= (1ULL << sq);
                mg[c] += PASSED_PAWN_BONUS_MG[r];
                eg[c] += PASSED_PAWN_BONUS_EG[r];

                // Connected passer bonus
                uint64_t adj = my_pawns & adjacent_files_mask(f);
                int act_r = sq / 8;
                uint64_t near_ranks = RANK_MASKS[act_r] | (act_r > 0 ? RANK_MASKS[act_r - 1] : 0) | (act_r < 7 ? RANK_MASKS[act_r + 1] : 0);
                if (adj & near_ranks) {
                    mg[c] += 15; eg[c] += 25;
                }

                // Supported passer bonus (defended by friendly pawn)
                uint64_t defenders = (c == WHITE) ? pawn_attacks[BLACK][sq] : pawn_attacks[WHITE][sq];
                if (defenders & my_pawns) {
                    mg[c] += 15; eg[c] += 25;
                }
            } else {
                // Candidate passed pawn: no enemy pawn directly ahead, and friendly support >= enemy opposition
                uint64_t front_span = (c == WHITE) ? (FILE_MASKS[f] & ~((1ULL << (sq + 1)) - 1))
                                                    : (FILE_MASKS[f] & ((1ULL << sq) - 1));
                if ((enemy_pawns & front_span) == 0 && r >= 3) {
                    uint64_t adj_my = my_pawns & adjacent_files_mask(f);
                    uint64_t adj_en = enemy_pawns & adjacent_files_mask(f);
                    if (popcount64(adj_my) >= popcount64(adj_en)) {
                        mg[c] += PASSED_PAWN_BONUS_MG[r] / 2;
                        eg[c] += PASSED_PAWN_BONUS_EG[r] / 2;
                    }
                }
            }
        }

        // 2. Isolated, Doubled, and Backward Pawns
        int occupied_files = 0;
        for (int f = 0; f < 8; f++) {
            uint64_t f_pawns = my_pawns & FILE_MASKS[f];
            if (f_pawns) {
                occupied_files |= (1 << f);

                // Isolated pawn
                if ((my_pawns & adjacent_files_mask(f)) == 0) {
                    mg[c] -= 12; eg[c] -= 20;
                }
                // Doubled pawn
                int cnt = popcount64(f_pawns);
                if (cnt > 1) {
                    mg[c] -= 15 * (cnt - 1);
                    eg[c] -= 25 * (cnt - 1);
                }

                // Backward pawn
                int base_sq = (c == WHITE) ? bitscan_forward(f_pawns) : bitscan_reverse(f_pawns);
                int base_r = base_sq / 8;
                int stop_sq = (c == WHITE) ? (base_sq + 8) : (base_sq - 8);
                if (stop_sq >= 0 && stop_sq < 64) {
                    uint64_t stop_attackers = (c == WHITE) ? pawn_attacks[WHITE][stop_sq] : pawn_attacks[BLACK][stop_sq];
                    if (stop_attackers & enemy_pawns) {
                        uint64_t friendly_adj = my_pawns & adjacent_files_mask(f);
                        bool has_supporter_behind = false;
                        while (friendly_adj) {
                            int asq = bitscan_forward(friendly_adj);
                            friendly_adj &= friendly_adj - 1;
                            int ar = asq / 8;
                            if ((c == WHITE && ar <= base_r) || (c == BLACK && ar >= base_r)) {
                                has_supporter_behind = true;
                                break;
                            }
                        }
                        if (!has_supporter_behind) {
                            mg[c] -= 10; eg[c] -= 15;
                        }
                    }
                }
            }
        }

        // 3. Pawn Islands
        int islands = 0;
        bool in_island = false;
        for (int f = 0; f < 8; f++) {
            if (occupied_files & (1 << f)) {
                if (!in_island) { islands++; in_island = true; }
            } else {
                in_island = false;
            }
        }
        if (islands > 1) {
            mg[c] -= (islands - 1) * 8;
            eg[c] -= (islands - 1) * 12;
        }
    }
}

static void eval_king_safety_v2(const NativeBoard* b, int mg[2], int eg[2]) {
    for (int c = 0; c < 2; c++) {
        uint64_t kbb = b->pieces[c][KING];
        if (!kbb) continue;
        int ksq = bitscan_forward(kbb);
        int kf = ksq % 8;
        int kr = ksq / 8;
        int them = 1 - c;

        int enemy_queens = popcount64(b->pieces[them][QUEEN]);

        // Pawn shield
        int shield_missing = 0;
        for (int f = std::max(0, kf - 1); f <= std::min(7, kf + 1); f++) {
            uint64_t f_pawns = b->pieces[c][PAWN] & FILE_MASKS[f];
            if (!f_pawns) {
                shield_missing++;
            } else {
                if (c == WHITE) {
                    int psq = bitscan_forward(f_pawns);
                    if (psq / 8 > kr + 2) shield_missing++;
                } else {
                    int psq = bitscan_reverse(f_pawns);
                    if (psq / 8 < kr - 2) shield_missing++;
                }
            }
        }
        // Scale shield penalty by enemy queen presence
        int shield_penalty = (enemy_queens > 0) ? (shield_missing * 15) : (shield_missing * 5);
        mg[c] -= shield_penalty;

        // King ring enemy attackers (Only if enemy has queen or multiple heavy pieces)
        if (enemy_queens > 0) {
            uint64_t king_ring = king_attacks[ksq];
            int attack_units = 0;
            int attackers = 0;

            uint64_t att_kn = b->pieces[them][KNIGHT];
            while (att_kn) {
                int sq = bitscan_forward(att_kn);
                att_kn &= att_kn - 1;
                if (knight_attacks[sq] & king_ring) { attack_units += 2; attackers++; }
            }
            uint64_t att_bi = b->pieces[them][BISHOP];
            while (att_bi) {
                int sq = bitscan_forward(att_bi);
                att_bi &= att_bi - 1;
                if (bishop_attacks_bb(sq, b->occupancy[2]) & king_ring) { attack_units += 2; attackers++; }
            }
            uint64_t att_ro = b->pieces[them][ROOK];
            while (att_ro) {
                int sq = bitscan_forward(att_ro);
                att_ro &= att_ro - 1;
                if (rook_attacks_bb(sq, b->occupancy[2]) & king_ring) { attack_units += 3; attackers++; }
            }
            uint64_t att_qu = b->pieces[them][QUEEN];
            while (att_qu) {
                int sq = bitscan_forward(att_qu);
                att_qu &= att_qu - 1;
                if (queen_attacks_bb(sq, b->occupancy[2]) & king_ring) { attack_units += 5; attackers++; }
            }
            if (attackers >= 2) {
                int danger = attack_units * attack_units;
                mg[c] -= std::min(200, danger * 2);
            }
        }

        // Enemy Pawn Storms
        if (kf <= 2 || kf >= 5) {
            uint64_t storm_pawns = b->pieces[them][PAWN];
            for (int f = std::max(0, kf - 1); f <= std::min(7, kf + 1); f++) {
                uint64_t f_storm = storm_pawns & FILE_MASKS[f];
                while (f_storm) {
                    int psq = bitscan_forward(f_storm);
                    f_storm &= f_storm - 1;
                    int pr = (them == WHITE) ? (psq / 8) : (7 - (psq / 8));
                    if (pr >= 3) {
                        mg[c] -= (pr - 2) * 8; // Storm penalty
                    }
                }
            }
        }
    }
}

static void eval_mobility_and_coordination_v2(const NativeBoard* b, int mg[2], int eg[2], const uint64_t passed_bb[2]) {
    constexpr uint64_t LIGHT_SQ_MASK = 0x55AA55AA55AA55AAULL;
    constexpr uint64_t DARK_SQ_MASK  = 0xAA55AA55AA55AA55ULL;

    for (int c = 0; c < 2; c++) {
        uint64_t bishops = b->pieces[c][BISHOP];
        // Color-separated bishop pair
        if ((bishops & LIGHT_SQ_MASK) && (bishops & DARK_SQ_MASK)) {
            mg[c] += 35; eg[c] += 55;
        }

        // Rooks: open/semi-open files, 7th rank, connected rooks, Tarrasch rule
        uint64_t rooks = b->pieces[c][ROOK];
        int seventh = (c == WHITE) ? 6 : 1;
        int rook_files[2] = { -1, -1 };
        int r_idx = 0;

        while (rooks) {
            int sq = bitscan_forward(rooks);
            rooks &= rooks - 1;
            int f = sq % 8;
            int r = sq / 8;
            if (r_idx < 2) rook_files[r_idx++] = f;

            bool my_p = (b->pieces[c][PAWN] & FILE_MASKS[f]) != 0;
            bool en_p = (b->pieces[1 - c][PAWN] & FILE_MASKS[f]) != 0;
            if (!my_p && !en_p) {
                mg[c] += 20; eg[c] += 25;
            } else if (!my_p && en_p) {
                mg[c] += 10; eg[c] += 15;
            }
            if (r == seventh) {
                mg[c] += 20; eg[c] += 35;
            }

            // Tarrasch rule: rook behind passed pawn
            uint64_t file_passers = passed_bb[c] & FILE_MASKS[f];
            if (file_passers) {
                int psq = bitscan_forward(file_passers);
                if ((c == WHITE && r < psq / 8) || (c == BLACK && r > psq / 8)) {
                    mg[c] += 20; eg[c] += 30; // Behind friendly passer
                }
            }
            uint64_t en_file_passers = passed_bb[1 - c] & FILE_MASKS[f];
            if (en_file_passers) {
                int psq = bitscan_forward(en_file_passers);
                if ((c == WHITE && r < psq / 8) || (c == BLACK && r > psq / 8)) {
                    mg[c] += 15; eg[c] += 25; // Behind enemy passer (blockade)
                }
            }
        }

        // Connected rooks
        if (r_idx == 2 && rook_files[0] == rook_files[1]) {
            mg[c] += 15; eg[c] += 15;
        }

        // True Knight Outposts (immune to enemy pawn kick)
        uint64_t knights = b->pieces[c][KNIGHT];
        while (knights) {
            int sq = bitscan_forward(knights);
            knights &= knights - 1;
            int r = (c == WHITE) ? (sq / 8) : (7 - (sq / 8));
            int f = sq % 8;
            if (r >= 3 && r <= 5) {
                uint64_t def = (c == WHITE) ? pawn_attacks[BLACK][sq] : pawn_attacks[WHITE][sq];
                if (def & b->pieces[c][PAWN]) {
                    // Check if kickable by enemy pawn
                    bool kickable = false;
                    for (int af : { f - 1, f + 1 }) {
                        if (af >= 0 && af <= 7) {
                            uint64_t en_pawns = b->pieces[1 - c][PAWN] & FILE_MASKS[af];
                            while (en_pawns) {
                                int esq = bitscan_forward(en_pawns);
                                en_pawns &= en_pawns - 1;
                                int er = (c == WHITE) ? (esq / 8) : (7 - (esq / 8));
                                if (er >= r) { kickable = true; break; }
                            }
                        }
                    }
                    if (!kickable) {
                        mg[c] += 25; eg[c] += 15; // True immune outpost
                    } else {
                        mg[c] += 10; eg[c] += 5;  // Temporary outpost
                    }
                }
            }
        }

        // Safe Mobility for Knights, Bishops, Rooks, and Queens
        uint64_t enemy_pawn_attacks_bb = 0;
        uint64_t ep = b->pieces[1 - c][PAWN];
        while (ep) {
            int sq = bitscan_forward(ep);
            ep &= ep - 1;
            enemy_pawn_attacks_bb |= pawn_attacks[1 - c][sq];
        }
        uint64_t safe_mask = ~(b->occupancy[c] | enemy_pawn_attacks_bb);

        uint64_t kn = b->pieces[c][KNIGHT];
        while (kn) {
            int sq = bitscan_forward(kn);
            kn &= kn - 1;
            int mob = popcount64(knight_attacks[sq] & safe_mask);
            mg[c] += (mob - 4) * 4; eg[c] += (mob - 4) * 4;
        }
        uint64_t bi = b->pieces[c][BISHOP];
        while (bi) {
            int sq = bitscan_forward(bi);
            bi &= bi - 1;
            int mob = popcount64(bishop_attacks_bb(sq, b->occupancy[2]) & safe_mask);
            mg[c] += (mob - 7) * 4; eg[c] += (mob - 7) * 4;
        }
        uint64_t ro = b->pieces[c][ROOK];
        while (ro) {
            int sq = bitscan_forward(ro);
            ro &= ro - 1;
            int mob = popcount64(rook_attacks_bb(sq, b->occupancy[2]) & safe_mask);
            mg[c] += (mob - 7) * 2; eg[c] += (mob - 7) * 2;
        }
        uint64_t qu = b->pieces[c][QUEEN];
        while (qu) {
            int sq = bitscan_forward(qu);
            qu &= qu - 1;
            int mob = popcount64(queen_attacks_bb(sq, b->occupancy[2]) & safe_mask);
            mg[c] += (mob - 14) * 2; eg[c] += (mob - 14) * 2;
        }
    }
}

static void eval_endgame_positional_v2(const NativeBoard* b, int mg[2], int eg[2], const uint64_t passed_bb[2]) {
    uint64_t kw = b->pieces[WHITE][KING];
    uint64_t kb = b->pieces[BLACK][KING];
    if (!kw || !kb) return;
    int w_ksq = bitscan_forward(kw);
    int b_ksq = bitscan_forward(kb);

    for (int c = 0; c < 2; c++) {
        int my_ksq = (c == WHITE) ? w_ksq : b_ksq;
        int en_ksq = (c == WHITE) ? b_ksq : w_ksq;
        int kr = my_ksq / 8;
        int kf = my_ksq % 8;
        int en_kr = en_ksq / 8;
        int en_kf = en_ksq % 8;

        // King centralization
        int center_dist = std::abs(2 * kr - 7) + std::abs(2 * kf - 7);
        eg[c] += (14 - center_dist) * 2;

        // Passed pawn escort
        uint64_t passers = passed_bb[c];
        while (passers) {
            int psq = bitscan_forward(passers);
            passers &= passers - 1;
            int pr = psq / 8;
            int pf = psq % 8;
            int my_dist = std::max(std::abs(kr - pr), std::abs(kf - pf));
            int en_dist = std::max(std::abs(en_kr - pr), std::abs(en_kf - pf));
            eg[c] += (en_dist - my_dist) * 6;
        }
    }

    // Rule of the Square in pure King + Pawn endgames
    int total_pieces = popcount64(b->occupancy[2] & ~(b->pieces[0][PAWN] | b->pieces[1][PAWN] | b->pieces[0][KING] | b->pieces[1][KING]));
    if (total_pieces == 0) {
        for (int c = 0; c < 2; c++) {
            uint64_t passers = passed_bb[c];
            int en_ksq = (c == WHITE) ? b_ksq : w_ksq;
            int en_kr = en_ksq / 8;
            int en_kf = en_ksq % 8;

            while (passers) {
                int psq = bitscan_forward(passers);
                passers &= passers - 1;
                int pr = (c == WHITE) ? (psq / 8) : (7 - (psq / 8));
                int pf = psq % 8;
                int dist_to_promo = 7 - pr;
                if (c == b->side_to_move) dist_to_promo--; // Side to move advantage

                int en_king_dist = std::max(std::abs(en_kr - (c == WHITE ? 7 : 0)), std::abs(en_kf - pf));
                if (dist_to_promo < en_king_dist) {
                    eg[c] += 500; // Guaranteed unescorted promotion
                }
            }
        }
    }
}

EXPORT int native_evaluate_internal(const NativeBoard* b, int emode) {
    g_telemetry_eval_calls++;
    int mg_score[2] = { 0, 0 };
    int eg_score[2] = { 0, 0 };
    int game_phase = 0;

    for (int c = 0; c < 2; c++) {
        // Pawns
        uint64_t pawns = b->pieces[c][PAWN];
        while (pawns) {
            int sq = bitscan_forward(pawns);
            pawns &= pawns - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[PAWN] + MG_PAWN_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[PAWN] + MG_PAWN_TABLE[psq];
        }

        // Knights
        uint64_t knights = b->pieces[c][KNIGHT];
        while (knights) {
            int sq = bitscan_forward(knights);
            knights &= knights - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[KNIGHT] + MG_KNIGHT_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[KNIGHT] + MG_KNIGHT_TABLE[psq];
            game_phase += 1;
        }

        // Bishops
        uint64_t bishops = b->pieces[c][BISHOP];
        while (bishops) {
            int sq = bitscan_forward(bishops);
            bishops &= bishops - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[BISHOP] + MG_BISHOP_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[BISHOP] + MG_BISHOP_TABLE[psq];
            game_phase += 1;
        }

        // Rooks
        uint64_t rooks = b->pieces[c][ROOK];
        while (rooks) {
            int sq = bitscan_forward(rooks);
            rooks &= rooks - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[ROOK] + MG_ROOK_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[ROOK] + MG_ROOK_TABLE[psq];
            game_phase += 2;
        }

        // Queens
        uint64_t queens = b->pieces[c][QUEEN];
        while (queens) {
            int sq = bitscan_forward(queens);
            queens &= queens - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[QUEEN] + MG_QUEEN_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[QUEEN] + MG_QUEEN_TABLE[psq];
            game_phase += 4;
        }

        // King
        uint64_t king = b->pieces[c][KING];
        if (king) {
            int sq = bitscan_forward(king);
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[KING] + MG_KING_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[KING] + MG_KING_TABLE[psq];
        }
    }

    // Positional evaluation terms based on active eval mode
    uint64_t passed_bb[2] = { 0, 0 };
    if (emode == 1) { // E1: Pawn Structure only (X7)
        eval_pawn_structure(b, mg_score, eg_score);
    } else if (emode == 2) { // E2: Mobility only (X7)
        eval_mobility_and_coordination(b, mg_score, eg_score);
    } else if (emode == 3) { // E3: King Safety only (X7)
        eval_king_safety(b, mg_score, eg_score);
    } else if (emode == 4) { // E4: Endgame only (X7)
        eval_endgame_positional(b, mg_score, eg_score);
    } else if (emode == 5) { // E5: Full combined positional evaluation (X7 Baseline)
        eval_pawn_structure(b, mg_score, eg_score);
        eval_mobility_and_coordination(b, mg_score, eg_score);
        eval_king_safety(b, mg_score, eg_score);
        eval_endgame_positional(b, mg_score, eg_score);
    } else if (emode == 6) { // E6: Enhanced Pawn Structure only
        eval_pawn_structure_v2(b, mg_score, eg_score, passed_bb);
    } else if (emode == 7) { // E7: Enhanced King Safety only
        eval_king_safety_v2(b, mg_score, eg_score);
    } else if (emode == 8) { // E8: Enhanced Piece Activity & Coordination only
        eval_mobility_and_coordination_v2(b, mg_score, eg_score, passed_bb);
    } else if (emode == 9) { // E9: Enhanced Endgame only
        eval_pawn_structure_v2(b, mg_score, eg_score, passed_bb);
        eval_endgame_positional_v2(b, mg_score, eg_score, passed_bb);
    } else if (emode == 10) { // E10: Full Enhanced Classical Evaluation (Candidate X10)
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
        eval_mobility_and_coordination_v2(b, mg_score, eg_score, passed_bb);
        eval_king_safety_v2(b, mg_score, eg_score);
        eval_endgame_positional_v2(b, mg_score, eg_score, passed_bb);
    }

    if (game_phase > 24) game_phase = 24;
    int mg_diff = mg_score[WHITE] - mg_score[BLACK];
    int eg_diff = eg_score[WHITE] - eg_score[BLACK];

    int score = (mg_diff * game_phase + eg_diff * (24 - game_phase)) / 24;

    // Castling rights bonus (+15 cp per right)
    int castling_diff = 0;
    if (b->castling_rights & CASTLE_W_OO) castling_diff++;
    if (b->castling_rights & CASTLE_W_OOO) castling_diff++;
    if (b->castling_rights & CASTLE_B_OO) castling_diff--;
    if (b->castling_rights & CASTLE_B_OOO) castling_diff--;
    score += 15 * castling_diff;

    return (b->side_to_move == WHITE) ? score : -score;
}

EXPORT int native_evaluate(const NativeBoard* b) {
    return native_evaluate_internal(b, g_eval_mode);
}

EXPORT int native_evaluate_detail(const NativeBoard* b, int emode) {
    return native_evaluate_internal(b, emode);
}

// Static Exchange Evaluation (SEE) values (centipawns)
constexpr int SEE_PIECE_VALUES[6] = { 100, 320, 335, 500, 900, 20000 };

static int janus_see(const NativeBoard* b, uint16_t m) {
    if (m == 0) return 0;

    int from_sq = move_from(m);
    int to_sq = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);
    int us = b->side_to_move;
    int them = 1 - us;

    int victim_val = 0;
    int ep_captured_sq = -1;

    if (flag == 2) { // En Passant
        victim_val = SEE_PIECE_VALUES[PAWN];
        int to_file = to_sq % 8;
        int from_rank = from_sq / 8;
        ep_captured_sq = from_rank * 8 + to_file;
    } else {
        for (int p = 0; p < 6; p++) {
            if (b->pieces[them][p] & (1ULL << to_sq)) {
                victim_val = SEE_PIECE_VALUES[p];
                break;
            }
        }
    }

    int moving_pt = NO_PIECE;
    for (int p = 0; p < 6; p++) {
        if (b->pieces[us][p] & (1ULL << from_sq)) {
            moving_pt = p;
            break;
        }
    }
    if (moving_pt == NO_PIECE) return 0;

    int promo_bonus = 0;
    int piece_on_target = moving_pt;
    if (flag == 3) { // Promotion
        int promo_pt = (promo == 0 ? KNIGHT : (promo == 1 ? BISHOP : (promo == 2 ? ROOK : QUEEN)));
        promo_bonus = SEE_PIECE_VALUES[promo_pt] - SEE_PIECE_VALUES[PAWN];
        piece_on_target = promo_pt;
    }

    int gain[32];
    gain[0] = victim_val + promo_bonus;

    uint64_t occupied = b->occupancy[2] ^ (1ULL << from_sq);
    if (ep_captured_sq >= 0) {
        occupied ^= (1ULL << ep_captured_sq);
    }
    occupied |= (1ULL << to_sq);

    uint64_t active_mask = b->occupancy[2] & ~(1ULL << from_sq);
    if (ep_captured_sq >= 0) {
        active_mask &= ~(1ULL << ep_captured_sq);
    }

    int cur_side = them;
    int cur_piece_type = piece_on_target;
    int d = 0;

    while (d < 31) {
        int opp_side = 1 - cur_side;
        int k_sq = bitscan_forward(b->pieces[cur_side][KING]);

        int best_sq = -1;
        int best_pt = -1;

        // Attacker piece order: PAWN (0), KNIGHT (1), BISHOP (2), ROOK (3), QUEEN (4), KING (5)
        for (int pt = 0; pt < 6; pt++) {
            uint64_t cands = 0;
            if (pt == PAWN) {
                cands = pawn_attacks[opp_side][to_sq] & b->pieces[cur_side][PAWN] & active_mask;
            } else if (pt == KNIGHT) {
                cands = knight_attacks[to_sq] & b->pieces[cur_side][KNIGHT] & active_mask;
            } else if (pt == BISHOP) {
                cands = bishop_attacks_bb(to_sq, occupied) & b->pieces[cur_side][BISHOP] & active_mask;
            } else if (pt == ROOK) {
                cands = rook_attacks_bb(to_sq, occupied) & b->pieces[cur_side][ROOK] & active_mask;
            } else if (pt == QUEEN) {
                cands = (bishop_attacks_bb(to_sq, occupied) | rook_attacks_bb(to_sq, occupied)) & b->pieces[cur_side][QUEEN] & active_mask;
            } else if (pt == KING) {
                cands = king_attacks[to_sq] & b->pieces[cur_side][KING] & active_mask;
            }

            while (cands) {
                int sq = bitscan_forward(cands);
                cands &= cands - 1;

                if (pt == KING) {
                    uint64_t temp_occ = occupied ^ (1ULL << to_sq);
                    bool attacked = (pawn_attacks[cur_side][to_sq] & b->pieces[opp_side][PAWN] & active_mask) ||
                                    (knight_attacks[to_sq] & b->pieces[opp_side][KNIGHT] & active_mask) ||
                                    (king_attacks[to_sq] & b->pieces[opp_side][KING] & active_mask) ||
                                    (bishop_attacks_bb(to_sq, temp_occ) & (b->pieces[opp_side][BISHOP] | b->pieces[opp_side][QUEEN]) & active_mask) ||
                                    (rook_attacks_bb(to_sq, temp_occ) & (b->pieces[opp_side][ROOK] | b->pieces[opp_side][QUEEN]) & active_mask);
                    if (attacked) continue;
                    best_sq = sq;
                    best_pt = pt;
                    break;
                } else {
                    uint64_t temp_occ = (occupied ^ (1ULL << sq)) | (1ULL << to_sq);
                    uint64_t opp_diag = (b->pieces[opp_side][BISHOP] | b->pieces[opp_side][QUEEN]) & active_mask & ~(1ULL << to_sq);
                    uint64_t opp_ortho = (b->pieces[opp_side][ROOK] | b->pieces[opp_side][QUEEN]) & active_mask & ~(1ULL << to_sq);
                    bool in_check = ((bishop_attacks_bb(k_sq, temp_occ) & opp_diag) != 0) ||
                                    ((rook_attacks_bb(k_sq, temp_occ) & opp_ortho) != 0);
                    if (in_check) continue;
                    best_sq = sq;
                    best_pt = pt;
                    break;
                }
            }

            if (best_sq >= 0) break;
        }

        if (best_sq < 0) break;

        d++;
        gain[d] = SEE_PIECE_VALUES[cur_piece_type] - gain[d - 1];
        int to_rank = to_sq / 8;
        if (best_pt == PAWN && (to_rank == 0 || to_rank == 7)) {
            gain[d] += (SEE_PIECE_VALUES[QUEEN] - SEE_PIECE_VALUES[PAWN]);
            cur_piece_type = QUEEN;
        } else {
            cur_piece_type = best_pt;
        }

        occupied ^= (1ULL << best_sq);
        active_mask ^= (1ULL << best_sq);
        cur_side = 1 - cur_side;
    }

    while (d > 0) {
        gain[d - 1] = -std::max(-gain[d - 1], gain[d]);
        d--;
    }

    return gain[0];
}

EXPORT int native_see(NativeBoard* b, uint16_t m) {
    return janus_see(b, m);
}

// Move Ordering Score (K0 / N5 / N7 policy)
static int score_move_for_ordering(const NativeBoard* b, uint16_t m, uint16_t tt_move, int ply) {
    if (m == tt_move) return 10000000;

    int flag = move_flag(m);
    if (flag == 3) { // Promotion
        int promo = move_promo(m);
        return (promo == 3) ? 900000 : 800000;
    }

    int to = move_to(m);
    int from = move_from(m);
    int them = 1 - b->side_to_move;

    // Check if capture
    int victim = NO_PIECE;
    if (flag == 2) { // EP
        victim = PAWN;
    } else {
        for (int p = 0; p < 6; p++) {
            if (b->pieces[them][p] & (1ULL << to)) {
                victim = p;
                break;
            }
        }
    }

    if (victim != NO_PIECE) {
        int attacker = NO_PIECE;
        for (int p = 0; p < 6; p++) {
            if (b->pieces[b->side_to_move][p] & (1ULL << from)) {
                attacker = p;
                break;
            }
        }
        int mvv_lva = (victim * 10) - attacker;

        int cap_hist_bonus = 0;
        if ((g_tactical_ordering_mode == 1 || g_tactical_ordering_mode == 3 || g_tactical_ordering_mode == 4) && attacker < 6 && victim < 6) {
            int raw_bonus = g_capture_history[attacker][to][victim];
            if (g_tactical_ordering_mode == 4) {
                // M4: Bounded and dampened capture history [-2500, +2500] to protect winning capture precedence
                cap_hist_bonus = std::max(-2500, std::min(2500, raw_bonus / 2));
            } else {
                cap_hist_bonus = raw_bonus;
            }
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

        return 100000 + mvv_lva + cap_hist_bonus;
    }

    // Killer Moves (Quiet moves only)
    if (g_use_killer_ordering && ply >= 0 && ply < MAX_PLY) {
        if (m == g_killer_moves[ply][0]) return 90000;
        if (m == g_killer_moves[ply][1]) return 80000;
    }

    // Countermove Heuristic (Quiet moves only)
    if ((g_tactical_ordering_mode == 2 || g_tactical_ordering_mode == 3 || g_tactical_ordering_mode == 4) && ply >= 1 && g_ss[ply - 1].current_move != 0) {
        int prev_from = move_from(g_ss[ply - 1].current_move);
        int prev_to = move_to(g_ss[ply - 1].current_move);
        if (m == g_countermove_table[prev_from][prev_to]) {
            g_telemetry_countermove_probes++;
            return 75000; // Ordered immediately after Killer 2 (80,000)
        }
    }

    // History & Continuation History Heuristic (Quiet moves only)
    if (g_use_history_ordering) {
        int side = b->side_to_move;
        int h = g_history_table[side][from][to];
        if (g_conthist_mode == 0) {
            // Strict legacy X6 history scoring
            if (h > 0) {
                return std::min(MAX_HISTORY_SCORE, h);
            }
        } else {
            // Continuation history augmented scoring (P1.2)
            g_telemetry_conthist_probes++;
            int piece = NO_PIECE;
            for (int p = 0; p < 6; p++) {
                if (b->pieces[side][p] & (1ULL << from)) {
                    piece = p;
                    break;
                }
            }
            int score = h;
            if ((g_conthist_mode == 1 || g_conthist_mode == 3) && ply >= 1 && g_ss[ply - 1].current_move != 0) {
                int p1_piece = g_ss[ply - 1].piece;
                int p1_to = move_to(g_ss[ply - 1].current_move);
                if (p1_piece >= 0 && p1_piece < 6 && piece >= 0 && piece < 6) {
                    score += g_conthist_1ply[p1_piece][p1_to][piece][to];
                }
            }
            if ((g_conthist_mode == 2 || g_conthist_mode == 3) && ply >= 2 && g_ss[ply - 2].current_move != 0) {
                int p2_piece = g_ss[ply - 2].piece;
                int p2_to = move_to(g_ss[ply - 2].current_move);
                if (p2_piece >= 0 && p2_piece < 6 && piece >= 0 && piece < 6) {
                    score += g_conthist_2ply[p2_piece][p2_to][piece][to];
                }
            }
            return std::max(-20000, std::min(MAX_HISTORY_SCORE, score));
        }
    }

    return 0; // Quiet moves
}

// ============================================================================
// Quiescence Search with Delta Pruning
// ============================================================================


// ============================================================================
// Specialized Capture & Promotion Generation (Phase 1 / Phase 2)
// ============================================================================
EXPORT int native_generate_captures(NativeBoard* b, uint16_t* out_moves) {
    g_telemetry_movegen_calls++;
    uint16_t pseudo_moves[MAX_MOVES];
    int p_count = 0;

    int us = b->side_to_move;
    int them = 1 - us;
    uint64_t occ = b->occupancy[2];
    uint64_t enemies = b->occupancy[them];

    // 1. Pawn Captures & Promotions
    uint64_t pawns = b->pieces[us][PAWN];
    int forward = (us == WHITE) ? 8 : -8;
    int promo_rank = (us == WHITE) ? 7 : 0;

    while (pawns) {
        int sq = bitscan_forward(pawns);
        pawns &= pawns - 1;

        // Push promotion
        int to = sq + forward;
        if (to >= 0 && to < 64 && !(occ & (1ULL << to))) {
            if (to / 8 == promo_rank) {
                for (int pr = 0; pr < 4; pr++) pseudo_moves[p_count++] = encode_move(sq, to, 3, pr);
            }
        }

        // Capture promotions & normal captures
        uint64_t att = pawn_attacks[us][sq];
        uint64_t caps = att & enemies;
        while (caps) {
            int cap_to = bitscan_forward(caps);
            caps &= caps - 1;
            if (cap_to / 8 == promo_rank) {
                for (int pr = 0; pr < 4; pr++) pseudo_moves[p_count++] = encode_move(sq, cap_to, 3, pr);
            } else {
                pseudo_moves[p_count++] = encode_move(sq, cap_to, 0);
            }
        }

        // En Passant
        if (b->ep_square <= 63 && (att & (1ULL << b->ep_square))) {
            pseudo_moves[p_count++] = encode_move(sq, b->ep_square, 2);
        }
    }

    // 2. Knights
    uint64_t knights = b->pieces[us][KNIGHT];
    while (knights) {
        int sq = bitscan_forward(knights);
        knights &= knights - 1;
        uint64_t att = knight_attacks[sq] & enemies;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 3. Bishops / Queens diagonal
    uint64_t diags = b->pieces[us][BISHOP] | b->pieces[us][QUEEN];
    while (diags) {
        int sq = bitscan_forward(diags);
        diags &= diags - 1;
        uint64_t att = bishop_attacks_bb(sq, occ) & enemies;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 4. Rooks / Queens straight
    uint64_t straights = b->pieces[us][ROOK] | b->pieces[us][QUEEN];
    while (straights) {
        int sq = bitscan_forward(straights);
        straights &= straights - 1;
        uint64_t att = rook_attacks_bb(sq, occ) & enemies;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 5. King
    int k_sq = bitscan_forward(b->pieces[us][KING]);
    uint64_t k_att = king_attacks[k_sq] & enemies;
    while (k_att) {
        int to = bitscan_forward(k_att);
        k_att &= k_att - 1;
        pseudo_moves[p_count++] = encode_move(k_sq, to);
    }

    // Legality filter
    int legal_count = 0;
    UndoInfo undo;
    for (int i = 0; i < p_count; i++) {
        uint16_t m = pseudo_moves[i];
        if (!native_make_move(b, m, &undo)) continue;

        int king_sq = bitscan_forward(b->pieces[us][KING]);
        bool in_check = is_square_attacked(b, king_sq, them);
        native_unmake_move(b, m, &undo);

        if (!in_check) {
            out_moves[legal_count++] = m;
        }
    }

    g_telemetry_captures_gen += legal_count;
    return legal_count;
}

// ============================================================================
// Specialized Quiet Move Generation (Phase 1)
// ============================================================================
EXPORT int native_generate_quiets(NativeBoard* b, uint16_t* out_moves) {
    g_telemetry_movegen_calls++;
    uint16_t pseudo_moves[MAX_MOVES];
    int p_count = 0;

    int us = b->side_to_move;
    int them = 1 - us;
    uint64_t occ = b->occupancy[2];
    uint64_t empty = ~occ;

    // 1. Pawn Moves (non-promotions, non-captures)
    uint64_t pawns = b->pieces[us][PAWN];
    int forward = (us == WHITE) ? 8 : -8;
    int start_rank = (us == WHITE) ? 1 : 6;
    int promo_rank = (us == WHITE) ? 7 : 0;

    while (pawns) {
        int sq = bitscan_forward(pawns);
        pawns &= pawns - 1;
        int r = sq / 8;

        // Single push
        int to = sq + forward;
        if (to >= 0 && to < 64 && !(occ & (1ULL << to))) {
            if (to / 8 != promo_rank) {
                pseudo_moves[p_count++] = encode_move(sq, to, 0);
                // Double push
                if (r == start_rank) {
                    int to2 = to + forward;
                    if (!(occ & (1ULL << to2))) {
                        pseudo_moves[p_count++] = encode_move(sq, to2, 0);
                    }
                }
            }
        }
    }

    // 2. Knights (empty squares)
    uint64_t knights = b->pieces[us][KNIGHT];
    while (knights) {
        int sq = bitscan_forward(knights);
        knights &= knights - 1;
        uint64_t att = knight_attacks[sq] & empty;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 3. Bishops / Queens diagonal (empty squares)
    uint64_t diags = b->pieces[us][BISHOP] | b->pieces[us][QUEEN];
    while (diags) {
        int sq = bitscan_forward(diags);
        diags &= diags - 1;
        uint64_t att = bishop_attacks_bb(sq, occ) & empty;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 4. Rooks / Queens straight (empty squares)
    uint64_t straights = b->pieces[us][ROOK] | b->pieces[us][QUEEN];
    while (straights) {
        int sq = bitscan_forward(straights);
        straights &= straights - 1;
        uint64_t att = rook_attacks_bb(sq, occ) & empty;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 5. King (empty squares)
    int k_sq = bitscan_forward(b->pieces[us][KING]);
    uint64_t k_att = king_attacks[k_sq] & empty;
    while (k_att) {
        int to = bitscan_forward(k_att);
        k_att &= k_att - 1;
        pseudo_moves[p_count++] = encode_move(k_sq, to);
    }

    // 6. Castling
    if (us == WHITE) {
        if ((b->castling_rights & CASTLE_W_OO) && !(occ & (1ULL << 5)) && !(occ & (1ULL << 6))) {
            if (!is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 5, BLACK) && !is_square_attacked(b, 6, BLACK)) {
                pseudo_moves[p_count++] = encode_move(4, 6, 1);
            }
        }
        if ((b->castling_rights & CASTLE_W_OOO) && !(occ & (1ULL << 1)) && !(occ & (1ULL << 2)) && !(occ & (1ULL << 3))) {
            if (!is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 3, BLACK) && !is_square_attacked(b, 2, BLACK)) {
                pseudo_moves[p_count++] = encode_move(4, 2, 1);
            }
        }
    } else {
        if ((b->castling_rights & CASTLE_B_OO) && !(occ & (1ULL << 61)) && !(occ & (1ULL << 62))) {
            if (!is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 61, WHITE) && !is_square_attacked(b, 62, WHITE)) {
                pseudo_moves[p_count++] = encode_move(60, 62, 1);
            }
        }
        if ((b->castling_rights & CASTLE_B_OOO) && !(occ & (1ULL << 57)) && !(occ & (1ULL << 58)) && !(occ & (1ULL << 59))) {
            if (!is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 59, WHITE) && !is_square_attacked(b, 58, WHITE)) {
                pseudo_moves[p_count++] = encode_move(60, 58, 1);
            }
        }
    }

    // Legality filter
    int legal_count = 0;
    UndoInfo undo;
    for (int i = 0; i < p_count; i++) {
        uint16_t m = pseudo_moves[i];
        if (!native_make_move(b, m, &undo)) continue;

        int king_sq = bitscan_forward(b->pieces[us][KING]);
        bool in_check = is_square_attacked(b, king_sq, them);
        native_unmake_move(b, m, &undo);

        if (!in_check) {
            out_moves[legal_count++] = m;
        }
    }

    g_telemetry_quiets_gen += legal_count;
    return legal_count;
}

// Helper: check if arbitrary encoded move is pseudo-legal
static bool is_pseudo_legal_move(const NativeBoard* b, uint16_t m) {
    if (m == 0) return false;
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int us = b->side_to_move;
    int them = 1 - us;
    uint64_t occ = b->occupancy[2];

    int piece = NO_PIECE;
    for (int p = 0; p < 6; p++) {
        if (b->pieces[us][p] & (1ULL << from)) {
            piece = p;
            break;
        }
    }
    if (piece == NO_PIECE) return false;

    if (flag == 1) { // Castling
        if (piece != KING) return false;
        if (us == WHITE) {
            if (from == 4 && to == 6) {
                return (b->castling_rights & CASTLE_W_OO) && !(occ & (1ULL << 5)) && !(occ & (1ULL << 6)) &&
                       !is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 5, BLACK) && !is_square_attacked(b, 6, BLACK);
            }
            if (from == 4 && to == 2) {
                return (b->castling_rights & CASTLE_W_OOO) && !(occ & (1ULL << 1)) && !(occ & (1ULL << 2)) && !(occ & (1ULL << 3)) &&
                       !is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 3, BLACK) && !is_square_attacked(b, 2, BLACK);
            }
        } else {
            if (from == 60 && to == 62) {
                return (b->castling_rights & CASTLE_B_OO) && !(occ & (1ULL << 61)) && !(occ & (1ULL << 62)) &&
                       !is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 61, WHITE) && !is_square_attacked(b, 62, WHITE);
            }
            if (from == 60 && to == 58) {
                return (b->castling_rights & CASTLE_B_OOO) && !(occ & (1ULL << 57)) && !(occ & (1ULL << 58)) && !(occ & (1ULL << 59)) &&
                       !is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 59, WHITE) && !is_square_attacked(b, 58, WHITE);
            }
        }
        return false;
    }

    if (b->occupancy[us] & (1ULL << to)) return false;

    if (piece == PAWN) {
        int forward = (us == WHITE) ? 8 : -8;
        int start_rank = (us == WHITE) ? 1 : 6;
        int promo_rank = (us == WHITE) ? 7 : 0;
        int r = from / 8;

        if (flag == 2) { // En passant
            return (b->ep_square == to && (pawn_attacks[us][from] & (1ULL << to)));
        }

        if (to == from + forward) {
            if (occ & (1ULL << to)) return false;
            if (to / 8 == promo_rank) return flag == 3;
            return flag == 0;
        }
        if (r == start_rank && to == from + 2 * forward) {
            return !(occ & (1ULL << (from + forward))) && !(occ & (1ULL << to)) && flag == 0;
        }
        if (pawn_attacks[us][from] & (1ULL << to)) {
            if (!(b->occupancy[them] & (1ULL << to))) return false;
            if (to / 8 == promo_rank) return flag == 3;
            return flag == 0;
        }
        return false;
    } else if (piece == KNIGHT) {
        return (knight_attacks[from] & (1ULL << to)) != 0;
    } else if (piece == BISHOP) {
        return (bishop_attacks_bb(from, occ) & (1ULL << to)) != 0;
    } else if (piece == ROOK) {
        return (rook_attacks_bb(from, occ) & (1ULL << to)) != 0;
    } else if (piece == QUEEN) {
        return ((bishop_attacks_bb(from, occ) | rook_attacks_bb(from, occ)) & (1ULL << to)) != 0;
    } else if (piece == KING) {
        return (king_attacks[from] & (1ULL << to)) != 0;
    }
    return false;
}

// Helper: check if move is pseudo-legal AND does not leave king in check
static bool is_legal_move(NativeBoard* b, uint16_t m) {
    if (!is_pseudo_legal_move(b, m)) return false;
    int us = b->side_to_move;
    int them = 1 - us;
    UndoInfo undo;
    if (!native_make_move(b, m, &undo)) return false;
    int k_sq = bitscan_forward(b->pieces[us][KING]);
    bool in_chk = is_square_attacked(b, k_sq, them);
    native_unmake_move(b, m, &undo);
    return !in_chk;
}

// ============================================================================
// Staged MovePicker Architecture (Phase 1)
// ============================================================================
enum MovePickerStage {
    STAGE_TT = 0,
    STAGE_GEN_CAPTURES,
    STAGE_CAPTURES,
    STAGE_KILLERS,
    STAGE_GEN_QUIETS,
    STAGE_QUIETS,
    STAGE_DONE
};

struct MovePicker {
    NativeBoard* board;
    uint16_t tt_move;
    int ply;
    int depth;
    bool in_check;
    MovePickerStage stage;

    uint16_t caps[MAX_MOVES];
    int caps_scores[MAX_MOVES];
    int num_caps;
    int cur_cap;

    uint16_t quiets[MAX_MOVES];
    int quiets_scores[MAX_MOVES];
    int num_quiets;
    int cur_quiet;

    uint16_t killer1;
    uint16_t killer2;
    int cur_killer;

    uint16_t evasions[MAX_MOVES];
    int evasion_scores[MAX_MOVES];
    int num_evasions;
    int cur_evasion;

    uint16_t yielded[MAX_MOVES];
    int num_yielded;

    void init(NativeBoard* b, uint16_t tt_m, int p, int d, bool chk) {
        board = b;
        tt_move = tt_m;
        ply = p;
        depth = d;
        in_check = chk;
        num_yielded = 0;
        cur_cap = 0;
        num_caps = 0;
        cur_quiet = 0;
        num_quiets = 0;
        cur_killer = 0;
        num_evasions = 0;
        cur_evasion = 0;

        killer1 = (ply >= 0 && ply < MAX_PLY) ? g_killer_moves[ply][0] : 0;
        killer2 = (ply >= 0 && ply < MAX_PLY) ? g_killer_moves[ply][1] : 0;

        if (in_check) {
            stage = STAGE_DONE;
            num_evasions = native_generate_legal_moves(board, evasions);
            for (int i = 0; i < num_evasions; i++) {
                evasion_scores[i] = score_move_for_ordering(board, evasions[i], tt_move, ply);
            }
            for (int i = 0; i < num_evasions - 1; i++) {
                int best_idx = i;
                for (int j = i + 1; j < num_evasions; j++) {
                    if (evasion_scores[j] > evasion_scores[best_idx]) best_idx = j;
                }
                std::swap(evasions[i], evasions[best_idx]);
                std::swap(evasion_scores[i], evasion_scores[best_idx]);
            }
        } else {
            stage = (tt_move != 0 && is_legal_move(board, tt_move)) ? STAGE_TT : STAGE_GEN_CAPTURES;
        }
    }

    uint16_t next_move() {
        if (in_check) {
            if (cur_evasion < num_evasions) {
                return evasions[cur_evasion++];
            }
            return 0;
        }

        while (stage != STAGE_DONE) {
            switch (stage) {
                case STAGE_TT: {
                    stage = STAGE_GEN_CAPTURES;
                    yielded[num_yielded++] = tt_move;
                    return tt_move;
                }
                case STAGE_GEN_CAPTURES: {
                    num_caps = native_generate_captures(board, caps);
                    for (int i = 0; i < num_caps; i++) {
                        caps_scores[i] = score_move_for_ordering(board, caps[i], 0, ply);
                    }
                    for (int i = 0; i < num_caps - 1; i++) {
                        int best_idx = i;
                        for (int j = i + 1; j < num_caps; j++) {
                            if (caps_scores[j] > caps_scores[best_idx]) best_idx = j;
                        }
                        std::swap(caps[i], caps[best_idx]);
                        std::swap(caps_scores[i], caps_scores[best_idx]);
                    }
                    stage = STAGE_CAPTURES;
                    cur_cap = 0;
                }
                case STAGE_CAPTURES: {
                    while (cur_cap < num_caps) {
                        uint16_t m = caps[cur_cap++];
                        if (!has_been_yielded(m)) {
                            yielded[num_yielded++] = m;
                            return m;
                        }
                    }
                    stage = STAGE_KILLERS;
                    cur_killer = 0;
                }
                case STAGE_KILLERS: {
                    if (cur_killer == 0) {
                        cur_killer++;
                        if (killer1 != 0 && !has_been_yielded(killer1) && is_legal_move(board, killer1)) {
                            yielded[num_yielded++] = killer1;
                            return killer1;
                        }
                    }
                    if (cur_killer == 1) {
                        cur_killer++;
                        if (killer2 != 0 && killer2 != killer1 && !has_been_yielded(killer2) && is_legal_move(board, killer2)) {
                            yielded[num_yielded++] = killer2;
                            return killer2;
                        }
                    }
                    stage = STAGE_GEN_QUIETS;
                }
                case STAGE_GEN_QUIETS: {
                    num_quiets = native_generate_quiets(board, quiets);
                    for (int i = 0; i < num_quiets; i++) {
                        quiets_scores[i] = score_move_for_ordering(board, quiets[i], 0, ply);
                    }
                    for (int i = 0; i < num_quiets - 1; i++) {
                        int best_idx = i;
                        for (int j = i + 1; j < num_quiets; j++) {
                            if (quiets_scores[j] > quiets_scores[best_idx]) best_idx = j;
                        }
                        std::swap(quiets[i], quiets[best_idx]);
                        std::swap(quiets_scores[i], quiets_scores[best_idx]);
                    }
                    stage = STAGE_QUIETS;
                    cur_quiet = 0;
                }
                case STAGE_QUIETS: {
                    while (cur_quiet < num_quiets) {
                        uint16_t m = quiets[cur_quiet++];
                        if (!has_been_yielded(m)) {
                            yielded[num_yielded++] = m;
                            return m;
                        }
                    }
                    stage = STAGE_DONE;
                    break;
                }
                default:
                    stage = STAGE_DONE;
                    break;
            }
        }
        return 0;
    }

    bool has_been_yielded(uint16_t m) const {
        for (int i = 0; i < num_yielded; i++) {
            if (yielded[i] == m) return true;
        }
        return false;
    }
};

static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted) {
    nodes++;

    if ((nodes & 2047) == 0) {
        if (std::chrono::steady_clock::now() >= deadline) {
            aborted = true;
            return 0;
        }
    }

    int stand_pat = native_evaluate(b);
    if (stand_pat >= beta) return beta;
    if (stand_pat > alpha) alpha = stand_pat;

    // Delta pruning margin: 900 (Queen) + 200 safety
    constexpr int DELTA_MARGIN = 1100;
    if (stand_pat + DELTA_MARGIN < alpha) {
        return alpha;
    }

    struct ScoredMove {
        uint16_t m;
        int score;
    };
    ScoredMove caps[MAX_MOVES];
    int n_caps = 0;

    uint16_t raw_caps[MAX_MOVES];
    int n_raw = 0;

    if (g_use_staged_movegen) {
        n_raw = native_generate_captures(b, raw_caps);
    } else {
        uint16_t all_m[MAX_MOVES];
        int n_all = native_generate_legal_moves(b, all_m);
        int them_side = 1 - b->side_to_move;
        for (int i = 0; i < n_all; i++) {
            int to = move_to(all_m[i]);
            bool is_c = (b->occupancy[them_side] & (1ULL << to)) || (move_flag(all_m[i]) == 2);
            if (is_c || move_flag(all_m[i]) == 3) {
                raw_caps[n_raw++] = all_m[i];
            }
        }
    }

    for (int i = 0; i < n_raw; i++) {
        uint16_t m = raw_caps[i];
        int to = move_to(m);
        int them = 1 - b->side_to_move;
        int score = 0;

        if (move_flag(m) == 3) {
            int promo = move_promo(m);
            score = (promo == 3) ? 900000 : 800000;
        } else if (g_quiescence_see_mode > 0 || g_use_see_in_quiescence) {
            int see_val = janus_see(b, m);
            g_see_total_evaluations++;
            if (g_quiescence_see_mode >= 2 && see_val < 0 && move_flag(m) != 3) {
                g_telemetry_qmoves_pruned++;
                continue;
            }
            if (g_quiescence_see_mode == 3 && see_val < -50 && move_flag(m) != 3) {
                g_telemetry_qmoves_pruned++;
                continue;
            }
            int victim = NO_PIECE;
            if (move_flag(m) == 2) {
                victim = PAWN;
            } else {
                for (int p = 0; p < 6; p++) {
                    if (b->pieces[them][p] & (1ULL << to)) { victim = p; break; }
                }
            }
            int attacker = NO_PIECE;
            int from = move_from(m);
            for (int p = 0; p < 6; p++) {
                if (b->pieces[b->side_to_move][p] & (1ULL << from)) { attacker = p; break; }
            }
            int mvv_lva = (victim * 10) - attacker;
            if (see_val > 0) {
                g_see_positive_captures++;
                score = 100000 + mvv_lva;
            } else if (see_val == 0) {
                g_see_neutral_captures++;
                score = 95000 + mvv_lva;
            } else {
                g_see_negative_captures++;
                score = 10000 + std::max(-10000, see_val) + mvv_lva;
            }
        } else {
            score = score_move_for_ordering(b, m, 0, 0);
        }
        caps[n_caps++] = { m, score };
    }

    std::sort(caps, caps + n_caps, [](const ScoredMove& a, const ScoredMove& b) {
        return a.score > b.score;
    });

    UndoInfo undo;
    for (int i = 0; i < n_caps; i++) {
        if (!native_make_move(b, caps[i].m, &undo)) continue;
        int score = -quiescence(b, -beta, -alpha, nodes, deadline, aborted);
        native_unmake_move(b, caps[i].m, &undo);

        if (aborted) return 0;
        if (score >= beta) return beta;
        if (score > alpha) alpha = score;
    }

    return alpha;
}

// ============================================================================
// Alpha-Beta Negamax Search with TT, PV and Draw Detection
// ============================================================================

static int negamax(
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
) {
    nodes++;

    if ((nodes & 2047) == 0) {
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
    }

    int extension = 0;
    // Singular Extension & Multi-Cut Verification (Phases 3 & 4)
    int min_se_depth = (g_singular_extension_mode == 3) ? 8 : 6;
    if (g_singular_extension_mode > 0 &&
        depth >= min_se_depth &&
        ply > 0 &&
        excluded_move == 0 &&
        tt_move != 0 &&
        entry.key == key &&
        entry.depth >= depth - 3 &&
        entry.flag != TT_UPPER &&
        std::abs(entry.score) < MATE_THRESHOLD) {

        g_telemetry_se_probes++;
        int se_margin = (g_singular_extension_mode == 1 || g_singular_extension_mode == 3) ? (2 * depth) : (depth + 15);
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
    }

    bool in_check = (native_is_check(b) != 0);

    // ========================================================================
    // Reverse Futility Pruning (RFP / Static Null Move Pruning, Phase 4)
    // ========================================================================
    if (g_use_reverse_futility && depth <= 3 && ply > 0 && !in_check && std::abs(beta) < MATE_SCORE - 100) {
        g_telemetry_rfp_probes++;
        int static_eval = native_evaluate(b);
        int rfp_margin = g_rfp_margin_per_depth * depth;
        if (static_eval - rfp_margin >= beta) {
            g_telemetry_rfp_cutoffs++;
            return static_eval;
        }
    }

    // ========================================================================
    // Null-Move Pruning (NMP, Phase 3)
    // ========================================================================
    int us_side = b->side_to_move;
    int them_side = 1 - us_side;
    uint64_t non_pawn_mat = b->pieces[us_side][KNIGHT] | b->pieces[us_side][BISHOP] | 
                            b->pieces[us_side][ROOK]   | b->pieces[us_side][QUEEN];
    if (g_use_null_move_pruning && depth >= 3 && ply > 0 && !in_check && non_pawn_mat != 0 && std::abs(beta) < MATE_SCORE - 100) {
        g_telemetry_nmp_probes++;
        int R = g_nmp_reduction;

        b->side_to_move = them_side;
        int saved_ep = b->ep_square;
        b->ep_square = 64;
        b->zobrist_key ^= zobrist_side;
        if (saved_ep <= 63) b->zobrist_key ^= zobrist_ep[saved_ep % 8];
        native_push_history(b->zobrist_key);

        int null_score = -negamax(b, depth - 1 - R, -beta, -beta + 1, ply + 1, nodes, deadline, aborted, nullptr);

        b->side_to_move = us_side;
        b->ep_square = saved_ep;
        b->zobrist_key ^= zobrist_side;
        if (saved_ep <= 63) b->zobrist_key ^= zobrist_ep[saved_ep % 8];
        native_pop_history();

        if (aborted) return 0;
        if (null_score >= beta) {
            g_telemetry_nmp_cutoffs++;
            return (null_score >= MATE_SCORE - 100) ? beta : null_score;
        }
    }

    // ProbCut Pruning (Phase 5)
    int min_pc_depth = (g_probcut_mode == 3) ? 6 : 5;
    if (g_probcut_mode > 0 &&
        depth >= min_pc_depth &&
        ply > 0 &&
        excluded_move == 0 &&
        !in_check &&
        std::abs(beta) < MATE_THRESHOLD) {

        int pc_margin = (g_probcut_mode == 2) ? 150 : 200;
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
    uint16_t best_move = 0;
    int best_score = -INF;
    UndoInfo undo;
    int moves_searched = 0;
    int legal_moves_count = 0;

    MovePicker picker;
    if (g_use_staged_movegen) {
        picker.init(b, tt_move, ply, depth, in_check);
    }

    uint16_t legacy_moves[MAX_MOVES];
    int legacy_n = 0;
    struct ScoredMove {
        uint16_t m;
        int score;
    };
    ScoredMove legacy_scored[MAX_MOVES];
    if (!g_use_staged_movegen) {
        legacy_n = native_generate_legal_moves(b, legacy_moves);
        if (legacy_n == 0) {
            return in_check ? -(MATE_SCORE - ply) : 0;
        }
        for (int i = 0; i < legacy_n; i++) {
            legacy_scored[i] = { legacy_moves[i], score_move_for_ordering(b, legacy_moves[i], tt_move, ply) };
        }
        std::sort(legacy_scored, legacy_scored + legacy_n, [](const ScoredMove& a, const ScoredMove& b) {
            return a.score > b.score;
        });
        best_move = legacy_scored[0].m;
    }

    int legacy_idx = 0;
    while (true) {
        uint16_t m = 0;
        if (g_use_staged_movegen) {
            m = picker.next_move();
            if (m == 0) break;
        } else {
            if (legacy_idx >= legacy_n) break;
            m = legacy_scored[legacy_idx++].m;
        }
        if (m == excluded_move) continue;

        legal_moves_count++;
        if (best_move == 0) best_move = m;

        // Query moved piece BEFORE make_move modifies bitboards
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

        if (!native_make_move(b, m, &undo)) continue;

        moves_searched++;

        // Track move in search stack for continuation history
        g_ss[ply].current_move = m;
        g_ss[ply].piece = moved_piece;

        // Push to game history stack for tree repetition detection
        native_push_history(b->zobrist_key);

        int child_depth = depth - 1 + (m == tt_move ? extension : 0);
        int score = 0;
        uint16_t child_best = 0;

        // LMR Eligibility Check (10 Invariants)
        bool is_lmr_eligible = g_use_lmr &&
                               (ply > 0) &&
                               (depth >= g_lmr_min_depth) &&
                               (moves_searched >= g_lmr_move_threshold) &&
                               !in_check &&
                               (undo.captured_piece == NO_PIECE) &&
                               (move_flag(m) != 3) && // Non-promotion
                               (m != tt_move) &&
                               (native_is_check(b) == 0); // Non-checking move

        int dynamic_reduction = g_lmr_base_reduction;
        if (is_lmr_eligible) {
            if (g_dynamic_lmr_mode == 1) { // L1: Logarithmic table
                int d_idx = std::min(depth, MAX_SEARCH_PLY - 1);
                int m_idx = std::min(moves_searched, MAX_MOVES - 1);
                dynamic_reduction = g_lmr_table[d_idx][m_idx];
                if (dynamic_reduction < 1) dynamic_reduction = 1;
            } else if (g_dynamic_lmr_mode == 2) { // L2: History modulated
                int d_idx = std::min(depth, MAX_SEARCH_PLY - 1);
                int m_idx = std::min(moves_searched, MAX_MOVES - 1);
                dynamic_reduction = g_lmr_table[d_idx][m_idx];
                int h = g_history_table[us_side][move_from(m)][move_to(m)];
                if (h > 8000) dynamic_reduction -= 1;
                else if (h < -4000) dynamic_reduction += 1;
                if (dynamic_reduction < 1) dynamic_reduction = 1;
            } else if (g_dynamic_lmr_mode == 3) { // L3: Dynamic + Conthist modulated
                int d_idx = std::min(depth, MAX_SEARCH_PLY - 1);
                int m_idx = std::min(moves_searched, MAX_MOVES - 1);
                dynamic_reduction = g_lmr_table[d_idx][m_idx];
                int h = g_history_table[us_side][move_from(m)][move_to(m)];
                int ch1 = 0, ch2 = 0;
                int p_cur = moved_piece;
                if (p_cur >= 0 && p_cur < 6) {
                    if (ply >= 1 && g_ss[ply - 1].current_move != 0) {
                        int p1_piece = g_ss[ply - 1].piece;
                        int p1_to = move_to(g_ss[ply - 1].current_move);
                        if (p1_piece >= 0 && p1_piece < 6) ch1 = g_conthist_1ply[p1_piece][p1_to][p_cur][move_to(m)];
                    }
                    if (ply >= 2 && g_ss[ply - 2].current_move != 0) {
                        int p2_piece = g_ss[ply - 2].piece;
                        int p2_to = move_to(g_ss[ply - 2].current_move);
                        if (p2_piece >= 0 && p2_piece < 6) ch2 = g_conthist_2ply[p2_piece][p2_to][p_cur][move_to(m)];
                    }
                }
                int tot_h = h + ch1 + ch2;
                int h_thresh = (g_search_variant == "X8" || g_search_variant == "X9") ? std::max(1000, 250 * depth) : 10000;
                int h_neg_thresh = (g_search_variant == "X8" || g_search_variant == "X9") ? (-h_thresh / 2) : -5000;
                if (tot_h > h_thresh) dynamic_reduction -= 1;
                else if (tot_h < h_neg_thresh) dynamic_reduction += 1;
                if (dynamic_reduction < 1) dynamic_reduction = 1;
            }
            if (child_depth - dynamic_reduction < 1) dynamic_reduction = child_depth - 1;
            if (dynamic_reduction <= 0) is_lmr_eligible = false;
        }

        if (moves_searched == 1 || !g_use_pvs) {
            // PV Move (or PVS disabled): search with full window [-beta, -alpha]
            if (is_lmr_eligible) {
                // If PVS disabled but LMR enabled
                g_lmr_eligible_moves++;
                int reduction = dynamic_reduction;
                int reduced_depth = std::max(1, child_depth - reduction);
                g_lmr_reduced_moves++;
                g_telemetry_dynamic_lmr_reduced++;

                score = -negamax(b, reduced_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);

                if (score > alpha && !aborted) {
                    g_lmr_researches++;
                    score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
                }
            } else {
                score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
            }
            g_pvs_full_window_searches++;
        } else {
            // PVS Subsequent moves: Null-window search [-alpha - 1, -alpha]
            if (is_lmr_eligible) {
                g_lmr_eligible_moves++;
                int reduction = dynamic_reduction;
                int reduced_depth = std::max(1, child_depth - reduction);
                g_lmr_reduced_moves++;
                g_telemetry_dynamic_lmr_reduced++;
                g_pvs_null_window_searches++;

                // Stage 1: Reduced Depth Null-Window Probe
                score = -negamax(b, reduced_depth, -alpha - 1, -alpha, ply + 1, nodes, deadline, aborted, &child_best);

                // Stage 2: Full Depth Null-Window Re-search if reduced probe beat alpha
                if (score > alpha && !aborted) {
                    g_lmr_researches++;
                    g_pvs_null_window_searches++;
                    score = -negamax(b, child_depth, -alpha - 1, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
                }
            } else {
                // Non-LMR move: Full depth null-window probe
                g_pvs_null_window_searches++;
                score = -negamax(b, child_depth, -alpha - 1, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
            }

            // Stage 3: Full-Window PVS Re-Search
            // If the null-window probe returned score > alpha and score < beta, re-search with full window [-beta, -alpha]
            if (score > alpha && score < beta && !aborted) {
                g_pvs_researches++;
                g_pvs_full_window_searches++;
                score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
            }
        }

        native_pop_history();
        native_unmake_move(b, m, &undo);
        g_ss[ply].current_move = 0;
        g_ss[ply].piece = NO_PIECE;

        if (aborted) return 0;

        if (score > best_score) {
            best_score = score;
            best_move = m;
        }
        if (score > alpha) {
            alpha = score;

            // Update PV Table
            g_pv_table[ply][0] = m;
            for (int j = 0; j < g_pv_len[ply + 1]; j++) {
                g_pv_table[ply][j + 1] = g_pv_table[ply + 1][j];
            }
            g_pv_len[ply] = g_pv_len[ply + 1] + 1;
        }
        if (alpha >= beta) {
            g_ordering_total_cutoffs++;
            g_ordering_sum_cutoff_index += moves_searched;
            if (moves_searched == 1) g_ordering_cutoff_move_1++;
            else if (moves_searched == 2) g_ordering_cutoff_move_2++;
            else if (moves_searched == 3) g_ordering_cutoff_move_3++;
            else g_ordering_cutoff_move_4plus++;

            if (m == tt_move) g_ordering_cutoff_tt++;

            bool is_quiet = (undo.captured_piece == NO_PIECE) && (move_flag(m) != 3);
            if (is_quiet) {
                g_ordering_cutoff_quiet++;
                // Killer update
                if (g_use_killer_ordering && ply >= 0 && ply < MAX_PLY) {
                    if (m == g_killer_moves[ply][0]) {
                        g_ordering_cutoff_killer1++;
                    } else if (m == g_killer_moves[ply][1]) {
                        g_ordering_cutoff_killer2++;
                    } else {
                        g_killer_moves[ply][1] = g_killer_moves[ply][0];
                        g_killer_moves[ply][0] = m;
                    }
                }
                // History & Continuation History Update (P1.2)
                if (g_use_history_ordering) {
                    int side = b->side_to_move;
                    int from = move_from(m);
                    int to = move_to(m);
                    if (g_history_table[side][from][to] > 0) {
                        g_ordering_cutoff_history++;
                    }
                    if (g_conthist_mode == 0) {
                        // Strict legacy X6 history update
                        int bonus = depth * depth;
                        g_history_table[side][from][to] += bonus;
                        if (g_history_table[side][from][to] > MAX_HISTORY_SCORE) {
                            g_history_table[side][from][to] = MAX_HISTORY_SCORE;
                        }
                    } else {
                        // Gravity history update
                        g_telemetry_conthist_cutoffs++;
                        int bonus = std::min(300, depth * depth);
                        int cur_h = g_history_table[side][from][to];
                        g_history_table[side][from][to] = cur_h + bonus - (cur_h * std::abs(bonus)) / 16384;

                        // Countermove heuristic update (Phase 2)
                        if ((g_tactical_ordering_mode == 2 || g_tactical_ordering_mode == 3 || g_tactical_ordering_mode == 4) && ply >= 1 && g_ss[ply - 1].current_move != 0) {
                            int prev_from = move_from(g_ss[ply - 1].current_move);
                            int prev_to = move_to(g_ss[ply - 1].current_move);
                            g_countermove_table[prev_from][prev_to] = m;
                            g_telemetry_countermove_cutoffs++;
                        }

                        // Continuation history updates
                        int p_cur = moved_piece;
                        if (p_cur >= 0 && p_cur < 6) {
                            if ((g_conthist_mode == 1 || g_conthist_mode == 3) && ply >= 1 && g_ss[ply - 1].current_move != 0) {
                                int p1_piece = g_ss[ply - 1].piece;
                                int p1_to = move_to(g_ss[ply - 1].current_move);
                                if (p1_piece >= 0 && p1_piece < 6) {
                                    int cur1 = g_conthist_1ply[p1_piece][p1_to][p_cur][to];
                                    g_conthist_1ply[p1_piece][p1_to][p_cur][to] = (int16_t)(cur1 + bonus - (cur1 * std::abs(bonus)) / 16384);
                                }
                            }
                            if ((g_conthist_mode == 2 || g_conthist_mode == 3) && ply >= 2 && g_ss[ply - 2].current_move != 0) {
                                int p2_piece = g_ss[ply - 2].piece;
                                int p2_to = move_to(g_ss[ply - 2].current_move);
                                if (p2_piece >= 0 && p2_piece < 6) {
                                    int cur2 = g_conthist_2ply[p2_piece][p2_to][p_cur][to];
                                    g_conthist_2ply[p2_piece][p2_to][p_cur][to] = (int16_t)(cur2 + bonus - (cur2 * std::abs(bonus)) / 16384);
                                }
                            }
                        }
                    }
                }
            } else {
                g_ordering_cutoff_captures++;
                // Capture History update (Phase 2)
                if ((g_tactical_ordering_mode == 1 || g_tactical_ordering_mode == 3 || g_tactical_ordering_mode == 4) && undo.captured_piece < 6) {
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
            }

            if (is_lmr_eligible) {
                g_lmr_cutoffs++;
            }
            if (g_use_pvs) {
                g_pvs_cutoffs++;
            }
            g_telemetry_total_cutoffs++;
            if (moves_searched == 1) g_telemetry_first_move_cutoffs++;
            break; // Beta cutoff
        }
    }

    if (legal_moves_count == 0) {
        return in_check ? -(MATE_SCORE - ply) : 0;
    }

    if (out_best_move) *out_best_move = best_move;

    // Store TT entry with normalized mate scores and depth-preferred replacement (Never store during excluded searches)
    if (!aborted && excluded_move == 0) {
        uint8_t flag = TT_EXACT;
        if (best_score <= orig_alpha) flag = TT_UPPER;
        else if (best_score >= beta) flag = TT_LOWER;

        if (g_search_variant == "X11" || g_num_threads > 1) {
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
        }
    }

    return best_score;
}

// ============================================================================
// Top-Level Iterative Deepening Search
// ============================================================================

struct WorkerSearchResult {
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
    g_tt_telemetry.reset();

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

    
    std::cout << "forensics_tt probes=" << g_tt_telemetry.probes.load()
              << " hits=" << g_tt_telemetry.hits.load()
              << " cutoffs=" << g_tt_telemetry.cutoffs.load()
              << " stores=" << g_tt_telemetry.stores.load()
              << " same_key_overwrites=" << g_tt_telemetry.same_key_overwrites.load()
              << " shallower_overwrites=" << g_tt_telemetry.shallower_overwrites.load()
              << " cross_key_evictions=" << g_tt_telemetry.cross_key_evictions.load()
              << " lock_spins=" << g_tt_telemetry.lock_spins.load()
              << std::endl;
    for (int wi = 0; wi < n_threads; ++wi) {
        char wm_str[16] = "-";
        if (w_res[wi].best_move != 0) native_move_to_uci(w_res[wi].best_move, wm_str);
        std::cout << "forensics_worker id=" << wi
                  << " depth=" << w_res[wi].depth
                  << " score=" << w_res[wi].score
                  << " nodes=" << w_res[wi].nodes
                  << " bestmove=" << wm_str
                  << std::endl;
    }

    if (out_res->best_move == 0) {
        uint16_t lmoves[MAX_MOVES];
        int ln = native_generate_legal_moves(b, lmoves);
        if (ln > 0) out_res->best_move = lmoves[0];
    }

    return 1;
}

// ============================================================================
// LMR Configuration & Telemetry API (Phase 3 v0.52)
// ============================================================================

EXPORT void native_set_lmr_options(bool use_lmr, int min_depth, int move_threshold, int base_reduction) {
    g_use_lmr = use_lmr;
    g_lmr_min_depth = min_depth;
    g_lmr_move_threshold = move_threshold;
    g_lmr_base_reduction = base_reduction;
}

EXPORT void native_reset_lmr_telemetry() {
    g_lmr_eligible_moves = 0;
    g_lmr_reduced_moves = 0;
    g_lmr_researches = 0;
    g_lmr_cutoffs = 0;
}

EXPORT void native_clear_tt() {
    std::memset(g_tt, 0, sizeof(g_tt));
}

EXPORT void native_get_lmr_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_lmr_eligible_moves;
        out_arr[1] = g_lmr_reduced_moves;
        out_arr[2] = g_lmr_researches;
        out_arr[3] = g_lmr_cutoffs;
    }
}

// ============================================================================
// PVS Configuration & Telemetry API (Phase 3 v0.53)
// ============================================================================

EXPORT void native_set_pvs_options(bool use_pvs) {
    g_use_pvs = use_pvs;
}

EXPORT void native_reset_pvs_telemetry() {
    g_pvs_full_window_searches = 0;
    g_pvs_null_window_searches = 0;
    g_pvs_researches = 0;
    g_pvs_cutoffs = 0;
}

EXPORT void native_get_pvs_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_pvs_full_window_searches;
        out_arr[1] = g_pvs_null_window_searches;
        out_arr[2] = g_pvs_researches;
        out_arr[3] = g_pvs_cutoffs;
    }
}

// ============================================================================
// Move Ordering Configuration & Telemetry API (Phase 2 & 3 v0.54)
// ============================================================================

EXPORT void native_set_ordering_options(bool use_killer, bool use_history) {
    g_use_killer_ordering = use_killer;
    g_use_history_ordering = use_history;
}

EXPORT void native_clear_killers() {
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
}

EXPORT void native_clear_history_heuristic() {
    std::memset(g_history_table, 0, sizeof(g_history_table));
}

EXPORT void native_reset_ordering_telemetry() {
    g_ordering_total_cutoffs = 0;
    g_ordering_sum_cutoff_index = 0;
    g_ordering_cutoff_move_1 = 0;
    g_ordering_cutoff_move_2 = 0;
    g_ordering_cutoff_move_3 = 0;
    g_ordering_cutoff_move_4plus = 0;
    g_ordering_cutoff_tt = 0;
    g_ordering_cutoff_killer1 = 0;
    g_ordering_cutoff_killer2 = 0;
    g_ordering_cutoff_history = 0;
    g_ordering_cutoff_captures = 0;
    g_ordering_cutoff_quiet = 0;
}

EXPORT void native_get_ordering_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_ordering_total_cutoffs;
        out_arr[1] = g_ordering_sum_cutoff_index;
        out_arr[2] = g_ordering_cutoff_move_1;
        out_arr[3] = g_ordering_cutoff_move_2;
        out_arr[4] = g_ordering_cutoff_move_3;
        out_arr[5] = g_ordering_cutoff_move_4plus;
        out_arr[6] = g_ordering_cutoff_tt;
        out_arr[7] = g_ordering_cutoff_killer1;
        out_arr[8] = g_ordering_cutoff_killer2;
        out_arr[9] = g_ordering_cutoff_history;
        out_arr[10] = g_ordering_cutoff_captures;
        out_arr[11] = g_ordering_cutoff_quiet;
    }
}

EXPORT uint16_t native_get_killer(int ply, int slot) {
    if (ply >= 0 && ply < MAX_PLY && slot >= 0 && slot < KILLER_SLOTS) {
        return g_killer_moves[ply][slot];
    }
    return 0;
}

EXPORT int native_get_history_score(int side, int from, int to) {
    if (side >= 0 && side < SIDES && from >= 0 && from < SQUARES && to >= 0 && to < SQUARES) {
        return g_history_table[side][from][to];
    }
    return 0;
}

// ============================================================================
// SEE Telemetry & Control Exports (Phase 4 v0.56)
// ============================================================================

EXPORT void native_set_see_ordering(int enable) {
    g_use_see_ordering = (enable != 0);
}

EXPORT void native_set_see_in_quiescence(int enable) {
    g_use_see_in_quiescence = (enable != 0);
}

EXPORT void native_reset_see_telemetry() {
    g_see_total_evaluations = 0;
    g_see_positive_captures = 0;
    g_see_neutral_captures = 0;
    g_see_negative_captures = 0;
    g_see_ordering_inversions = 0;
}

EXPORT void native_get_see_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_see_total_evaluations;
        out_arr[1] = g_see_positive_captures;
        out_arr[2] = g_see_neutral_captures;
        out_arr[3] = g_see_negative_captures;
        out_arr[4] = g_see_ordering_inversions;
    }
}

// ============================================================================
// Milestone P1.2 Control & Telemetry Exports
// ============================================================================
EXPORT void native_set_conthist_mode(int mode) { g_conthist_mode = mode; }
EXPORT void native_set_dynamic_lmr_mode(int mode) { g_dynamic_lmr_mode = mode; }
EXPORT void native_set_eval_mode(int mode) { g_eval_mode = mode; }
EXPORT void native_clear_conthist() {
    std::memset(g_conthist_1ply, 0, sizeof(g_conthist_1ply));
    std::memset(g_conthist_2ply, 0, sizeof(g_conthist_2ply));
}
EXPORT void native_reset_p12_telemetry() {
    native_reset_p11_telemetry();
    g_telemetry_conthist_probes = 0;
    g_telemetry_conthist_cutoffs = 0;
    g_telemetry_dynamic_lmr_reduced = 0;
    g_telemetry_dynamic_lmr_researches = 0;
    g_telemetry_eval_calls = 0;
}
EXPORT void native_get_p12_telemetry(uint64_t* out_arr) {
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
}

// ============================================================================
// Formatting & UCI Helpers
// ============================================================================

EXPORT void native_move_to_uci(uint16_t m, char* out_str) {
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);

    out_str[0] = 'a' + (from % 8);
    out_str[1] = '1' + (from / 8);
    out_str[2] = 'a' + (to % 8);
    out_str[3] = '1' + (to / 8);
    out_str[4] = '\0';

    if (flag == 3) {
        const char pr_chars[4] = { 'n', 'b', 'r', 'q' };
        out_str[4] = pr_chars[promo];
        out_str[5] = '\0';
    }
}

EXPORT uint16_t native_parse_uci(NativeBoard* b, const char* str) {
    if (!str || std::strlen(str) < 4) return 0;
    int f_from = str[0] - 'a';
    int r_from = str[1] - '1';
    int f_to = str[2] - 'a';
    int r_to = str[3] - '1';
    if (f_from < 0 || f_from > 7 || r_from < 0 || r_from > 7 ||
        f_to < 0 || f_to > 7 || r_to < 0 || r_to > 7) {
        return 0;
    }
    int from = r_from * 8 + f_from;
    int to = r_to * 8 + f_to;

    int promo_piece = -1;
    if (str[4] == 'n' || str[4] == 'N') promo_piece = 0;
    else if (str[4] == 'b' || str[4] == 'B') promo_piece = 1;
    else if (str[4] == 'r' || str[4] == 'R') promo_piece = 2;
    else if (str[4] == 'q' || str[4] == 'Q') promo_piece = 3;

    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);
    for (int i = 0; i < n; i++) {
        uint16_t m = moves[i];
        if (move_from(m) == from && move_to(m) == to) {
            if (move_flag(m) == 3) {
                if (move_promo(m) == promo_piece) return m;
            } else {
                return m;
            }
        }
    }
    return 0;
}

// ============================================================================
// Standalone UCI Engine Protocol Loop (Phase E)
// ============================================================================

static void uci_loop() {
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    std::cout << std::unitbuf;

    native_init();
    NativeBoard board;
    const char* STARTPOS_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    native_set_fen(STARTPOS_FEN, &board);

    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream iss(line);
        std::string cmd;
        iss >> cmd;

        if (cmd == "uci") {
            std::cout << "id name Janus Classical X (P1.6 Candidate X11)" << std::endl;
            std::cout << "id author Project Janus Team" << std::endl;
            std::cout << "option name Threads type spin default 1 min 1 max 16" << std::endl;
            std::cout << "option name UCI_LMP type combo default L1 var L0 var L1 var L2 var L3" << std::endl;
            std::cout << "option name UseKillerOrdering type check default true" << std::endl;
            std::cout << "option name UseHistoryOrdering type check default true" << std::endl;
            std::cout << "option name UsePVS type check default false" << std::endl;
            std::cout << "option name UseLMR type check default true" << std::endl;
            std::cout << "option name LMRMinDepth type spin default 3 min 2 max 8" << std::endl;
            std::cout << "option name LMRMoveThreshold type spin default 4 min 2 max 16" << std::endl;
            std::cout << "option name LMRBaseReduction type spin default 1 min 1 max 3" << std::endl;
            std::cout << "option name UseSEEOrdering type check default false" << std::endl;
            std::cout << "option name UseSEEInQuiescence type check default false" << std::endl;
            std::cout << "option name UCI_Variant type combo default X11 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11" << std::endl;
            std::cout << "option name UCI_ContinuationHistory type combo default H3 var H0 var H1 var H2 var H3" << std::endl;
            std::cout << "option name UCI_DynamicLMR type combo default L3 var L0 var L1 var L2 var L3" << std::endl;
            std::cout << "option name UCI_ClassicalEval type combo default E10 var E0 var E1 var E2 var E3 var E4 var E5 var E6 var E7 var E8 var E9 var E10" << std::endl;
            std::cout << "option name UCI_TacticalOrdering type combo default M4 var M0 var M1 var M2 var M3 var M4" << std::endl;
            std::cout << "option name UCI_SingularExtensions type combo default S3 var S0 var S1 var S2 var S3" << std::endl;
            std::cout << "option name UCI_MultiCut type combo default C1 var C0 var C1" << std::endl;
            std::cout << "option name UCI_ProbCut type combo default P3 var P0 var P1 var P2 var P3" << std::endl;
            std::cout << "option name UCI_StagedMovegen type check default true" << std::endl;
            std::cout << "option name UCI_QuiescenceSEE type spin default 2 min 0 max 3" << std::endl;
            std::cout << "option name UCI_NullMovePruning type check default true" << std::endl;
            std::cout << "option name UCI_RFP type check default true" << std::endl;
            std::cout << "option name UCI_AspirationWindow type check default true" << std::endl;
            std::cout << "option name UCI_DynamicTime type check default true" << std::endl;
            std::cout << "option name UCI_PawnHash type check default true" << std::endl;
            std::cout << "uciok" << std::endl;
        } else if (cmd == "isready") {
            std::cout << "readyok" << std::endl;
        } else if (cmd == "setoption") {
            std::string name_tok, opt_name;
            iss >> name_tok >> opt_name;
            if (name_tok == "name") {
                std::string val_tok, opt_val;
                if (iss >> val_tok) {
                    if (val_tok == "value") {
                        iss >> opt_val;
                    } else {
                        opt_val = val_tok;
                    }
                }
                if (opt_name == "Threads" && !opt_val.empty()) {
                    g_num_threads = std::max(1, std::min(16, std::stoi(opt_val)));
                } else if (opt_name == "UCI_LMP" && !opt_val.empty()) {
                    if (opt_val == "L0") { g_use_lmp = false; g_lmp_mode = 0; }
                    else if (opt_val == "L1") { g_use_lmp = true; g_lmp_mode = 1; }
                    else if (opt_val == "L2") { g_use_lmp = true; g_lmp_mode = 2; }
                    else if (opt_val == "L3") { g_use_lmp = true; g_lmp_mode = 3; }
                } else if (opt_name == "UseKillerOrdering") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_killer_ordering = true;
                    } else {
                        g_use_killer_ordering = false;
                    }
                } else if (opt_name == "UseHistoryOrdering") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_history_ordering = true;
                    } else {
                        g_use_history_ordering = false;
                    }
                } else if (opt_name == "UsePVS") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_pvs = true;
                    } else {
                        g_use_pvs = false;
                    }
                } else if (opt_name == "UseLMR") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_lmr = true;
                    } else {
                        g_use_lmr = false;
                    }
                } else if (opt_name == "UseSEEOrdering") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_see_ordering = true;
                    } else {
                        g_use_see_ordering = false;
                    }
                } else if (opt_name == "UseSEEInQuiescence") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_see_in_quiescence = true;
                    } else {
                        g_use_see_in_quiescence = false;
                    }
                } else if (opt_name == "LMRMinDepth" && !opt_val.empty()) {
                    g_lmr_min_depth = std::stoi(opt_val);
                } else if (opt_name == "LMRMoveThreshold" && !opt_val.empty()) {
                    g_lmr_move_threshold = std::stoi(opt_val);
                } else if (opt_name == "LMRBaseReduction" && !opt_val.empty()) {
                    g_lmr_base_reduction = std::stoi(opt_val);
                } else if (opt_name == "UCI_Variant" && !opt_val.empty()) {
                    native_apply_search_variant(opt_val.c_str());
                } else if (opt_name == "UCI_StagedMovegen") {
                    g_use_staged_movegen = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_QuiescenceSEE" && !opt_val.empty()) {
                    g_quiescence_see_mode = std::stoi(opt_val);
                    g_use_see_in_quiescence = (g_quiescence_see_mode > 0);
                } else if (opt_name == "UCI_NullMovePruning") {
                    g_use_null_move_pruning = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_RFP") {
                    g_use_reverse_futility = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_AspirationWindow") {
                    g_use_aspiration_window = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_ContinuationHistory" && !opt_val.empty()) {
                    if (opt_val == "H0") g_conthist_mode = 0;
                    else if (opt_val == "H1") g_conthist_mode = 1;
                    else if (opt_val == "H2") g_conthist_mode = 2;
                    else if (opt_val == "H3") g_conthist_mode = 3;
                } else if (opt_name == "UCI_DynamicLMR" && !opt_val.empty()) {
                    if (opt_val == "L0") g_dynamic_lmr_mode = 0;
                    else if (opt_val == "L1") g_dynamic_lmr_mode = 1;
                    else if (opt_val == "L2") g_dynamic_lmr_mode = 2;
                    else if (opt_val == "L3") g_dynamic_lmr_mode = 3;
                } else if (opt_name == "UCI_ClassicalEval" && !opt_val.empty()) {
                    if (opt_val == "E0") g_eval_mode = 0;
                    else if (opt_val == "E1") g_eval_mode = 1;
                    else if (opt_val == "E2") g_eval_mode = 2;
                    else if (opt_val == "E3") g_eval_mode = 3;
                    else if (opt_val == "E4") g_eval_mode = 4;
                    else if (opt_val == "E5") g_eval_mode = 5;
                    else if (opt_val == "E6") g_eval_mode = 6;
                    else if (opt_val == "E7") g_eval_mode = 7;
                    else if (opt_val == "E8") g_eval_mode = 8;
                    else if (opt_val == "E9") g_eval_mode = 9;
                    else if (opt_val == "E10") g_eval_mode = 10;
                } else if (opt_name == "UCI_DynamicTime" && !opt_val.empty()) {
                    g_dynamic_time_mgmt = (opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_PawnHash" && !opt_val.empty()) {
                    g_use_pawn_hash = (opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_TacticalOrdering" && !opt_val.empty()) {
                    if (opt_val == "M0") g_tactical_ordering_mode = 0;
                    else if (opt_val == "M1") g_tactical_ordering_mode = 1;
                    else if (opt_val == "M2") g_tactical_ordering_mode = 2;
                    else if (opt_val == "M3") g_tactical_ordering_mode = 3;
                    else if (opt_val == "M4") g_tactical_ordering_mode = 4;
                } else if (opt_name == "UCI_SingularExtensions" && !opt_val.empty()) {
                    if (opt_val == "S0") g_singular_extension_mode = 0;
                    else if (opt_val == "S1") g_singular_extension_mode = 1;
                    else if (opt_val == "S2") g_singular_extension_mode = 2;
                    else if (opt_val == "S3") g_singular_extension_mode = 3;
                } else if (opt_name == "UCI_MultiCut" && !opt_val.empty()) {
                    if (opt_val == "C0") g_multicut_mode = 0;
                    else if (opt_val == "C1") g_multicut_mode = 1;
                } else if (opt_name == "UCI_ProbCut" && !opt_val.empty()) {
                    if (opt_val == "P0") g_probcut_mode = 0;
                    else if (opt_val == "P1") g_probcut_mode = 1;
                    else if (opt_val == "P2") g_probcut_mode = 2;
                    else if (opt_val == "P3") g_probcut_mode = 3;
                }
            }
                } else if (cmd == "telemetry_report") {
            std::cout << "TELEMETRY_START" << std::endl;
            std::cout << "variant " << g_search_variant << std::endl;
            std::cout << "movegen_calls " << g_telemetry_movegen_calls << std::endl;
            std::cout << "captures_gen " << g_telemetry_captures_gen << std::endl;
            std::cout << "quiets_gen " << g_telemetry_quiets_gen << std::endl;
            std::cout << "moves_scored " << g_telemetry_moves_scored << std::endl;
            std::cout << "moves_searched " << g_telemetry_moves_searched << std::endl;
            std::cout << "first_move_cutoffs " << g_telemetry_first_move_cutoffs << std::endl;
            std::cout << "total_cutoffs " << g_telemetry_total_cutoffs << std::endl;
            std::cout << "nmp_probes " << g_telemetry_nmp_probes << std::endl;
            std::cout << "nmp_cutoffs " << g_telemetry_nmp_cutoffs << std::endl;
            std::cout << "rfp_probes " << g_telemetry_rfp_probes << std::endl;
            std::cout << "rfp_cutoffs " << g_telemetry_rfp_cutoffs << std::endl;
            std::cout << "aspiration_researches " << g_telemetry_aspiration_researches << std::endl;
            std::cout << "qmoves_pruned " << g_telemetry_qmoves_pruned << std::endl;
            std::cout << "conthist_mode " << g_conthist_mode << std::endl;
            std::cout << "dynamic_lmr_mode " << g_dynamic_lmr_mode << std::endl;
            std::cout << "eval_mode " << g_eval_mode << std::endl;
            std::cout << "conthist_probes " << g_telemetry_conthist_probes << std::endl;
            std::cout << "conthist_cutoffs " << g_telemetry_conthist_cutoffs << std::endl;
            std::cout << "dynamic_lmr_reduced " << g_telemetry_dynamic_lmr_reduced << std::endl;
            std::cout << "eval_calls " << g_telemetry_eval_calls << std::endl;
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
            std::cout << "TELEMETRY_END" << std::endl;
        } else if (cmd == "telemetry_reset") {
            native_reset_p11_telemetry();
            std::cout << "telemetry_reset_ok" << std::endl;
        } else if (cmd == "ucinewgame") {
            native_reset_history();
            native_clear_conthist();
            native_clear_tactical_tables();
            native_clear_killers();
            native_clear_history_heuristic();
            native_reset_ordering_telemetry();
            std::memset(g_tt, 0, sizeof(g_tt));
            g_parallel_tt.clear();
            native_reset_lmr_telemetry();
            native_reset_pvs_telemetry();
            native_reset_see_telemetry();
            native_set_fen(STARTPOS_FEN, &board);
        } else if (cmd == "position") {
            std::string type;
            iss >> type;
            if (type == "startpos") {
                native_set_fen(STARTPOS_FEN, &board);
                native_reset_history();
                native_push_history(board.zobrist_key);

                std::string moves_token;
                if (iss >> moves_token && moves_token == "moves") {
                    std::string m_str;
                    while (iss >> m_str) {
                        uint16_t m = native_parse_uci(&board, m_str.c_str());
                        if (m != 0) {
                            UndoInfo undo;
                            native_make_move(&board, m, &undo);
                            native_push_history(board.zobrist_key);
                        }
                    }
                }
            } else if (type == "fen") {
                std::string fen_part, fen;
                while (iss >> fen_part && fen_part != "moves") {
                    if (!fen.empty()) fen += " ";
                    fen += fen_part;
                }
                native_set_fen(fen.c_str(), &board);
                native_reset_history();
                native_push_history(board.zobrist_key);

                if (fen_part == "moves") {
                    std::string m_str;
                    while (iss >> m_str) {
                        uint16_t m = native_parse_uci(&board, m_str.c_str());
                        if (m != 0) {
                            UndoInfo undo;
                            native_make_move(&board, m, &undo);
                            native_push_history(board.zobrist_key);
                        }
                    }
                }
            }
        } else if (cmd == "go") {
            std::string subcmd;
            int max_depth = 64;
            double time_limit = 1000.0;
            int wtime = -1, btime = -1, winc = 0, binc = 0, movetime = -1;

            int movestogo = -1;
            while (iss >> subcmd) {
                if (subcmd == "depth") iss >> max_depth;
                else if (subcmd == "movetime") { iss >> movetime; time_limit = movetime / 1000.0; }
                else if (subcmd == "wtime") iss >> wtime;
                else if (subcmd == "btime") iss >> btime;
                else if (subcmd == "winc") iss >> winc;
                else if (subcmd == "binc") iss >> binc;
                else if (subcmd == "movestogo") iss >> movestogo;
            }

            // Time Management Policy
            if (movetime < 0) {
                int my_time = (board.side_to_move == WHITE) ? wtime : btime;
                int my_inc = (board.side_to_move == WHITE) ? winc : binc;

                if (my_time > 0) {
                    double alloc_ms;
                    if (g_dynamic_time_mgmt) {
                        int moves_left = (movestogo > 0) ? std::min(movestogo, 40) : 30;
                        alloc_ms = (double)my_time / moves_left + 0.8 * my_inc;
                    } else {
                        alloc_ms = (my_time + 40.0 * my_inc) / 40.0;
                    }
                    if (alloc_ms > my_time - 40.0) alloc_ms = std::max(10.0, my_time - 40.0);
                    time_limit = alloc_ms / 1000.0;
                }
            }

            NativeSearchResult res;
            native_search(&board, max_depth, time_limit, &res);

            char best_uci[16] = {0};
            if (res.best_move != 0) {
                native_move_to_uci(res.best_move, best_uci);
            } else {
                // If search aborted before finding move, pick any legal move
                uint16_t lmoves[MAX_MOVES];
                int ln = native_generate_legal_moves(&board, lmoves);
                if (ln > 0) native_move_to_uci(lmoves[0], best_uci);
                else std::strcpy(best_uci, "0000");
            }

            // Print info
            std::cout << "info depth " << res.depth
                      << " score cp " << res.score
                      << " nodes " << res.nodes
                      << " nps " << (res.elapsed_seconds > 0 ? (int)(res.nodes / res.elapsed_seconds) : 0)
                      << " time " << (int)(res.elapsed_seconds * 1000)
                      << " pv";
            for (int pvi = 0; pvi < res.pv_length; pvi++) {
                char pv_str[16];
                native_move_to_uci(res.pv[pvi], pv_str);
                std::cout << " " << pv_str;
            }
            std::cout << std::endl;

            std::cout << "bestmove " << best_uci << std::endl;
        } else if (cmd == "stop") {
            g_stop_search.store(true, std::memory_order_relaxed);
        } else if (cmd == "quit") {
            g_stop_search.store(true, std::memory_order_relaxed);
            break;
        }
    }
}

#ifndef _WINDLL
int main() {
    uci_loop();
    return 0;
}
#endif
