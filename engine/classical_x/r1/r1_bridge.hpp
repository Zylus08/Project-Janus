#pragma once
/**
 * r1_bridge.hpp
 * Janus Classical R1 — C-Linkage Bridge and Search Controller.
 * Bridges R1 search core with NativeBoard, UCI loop, and Python ctypes testing harness.
 */

#include "r1_types.hpp"
#include "r1_telemetry.hpp"
#include "r1_tt.hpp"
#include "r1_movepicker.hpp"
#include "r1_quiescence.hpp"
#include "r1_search.hpp"

#include <memory>
#include <iostream>

namespace r1 {

class R1EngineInstance {
public:
    R1EngineInstance() 
        : tt_(32), telemetry_(), config_(), core_(tt_, telemetry_, config_) {}

    TranspositionTable& tt() { return tt_; }
    SearchTelemetry& telemetry() { return telemetry_; }
    SearchConfig& config() { return config_; }
    SearchCore& core() { return core_; }

    void resize_tt(size_t mb) {
        tt_.resize(mb);
    }

    void clear() {
        tt_.clear();
        telemetry_.reset();
        core_.clear_tables();
    }

private:
    TranspositionTable tt_;
    SearchTelemetry telemetry_;
    SearchConfig config_;
    SearchCore core_;
};

static R1EngineInstance g_r1_engine;

} // namespace r1

// Forward declare UCI formatting
void native_move_to_uci(uint16_t m, char* out_str);

// ============================================================================
// Exported C-Linkage API for Python Test Suites and UCI Engine
// ============================================================================

EXPORT int native_r1_full_width_minimax(NativeBoard* b, int depth, int alpha, int beta, uint16_t* out_best_move) {
    return r1::g_r1_engine.core().full_width_minimax(b, depth, alpha, beta, 0, out_best_move);
}

EXPORT void native_r1_set_config(
    int full_width_mode,
    int use_pvs,
    int use_aspiration,
    int use_qsearch,
    int use_tt,
    int use_nmp,
    int use_rfp,
    int use_lmr,
    int use_lmp
) {
    r1::SearchConfig cfg;
    cfg.full_width_minimax_mode = (full_width_mode != 0);
    cfg.use_pvs = (use_pvs != 0);
    cfg.use_aspiration_window = (use_aspiration != 0);
    cfg.use_qsearch = (use_qsearch != 0);
    cfg.use_tt = (use_tt != 0);
    cfg.use_nmp = (use_nmp != 0);
    cfg.use_rfp = (use_rfp != 0);
    cfg.use_lmr = (use_lmr != 0);
    cfg.use_lmp = (use_lmp != 0);
    r1::g_r1_engine.config() = cfg;
    r1::g_r1_engine.core().set_config(cfg);
}

EXPORT void native_r1_clear_tt() {
    r1::g_r1_engine.clear();
}

EXPORT void native_r1_get_telemetry(
    uint64_t* main_nodes,
    uint64_t* qsearch_nodes,
    uint64_t* tt_probes,
    uint64_t* tt_hits,
    uint64_t* tt_cutoffs,
    uint64_t* nmp_cutoffs,
    uint64_t* rfp_cutoffs,
    uint64_t* lmr_researches,
    uint64_t* lmp_cutoffs
) {
    const auto& tel = r1::g_r1_engine.telemetry();
    if (main_nodes) *main_nodes = tel.main_nodes;
    if (qsearch_nodes) *qsearch_nodes = tel.qsearch_nodes;
    if (tt_probes) *tt_probes = tel.tt_probes;
    if (tt_hits) *tt_hits = tel.tt_hits;
    if (tt_cutoffs) *tt_cutoffs = tel.tt_cutoffs;
    if (nmp_cutoffs) *nmp_cutoffs = tel.nmp_cutoffs;
    if (rfp_cutoffs) *rfp_cutoffs = tel.rfp_cutoffs;
    if (lmr_researches) *lmr_researches = tel.lmr_researches;
    if (lmp_cutoffs) *lmp_cutoffs = tel.lmp_cutoffs;
}

// Formal TT Contract Tests (TT0, TT1, TT2)
EXPORT int native_r1_test_tt_contract(int contract_id) {
    // contract_id:
    // 0 = TT0 (Exact / Bound cutoff test)
    // 1 = TT1 (Upper-bound conflict precedence)
    // 2 = TT2 (Store and retrieve with ply normalization)
    r1::TranspositionTable tt(4); // 4 MB table
    uint64_t test_key = 0x123456789ABCDEF0ULL;
    uint16_t test_move = encode_move(12, 28, 0, 0); // e2e4

    if (contract_id == 0) {
        // TT0 Test: Exact match cutoffs (tested at ply 1 where cutoffs are permitted)
        tt.store(test_key, 150, 4, r1::TT_EXACT, 1, test_move);
        int out_score = 0;
        uint16_t out_move = 0;
        bool cutoff = tt.probe(test_key, 4, 1, 100, 200, out_score, out_move, true);
        if (!cutoff || out_score != 150 || out_move != test_move) return 101; // Failed

        // Lower bound cutoff (score >= beta)
        tt.store(test_key, 250, 4, r1::TT_LOWER, 1, test_move);
        cutoff = tt.probe(test_key, 4, 1, 100, 200, out_score, out_move, true);
        if (!cutoff || out_score != 250) return 102; // Failed lower cutoff

        // Upper bound cutoff (score <= alpha)
        tt.store(test_key, 50, 4, r1::TT_UPPER, 1, test_move);
        cutoff = tt.probe(test_key, 4, 1, 100, 200, out_score, out_move, true);
        if (!cutoff || out_score != 50) return 103; // Failed upper cutoff

        return 0; // Success
    } else if (contract_id == 1) {
        // TT1 Test: Bound precedence over static evaluation
        tt.store(test_key, 100, 4, r1::TT_UPPER, 0, test_move);
        r1::TTEntry entry;
        int out_score = 0;
        uint16_t out_move = 0;
        tt.probe(test_key, 4, 0, 150, 250, out_score, out_move, false, &entry);
        if (entry.key != test_key || entry.flag != r1::TT_UPPER) return 201;
        int tt_s = r1::score_from_tt(entry.score, 0);
        // An RFP attempt with beta = 200 should notice entry.flag == TT_UPPER && tt_s < beta (100 < 200)
        if (entry.flag == r1::TT_UPPER && tt_s < 200) {
            return 0; // Successfully detected contradiction
        }
        return 202;
    } else if (contract_id == 2) {
        // TT2 Test: Mate score normalization across plies
        int raw_mate = r1::MATE_SCORE - 4; // Mate in 4
        tt.store(test_key, raw_mate, 4, r1::TT_EXACT, 2, test_move); // Stored at ply 2
        int out_score = 0;
        uint16_t out_move = 0;
        tt.probe(test_key, 4, 6, -r1::INF, r1::INF, out_score, out_move, true); // Probed at ply 6
        // Stored value in TT was raw_mate + 2. When probed at ply 6, should return (raw_mate + 2) - 6 = raw_mate - 4.
        if (out_score != raw_mate - 4) return 301;
        return 0; // Success
    }
    return -1;
}

EXPORT void native_r1_search(
    NativeBoard* b,
    int max_depth,
    double time_limit_sec,
    NativeSearchResult* out_res
) {
    int allocated_ms = static_cast<int>(time_limit_sec * 1000.0);
    auto res = r1::g_r1_engine.core().search_root(b, max_depth, allocated_ms);

    if (out_res) {
        out_res->best_move = res.best_move;
        out_res->score = res.score;
        out_res->depth = res.completed_depth > 0 ? res.completed_depth : res.depth;
        out_res->nodes = res.nodes;
        out_res->elapsed_seconds = res.elapsed_ms / 1000.0;
        out_res->pv_length = res.pv_length;
        for (int i = 0; i < res.pv_length; ++i) {
            out_res->pv[i] = res.pv[i];
        }
    }

    // Print UCI info lines
    char move_str[16] = {0};
    native_move_to_uci(res.best_move, move_str);

    int nps = (res.elapsed_ms > 0) ? static_cast<int>((res.nodes * 1000.0) / res.elapsed_ms) : 0;
    std::cout << "info depth " << (res.completed_depth > 0 ? res.completed_depth : res.depth)
              << " score cp " << res.score
              << " nodes " << res.nodes
              << " nps " << nps
              << " time " << static_cast<int>(res.elapsed_ms)
              << " pv ";
    for (int i = 0; i < res.pv_length; ++i) {
        char pv_str[16] = {0};
        native_move_to_uci(res.pv[i], pv_str);
        std::cout << pv_str << " ";
    }
    std::cout << std::endl;
}
