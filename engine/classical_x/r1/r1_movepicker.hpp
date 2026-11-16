#pragma once
/**
 * r1_movepicker.hpp
 * Janus Classical R1 — Staged Move Ordering State Machine.
 * Orders moves cleanly: TT Move -> Good Captures (SEE >= 0) -> Killers -> Countermoves -> Quiets (History) -> Bad Captures.
 */

#include "r1_types.hpp"
#include <cstdint>
#include <algorithm>

namespace r1 {

// Move ordering tables owned by search instance
struct MoveOrderingTables {
    int history[2][64][64] = {{{0}}};
    uint16_t killers[MAX_PLY][2] = {{0}};
    uint16_t countermoves[64][64] = {{0}};

    void clear() {
        std::memset(history, 0, sizeof(history));
        std::memset(killers, 0, sizeof(killers));
        std::memset(countermoves, 0, sizeof(countermoves));
    }

    void update_killer(int ply, uint16_t m) {
        if (ply >= MAX_PLY || m == 0) return;
        if (killers[ply][0] != m) {
            killers[ply][1] = killers[ply][0];
            killers[ply][0] = m;
        }
    }

    void update_countermove(uint16_t prev_move, uint16_t best_move) {
        if (prev_move == 0 || best_move == 0) return;
        int from = move_from(prev_move);
        int to = move_to(prev_move);
        countermoves[from][to] = best_move;
    }

    void update_history(int side, uint16_t m, int bonus) {
        int from = move_from(m);
        int to = move_to(m);
        // Bound history values to [-16384, 16384] to prevent overflow
        history[side][from][to] = std::clamp(history[side][from][to] + bonus, -16384, 16384);
    }
};

enum PickerStage : uint8_t {
    STAGE_TT = 0,
    STAGE_GEN_ALL = 1,
    STAGE_GOOD_CAPTURES = 2,
    STAGE_KILLER1 = 3,
    STAGE_KILLER2 = 4,
    STAGE_COUNTERMOVE = 5,
    STAGE_QUIETS = 6,
    STAGE_BAD_CAPTURES = 7,
    STAGE_DONE = 8
};

struct ScoredMove {
    uint16_t move = 0;
    int score = 0;
};

class MovePicker {
public:
    MovePicker(NativeBoard* b, uint16_t tt_move, int ply, uint16_t prev_move,
               const MoveOrderingTables& tables, bool captures_only = false)
        : board_(b), tt_move_(tt_move), ply_(ply), prev_move_(prev_move),
          tables_(tables), captures_only_(captures_only) {
        stage_ = (tt_move_ != 0 && !captures_only_) ? STAGE_TT : STAGE_GEN_ALL;
    }

    uint16_t next_move() {
        while (stage_ != STAGE_DONE) {
            switch (stage_) {
                case STAGE_TT: {
                    stage_ = STAGE_GEN_ALL;
                    // Verify tt_move legality
                    if (is_legal(tt_move_)) {
                        yielded_moves_[yielded_count_++] = tt_move_;
                        return tt_move_;
                    }
                    break;
                }
                case STAGE_GEN_ALL: {
                    move_count_ = ::native_generate_legal_moves(board_, raw_moves_);
                    if (move_count_ == 0) {
                        stage_ = STAGE_DONE;
                        return 0;
                    }

                    // Score and classify moves
                    good_cap_count_ = 0;
                    bad_cap_count_ = 0;
                    quiet_count_ = 0;

                    int us = board_->side_to_move;
                    int them = 1 - us;
                    uint64_t enemies = board_->occupancy[them];

                    for (int i = 0; i < move_count_; ++i) {
                        uint16_t m = raw_moves_[i];
                        if (was_yielded(m)) continue;

                        int to_sq = move_to(m);
                        bool is_cap = ((enemies & (1ULL << to_sq)) != 0) || (move_flag(m) == 2);
                        bool is_promo = (move_flag(m) == 3);

                        if (is_cap || is_promo) {
                            int see_val = ::janus_see(board_, m);
                            int mvv_lva = get_mvv_lva(m);
                            if (see_val >= 0) {
                                good_caps_[good_cap_count_++] = {m, 100000 + mvv_lva + see_val};
                            } else {
                                bad_caps_[bad_cap_count_++] = {m, -100000 + see_val};
                            }
                        } else if (!captures_only_) {
                            int hist = tables_.history[us][move_from(m)][to_sq];
                            quiets_[quiet_count_++] = {m, hist};
                        }
                    }

                    stage_ = STAGE_GOOD_CAPTURES;
                    curr_idx_ = 0;
                    break;
                }
                case STAGE_GOOD_CAPTURES: {
                    if (curr_idx_ < good_cap_count_) {
                        pick_best(good_caps_, good_cap_count_, curr_idx_);
                        uint16_t m = good_caps_[curr_idx_++].move;
                        yielded_moves_[yielded_count_++] = m;
                        return m;
                    }
                    if (captures_only_) {
                        stage_ = STAGE_DONE;
                        return 0;
                    }
                    stage_ = STAGE_KILLER1;
                    break;
                }
                case STAGE_KILLER1: {
                    stage_ = STAGE_KILLER2;
                    if (ply_ < MAX_PLY) {
                        uint16_t k1 = tables_.killers[ply_][0];
                        if (k1 != 0 && !was_yielded(k1) && is_in_raw(k1)) {
                            yielded_moves_[yielded_count_++] = k1;
                            return k1;
                        }
                    }
                    break;
                }
                case STAGE_KILLER2: {
                    stage_ = STAGE_COUNTERMOVE;
                    if (ply_ < MAX_PLY) {
                        uint16_t k2 = tables_.killers[ply_][1];
                        if (k2 != 0 && !was_yielded(k2) && is_in_raw(k2)) {
                            yielded_moves_[yielded_count_++] = k2;
                            return k2;
                        }
                    }
                    break;
                }
                case STAGE_COUNTERMOVE: {
                    stage_ = STAGE_QUIETS;
                    curr_idx_ = 0;
                    if (prev_move_ != 0) {
                        uint16_t cm = tables_.countermoves[move_from(prev_move_)][move_to(prev_move_)];
                        if (cm != 0 && !was_yielded(cm) && is_in_raw(cm)) {
                            yielded_moves_[yielded_count_++] = cm;
                            return cm;
                        }
                    }
                    break;
                }
                case STAGE_QUIETS: {
                    while (curr_idx_ < quiet_count_) {
                        pick_best(quiets_, quiet_count_, curr_idx_);
                        uint16_t m = quiets_[curr_idx_++].move;
                        if (!was_yielded(m)) {
                            yielded_moves_[yielded_count_++] = m;
                            return m;
                        }
                    }
                    stage_ = STAGE_BAD_CAPTURES;
                    curr_idx_ = 0;
                    break;
                }
                case STAGE_BAD_CAPTURES: {
                    while (curr_idx_ < bad_cap_count_) {
                        pick_best(bad_caps_, bad_cap_count_, curr_idx_);
                        uint16_t m = bad_caps_[curr_idx_++].move;
                        if (!was_yielded(m)) {
                            yielded_moves_[yielded_count_++] = m;
                            return m;
                        }
                    }
                    stage_ = STAGE_DONE;
                    break;
                }
                default:
                    stage_ = STAGE_DONE;
                    break;
            }
        }
        return 0;
    }

private:
    NativeBoard* board_;
    uint16_t tt_move_ = 0;
    int ply_ = 0;
    uint16_t prev_move_ = 0;
    const MoveOrderingTables& tables_;
    bool captures_only_ = false;

    PickerStage stage_ = STAGE_TT;
    int curr_idx_ = 0;

    int move_count_ = 0;
    uint16_t raw_moves_[MAX_MOVES] = {0};

    int yielded_count_ = 0;
    uint16_t yielded_moves_[MAX_MOVES] = {0};

    int good_cap_count_ = 0;
    ScoredMove good_caps_[MAX_MOVES];

    int bad_cap_count_ = 0;
    ScoredMove bad_caps_[MAX_MOVES];

    int quiet_count_ = 0;
    ScoredMove quiets_[MAX_MOVES];

    bool was_yielded(uint16_t m) const {
        for (int i = 0; i < yielded_count_; ++i) {
            if (yielded_moves_[i] == m) return true;
        }
        return false;
    }

    bool is_in_raw(uint16_t m) const {
        for (int i = 0; i < move_count_; ++i) {
            if (raw_moves_[i] == m) return true;
        }
        return false;
    }

    bool is_legal(uint16_t m) const {
        uint16_t legals[MAX_MOVES];
        int count = ::native_generate_legal_moves(board_, legals);
        for (int i = 0; i < count; ++i) {
            if (legals[i] == m) return true;
        }
        return false;
    }

    void pick_best(ScoredMove* list, int count, int start) {
        int best_idx = start;
        for (int i = start + 1; i < count; ++i) {
            if (list[i].score > list[best_idx].score) {
                best_idx = i;
            }
        }
        if (best_idx != start) {
            std::swap(list[start], list[best_idx]);
        }
    }

    int get_mvv_lva(uint16_t m) const {
        int to_sq = move_to(m);
        int victim_val = 100; // default pawn
        int them = 1 - board_->side_to_move;
        uint64_t to_bb = 1ULL << to_sq;

        if (board_->pieces[them][QUEEN] & to_bb) victim_val = 900;
        else if (board_->pieces[them][ROOK] & to_bb) victim_val = 500;
        else if (board_->pieces[them][BISHOP] & to_bb) victim_val = 325;
        else if (board_->pieces[them][KNIGHT] & to_bb) victim_val = 320;
        else if (board_->pieces[them][PAWN] & to_bb) victim_val = 100;

        int from_sq = move_from(m);
        uint64_t from_bb = 1ULL << from_sq;
        int us = board_->side_to_move;
        int attacker_val = 100;
        if (board_->pieces[us][KING] & from_bb) attacker_val = 10000;
        else if (board_->pieces[us][QUEEN] & from_bb) attacker_val = 900;
        else if (board_->pieces[us][ROOK] & from_bb) attacker_val = 500;
        else if (board_->pieces[us][BISHOP] & from_bb) attacker_val = 325;
        else if (board_->pieces[us][KNIGHT] & from_bb) attacker_val = 320;

        return (victim_val * 10) - (attacker_val / 10);
    }
};

} // namespace r1
