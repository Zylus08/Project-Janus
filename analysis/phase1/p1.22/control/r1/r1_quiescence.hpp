#pragma once
/**
 * r1_quiescence.hpp
 * Janus Classical R1 — Corrected Tactical Quiescence Search (Q1 Semantics).
 * Implements stand-pat fail-high, check evasion completeness, delta pruning, and SEE filtering.
 */

#include "r1_types.hpp"
#include "r1_telemetry.hpp"
#include "r1_movepicker.hpp"

namespace r1 {

class QuiescenceCore {
public:
    QuiescenceCore(SearchTelemetry& telemetry, const MoveOrderingTables& tables)
        : telemetry_(telemetry), tables_(tables) {}

    int search(NativeBoard* b, int alpha, int beta, int ply) {
        telemetry_.qsearch_nodes++;

        if (ply >= MAX_PLY - 1) {
            return ::native_evaluate(b);
        }

        bool in_check = (::native_is_check(b) != 0);

        // Stand-pat evaluation (only if not in check)
        int stand_pat = -INF;
        if (!in_check) {
            stand_pat = ::native_evaluate(b);
            if (stand_pat >= beta) {
                return stand_pat; // Stand-pat fail-high cutoff
            }
            if (stand_pat > alpha) {
                alpha = stand_pat;
            }
        }

        // Generate legal moves: all legal evasions if in check, captures/promotions otherwise
        MovePicker picker(b, 0, ply, 0, tables_, !in_check);

        int moves_searched = 0;
        uint16_t move = 0;

        while ((move = picker.next_move()) != 0) {
            // Delta pruning (if not in check and not a pawn promotion)
            if (!in_check && move_flag(move) != 3) {
                int to_sq = move_to(move);
                int them = 1 - b->side_to_move;
                int cap_val = 100;
                uint64_t to_bb = 1ULL << to_sq;
                if (b->pieces[them][QUEEN] & to_bb) cap_val = 900;
                else if (b->pieces[them][ROOK] & to_bb) cap_val = 500;
                else if (b->pieces[them][BISHOP] & to_bb) cap_val = 325;
                else if (b->pieces[them][KNIGHT] & to_bb) cap_val = 320;

                if (stand_pat + cap_val + 200 < alpha) {
                    continue; // Even with capture + 200 cp safety margin, cannot raise alpha
                }
            }

            UndoInfo undo;
            ::native_make_move(b, move, &undo);
            moves_searched++;

            int score = -search(b, -beta, -alpha, ply + 1);

            ::native_unmake_move(b, move, &undo);

            if (score >= beta) {
                return score; // Beta cutoff
            }
            if (score > alpha) {
                alpha = score;
            }
        }

        // If in check and no legal moves exist, it is checkmate
        if (in_check && moves_searched == 0) {
            return -MATE_SCORE + ply;
        }

        return alpha;
    }

private:
    SearchTelemetry& telemetry_;
    const MoveOrderingTables& tables_;
};

} // namespace r1
