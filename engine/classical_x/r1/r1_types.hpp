#pragma once
/**
 * r1_types.hpp
 * Janus Classical R1 — Core Types, Constants, and Search Configuration.
 */

#include <cstdint>
#include <algorithm>
#include <chrono>
#include <vector>
#include <string>

namespace r1 {

// Search score limits
constexpr int INF = 30000;
constexpr int MATE_SCORE = 29000;
constexpr int MATE_THRESHOLD = 28000;
constexpr int MAX_PLY = 128;
constexpr int MAX_MOVES = 256;

// Node classifications for formal contracts
enum NodeType : uint8_t {
    NODE_PV = 0,   // beta - alpha > 1 (open window, zero heuristic pruning)
    NODE_CUT = 1,  // beta - alpha == 1, expected fail-high
    NODE_ALL = 2   // beta - alpha == 1, expected fail-low
};

// Transposition table flags
enum TTFlag : uint8_t {
    TT_NONE = 0,
    TT_EXACT = 1,
    TT_LOWER = 2,  // Fail-high bound (score >= beta)
    TT_UPPER = 3   // Fail-low bound  (score <= alpha)
};

// Search result payload
struct SearchResult {
    uint16_t best_move = 0;
    int score = 0;
    int depth = 0;
    int completed_depth = 0;
    uint64_t nodes = 0;
    uint64_t main_nodes = 0;
    uint64_t qsearch_nodes = 0;
    double elapsed_ms = 0.0;
    int pv_length = 0;
    uint16_t pv[MAX_PLY] = {0};
    bool aborted = false;
};

// Search configuration options (strictly non-ML)
struct SearchConfig {
    bool full_width_minimax_mode = false; // Phase 3: exact minimax verification
    bool use_pvs = true;                  // Phase 5: Principal Variation Search
    bool use_aspiration_window = true;    // Phase 5: Aspiration windows
    int aspiration_delta = 25;            // 25 cp initial aspiration margin
    bool use_qsearch = true;              // Phase 6: Quiescence search
    bool use_tt = true;                   // Phase 4: Transposition table
    bool use_nmp = true;                  // Phase 10: Null Move Pruning
    int nmp_base_reduction = 2;           // R = 2 + depth / 6
    bool use_rfp = true;                  // Phase 10: Reverse Futility Pruning
    int rfp_margin_per_depth = 120;       // 120 cp / ply
    bool use_lmr = true;                  // Phase 10: Late Move Reductions
    bool use_lmp = true;                  // Phase 10: Late Move Pruning
    int lmp_max_depth = 3;                // LMP active up to depth 3
};

// Mate score normalization to make TT entries depth-independent
inline int score_to_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_PLY) return score + ply;
    if (score <= -MATE_SCORE + MAX_PLY) return score - ply;
    return score;
}

inline int score_from_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_PLY) return score - ply;
    if (score <= -MATE_SCORE + MAX_PLY) return score + ply;
    return score;
}

} // namespace r1
