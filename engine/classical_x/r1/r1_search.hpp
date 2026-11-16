#pragma once
/**
 * r1_search.hpp
 * Janus Classical R1 — Modular Alpha-Beta Search Core.
 * Implements pure full-width minimax, contract-bound PVS, aspiration windows, and completed-iteration safety.
 */

#include "r1_types.hpp"
#include "r1_telemetry.hpp"
#include "r1_tt.hpp"
#include "r1_movepicker.hpp"
#include "r1_quiescence.hpp"
#include "r1_nnue.hpp"

#include <chrono>
#include <iostream>

namespace r1 {

class SearchCore {
public:
    SearchCore(TranspositionTable& tt, SearchTelemetry& telemetry, const SearchConfig& config = SearchConfig{})
        : tt_(tt), telemetry_(telemetry), config_(config), quiescence_(telemetry, tables_, config) {}

    void set_config(const SearchConfig& cfg) {
        config_ = cfg;
        quiescence_.set_config(cfg);
    }
    const SearchConfig& config() const { return config_; }

    inline int evaluate_position(const NativeBoard* b) const {
        if (config_.eval_mode == EVAL_CLASSICAL) {
            return ::native_evaluate(b);
        }
        int nnue_score = NNUEEvaluator::evaluate_full(b);
        if (config_.eval_mode == EVAL_NNUE) {
            return nnue_score;
        }
        int classical_score = ::native_evaluate(b);
        int w = config_.hybrid_nnue_weight;
        return (w * nnue_score + (100 - w) * classical_score) / 100;
    }

    void clear_tables() {
        tables_.clear();
    }

    void request_stop() {
        stop_requested_ = true;
    }

    // ========================================================================
    // Phase 3: Pure Full-Width Negamax (Exact Minimax Correctness Reference)
    // Zero pruning, zero TT, zero qsearch. Exact mathematical minimax reference.
    // ========================================================================
    int full_width_minimax(NativeBoard* b, int depth, int alpha, int beta, int ply, uint16_t* best_move = nullptr) {
        telemetry_.main_nodes++;

        if (depth <= 0) {
            return evaluate_position(b);
        }

        uint16_t legals[MAX_MOVES];
        int count = ::native_generate_legal_moves(b, legals);

        if (count == 0) {
            if (::native_is_check(b)) {
                return -MATE_SCORE + ply; // Checkmate
            }
            return 0; // Stalemate
        }

        int best_score = -INF;
        uint16_t local_best = 0;

        for (int i = 0; i < count; ++i) {
            UndoInfo undo;
            ::native_make_move(b, legals[i], &undo);

            int score = -full_width_minimax(b, depth - 1, -beta, -alpha, ply + 1);

            ::native_unmake_move(b, legals[i], &undo);

            if (score > best_score) {
                best_score = score;
                local_best = legals[i];
            }
            if (score > alpha) {
                alpha = score;
            }
            if (alpha >= beta) {
                break; // Alpha-beta pruning invariant
            }
        }

        if (best_move) *best_move = local_best;
        return best_score;
    }

    // ========================================================================
    // Production Alpha-Beta Recursive Search (PVS + Formal Contracts)
    // ========================================================================
    int negamax(NativeBoard* b, int depth, int alpha, int beta, int ply, bool is_pv, uint16_t excluded_move = 0) {
        telemetry_.main_nodes++;

        if (stop_requested_) return 0;

        // Periodic time check every 2048 nodes
        if ((telemetry_.main_nodes & 2047) == 0 && has_deadline_) {
            if (std::chrono::steady_clock::now() >= deadline_) {
                stop_requested_ = true;
                return 0;
            }
        }

        if (ply >= MAX_PLY - 1) {
            return evaluate_position(b);
        }

        // Base case: Quiescence search
        if (depth <= 0) {
            if (config_.use_qsearch) {
                return quiescence_.search(b, alpha, beta, ply);
            } else {
                return evaluate_position(b);
            }
        }

        bool in_check = (::native_is_check(b) != 0);

        // Check extension: preserve tactical depth when in check
        if (in_check) {
            depth++;
        }

        int orig_alpha = alpha;
        uint16_t tt_move = 0;
        int tt_score = 0;
        TTEntry tt_entry{};
        bool has_tt_entry = false;

        // TT0 Contract: probe with depth and bound validation
        if (config_.use_tt) {
            telemetry_.tt_probes++;
            bool tt_cutoff = tt_.probe(b->zobrist_key, depth, ply, alpha, beta,
                                       tt_score, tt_move, !is_pv && excluded_move == 0, &tt_entry);
            if (tt_entry.key == b->zobrist_key) {
                has_tt_entry = true;
                telemetry_.tt_hits++;
            }
            if (tt_cutoff) {
                telemetry_.tt_cutoffs++;
                return tt_score;
            }
        }

        // ====================================================================
        // Selectivity Heuristics (Strictly Non-PV, ply > 0, !in_check)
        // ====================================================================
        if (!is_pv && ply > 0 && !in_check && excluded_move == 0) {
            int static_eval = evaluate_position(b);

            // 1. Reverse Futility Pruning (RFP) with Formal Contract Guard
            if (config_.use_rfp && depth <= 3 && std::abs(beta) < MATE_THRESHOLD) {
                // TT1 Contract: respect prior TT upper bound proof
                bool tt_contradiction = (has_tt_entry && tt_entry.flag == TT_UPPER &&
                                         score_from_tt(tt_entry.score, ply) < beta);

                if (!tt_contradiction) {
                    telemetry_.rfp_probes++;
                    int margin = config_.rfp_margin_per_depth * depth;
                    if (static_eval - margin >= beta) {
                        telemetry_.rfp_cutoffs++;
                        // TT2 Contract: store lower bound on cutoff
                        if (config_.use_tt) {
                            tt_.store(b->zobrist_key, static_eval, (int8_t)depth, TT_LOWER, ply, 0);
                        }
                        return static_eval;
                    }
                }
            }

            // 2. Null-Move Pruning (NMP) with Non-Pawn Material Guard
            if (config_.use_nmp && depth >= 3 && std::abs(beta) < MATE_THRESHOLD) {
                int us = b->side_to_move;
                uint64_t my_non_pawns = b->pieces[us][KNIGHT] | b->pieces[us][BISHOP] |
                                        b->pieces[us][ROOK]   | b->pieces[us][QUEEN];
                if (my_non_pawns != 0 && static_eval >= beta) {
                    telemetry_.nmp_probes++;
                    int r = config_.nmp_base_reduction + (depth / 6);

                    // Execute null move
                    b->side_to_move = 1 - us;
                    b->zobrist_key ^= 0x1ULL; // toggle side
                    uint8_t old_ep = b->ep_square;
                    b->ep_square = 64;

                    int null_score = -negamax(b, depth - 1 - r, -beta, -beta + 1, ply + 1, false);

                    // Revert null move
                    b->side_to_move = us;
                    b->zobrist_key ^= 0x1ULL;
                    b->ep_square = old_ep;

                    if (stop_requested_) return 0;

                    if (null_score >= beta) {
                        telemetry_.nmp_cutoffs++;
                        return null_score;
                    }
                }
            }
        }

        // ====================================================================
        // Move Ordering & PVS Search Loop
        // ====================================================================
        MovePicker picker(b, tt_move, ply, prev_moves_[ply], tables_);

        int moves_searched = 0;
        int best_score = -INF;
        uint16_t best_move = 0;
        uint16_t move = 0;

        while ((move = picker.next_move()) != 0) {
            if (move == excluded_move) continue;

            // Late Move Pruning (LMP) at shallow non-PV cut nodes
            if (config_.use_lmp && !is_pv && !in_check && depth <= config_.lmp_max_depth) {
                int lmp_threshold = 3 + 3 * depth * depth;
                if (moves_searched >= lmp_threshold) {
                    telemetry_.lmp_cutoffs++;
                    break; // Prune remaining quiet branches
                }
            }

            UndoInfo undo;
            ::native_make_move(b, move, &undo);
            prev_moves_[ply + 1] = move;
            moves_searched++;

            int score = 0;

            // Principal Variation Search (PVS)
            if (moves_searched == 1) {
                // First move (PV candidate): full window
                score = -negamax(b, depth - 1, -beta, -alpha, ply + 1, is_pv);
            } else {
                // Subsequent moves: Late Move Reductions (LMR)
                int to_sq = move_to(move);
                int them = 1 - b->side_to_move;
                bool is_cap = ((b->occupancy[them] & (1ULL << to_sq)) != 0) || (move_flag(move) == 2);
                bool is_killer = (ply < MAX_PLY && (move == tables_.killers[ply][0] || move == tables_.killers[ply][1]));

                int reduction = 0;
                if (config_.use_lmr && moves_searched >= 4 && depth >= 3 && !in_check && !is_cap && !is_killer) {
                    reduction = 1 + (moves_searched >= 8 ? 1 : 0);
                    telemetry_.lmr_probes++;
                }

                // Null-window search with reduction
                score = -negamax(b, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1, false);

                // Re-search if failed high out of reduction
                if (reduction > 0 && score > alpha) {
                    telemetry_.lmr_researches++;
                    score = -negamax(b, depth - 1, -alpha - 1, -alpha, ply + 1, false);
                }

                // Re-search with full window if failed high inside PV node
                if (is_pv && score > alpha && score < beta) {
                    score = -negamax(b, depth - 1, -beta, -alpha, ply + 1, true);
                }
            }

            ::native_unmake_move(b, move, &undo);

            if (stop_requested_) return 0;

            if (score > best_score) {
                best_score = score;
                best_move = move;
            }

            if (score > alpha) {
                alpha = score;
            }

            if (alpha >= beta) {
                // Beta cutoff! Update move ordering heuristics
                int us = b->side_to_move;
                int to_sq = move_to(move);
                bool is_cap = ((b->occupancy[1 - us] & (1ULL << to_sq)) != 0) || (move_flag(move) == 2);
                if (!is_cap) {
                    tables_.update_killer(ply, move);
                    if (ply > 0) {
                        tables_.update_countermove(prev_moves_[ply], move);
                    }
                    tables_.update_history(us, move, depth * depth);
                }

                // TT2 Contract: store lower bound
                if (config_.use_tt) {
                    tt_.store(b->zobrist_key, score, (int8_t)depth, TT_LOWER, ply, move);
                }
                return score;
            }
        }

        // Terminal position checks
        if (moves_searched == 0) {
            if (in_check) {
                return -MATE_SCORE + ply; // Checkmate
            }
            return 0; // Stalemate
        }

        // TT2 Contract: store exact or upper bound
        if (config_.use_tt && !stop_requested_) {
            uint8_t flag = (best_score <= orig_alpha) ? TT_UPPER : TT_EXACT;
            tt_.store(b->zobrist_key, best_score, (int8_t)depth, flag, ply, best_move);
        }

        return best_score;
    }

    // ========================================================================
    // Root Search: Iterative Deepening & Aspiration Windows
    // ========================================================================
    SearchResult search_root(NativeBoard* b, int max_depth, int allocated_ms = 0) {
        stop_requested_ = false;
        has_deadline_ = (allocated_ms > 0);
        auto start_time = std::chrono::steady_clock::now();
        if (has_deadline_) {
            deadline_ = start_time + std::chrono::milliseconds(allocated_ms);
        }

        SearchResult result{};
        int best_score = 0;
        uint16_t root_best_move = 0;

        // Extract root legal moves to verify move availability
        uint16_t root_legals[MAX_MOVES];
        int root_move_count = ::native_generate_legal_moves(b, root_legals);
        if (root_move_count == 0) {
            result.score = ::native_is_check(b) ? -MATE_SCORE : 0;
            return result;
        }

        tt_.new_search();
        telemetry_.reset();

        for (int depth = 1; depth <= max_depth; ++depth) {
            int score = 0;

            if (config_.use_aspiration_window && depth >= 4) {
                int delta = config_.aspiration_delta;
                int alpha = std::max(-INF, best_score - delta);
                int beta = std::min(INF, best_score + delta);

                while (!stop_requested_) {
                    score = negamax(b, depth, alpha, beta, 0, true);

                    if (stop_requested_) break;

                    if (score <= alpha) {
                        telemetry_.aspiration_researches++;
                        alpha = std::max(-INF, alpha - delta * 2);
                        delta += delta / 2;
                    } else if (score >= beta) {
                        telemetry_.aspiration_researches++;
                        beta = std::min(INF, beta + delta * 2);
                        delta += delta / 2;
                    } else {
                        break; // Inside aspiration window
                    }
                }
            } else {
                score = negamax(b, depth, -INF, INF, 0, true);
            }

            if (stop_requested_) {
                result.aborted = true;
                break; // Preserve completed_depth from previous iteration
            }

            // Completed iteration! Update authoritative result
            best_score = score;
            result.completed_depth = depth;
            result.depth = depth;
            result.score = best_score;

            // Probe TT for root best move
            uint16_t probed_move = 0;
            int dummy_s = 0;
            tt_.probe(b->zobrist_key, depth, 0, -INF, INF, dummy_s, probed_move, false);
            if (probed_move != 0) {
                root_best_move = probed_move;
            } else if (root_best_move == 0) {
                root_best_move = root_legals[0];
            }
            result.best_move = root_best_move;

            auto now = std::chrono::steady_clock::now();
            result.elapsed_ms = std::chrono::duration<double, std::milli>(now - start_time).count();
            result.nodes = telemetry_.total_nodes();
            result.main_nodes = telemetry_.main_nodes;
            result.qsearch_nodes = telemetry_.qsearch_nodes;

            // Collect PV from TT
            extract_pv(b, depth, result.pv, result.pv_length);

            // Hard time limit: stop if >= 60% of time used to avoid timeout on next ply
            if (has_deadline_ && (result.elapsed_ms >= 0.6 * allocated_ms)) {
                break;
            }
        }

        result.nodes = telemetry_.total_nodes();
        result.main_nodes = telemetry_.main_nodes;
        result.qsearch_nodes = telemetry_.qsearch_nodes;
        return result;
    }

private:
    TranspositionTable& tt_;
    SearchTelemetry& telemetry_;
    SearchConfig config_;
    MoveOrderingTables tables_;
    QuiescenceCore quiescence_;

    uint16_t prev_moves_[MAX_PLY] = {0};
    bool stop_requested_ = false;
    bool has_deadline_ = false;
    std::chrono::steady_clock::time_point deadline_;

    void extract_pv(NativeBoard* b, int max_depth, uint16_t* out_pv, int& out_len) {
        out_len = 0;
        uint64_t visited_keys[MAX_PLY] = {0};
        NativeBoard temp = *b;

        for (int d = 0; d < max_depth && d < MAX_PLY; ++d) {
            uint16_t m = 0;
            int dummy_score = 0;
            tt_.probe(temp.zobrist_key, 0, 0, -INF, INF, dummy_score, m, false);
            if (m == 0) break;

            // Check cycle
            bool cycle = false;
            for (int k = 0; k < d; ++k) {
                if (visited_keys[k] == temp.zobrist_key) { cycle = true; break; }
            }
            if (cycle) break;

            visited_keys[d] = temp.zobrist_key;
            out_pv[out_len++] = m;

            UndoInfo undo;
            ::native_make_move(&temp, m, &undo);
        }
    }
};

} // namespace r1
