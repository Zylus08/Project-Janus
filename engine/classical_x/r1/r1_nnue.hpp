#pragma once
/**
 * r1_nnue.hpp
 * Project Janus — Original Quantized CPU NNUE Evaluator & Incremental Accumulator.
 * Architecture: Dual-Perspective HalfKP-768 -> 128 (x2) -> 32 -> 1
 */

#include "r1_types.hpp"
#include "r1_nnue_weights.hpp"
#include <cstring>
#include <cmath>
#include <algorithm>
#include <immintrin.h>

namespace r1 {

struct alignas(64) Accumulator {
    int16_t white[128];
    int16_t black[128];
    bool computed = false;
};

class NNUEEvaluator {
public:
    static constexpr int SCALE_FT = 256;
    static constexpr int SCALE_L1 = 128;
    static constexpr int SCALE_L2 = 128;

    // Feature index calculation:
    // piece: 0=P, 1=N, 2=B, 3=R, 4=Q, 5=K
    // color: 0=White, 1=Black
    static inline int white_feature_idx(int piece, int color, int sq) {
        int pt_idx = color * 6 + piece;
        return pt_idx * 64 + sq;
    }

    static inline int black_feature_idx(int piece, int color, int sq) {
        int pt_idx = (1 - color) * 6 + piece;
        return pt_idx * 64 + (sq ^ 56);
    }

    // Add feature to accumulator (feature-major FT_WEIGHTS)
    static inline void add_feature(Accumulator& acc, int w_feat, int b_feat) {
        const int16_t* w_weights = &nnue_embedded::FT_WEIGHTS[w_feat * 128];
        const int16_t* b_weights = &nnue_embedded::FT_WEIGHTS[b_feat * 128];
        for (int i = 0; i < 128; ++i) {
            acc.white[i] += w_weights[i];
            acc.black[i] += b_weights[i];
        }
    }

    // Remove feature from accumulator
    static inline void sub_feature(Accumulator& acc, int w_feat, int b_feat) {
        const int16_t* w_weights = &nnue_embedded::FT_WEIGHTS[w_feat * 128];
        const int16_t* b_weights = &nnue_embedded::FT_WEIGHTS[b_feat * 128];
        for (int i = 0; i < 128; ++i) {
            acc.white[i] -= w_weights[i];
            acc.black[i] -= b_weights[i];
        }
    }

    // Full Recomputation of Accumulators from board state
    static void full_recompute(const NativeBoard* b, Accumulator& acc) {
        std::memcpy(acc.white, nnue_embedded::FT_BIASES, sizeof(acc.white));
        std::memcpy(acc.black, nnue_embedded::FT_BIASES, sizeof(acc.black));

        for (int c = 0; c < 2; ++c) {
            for (int pt = 0; pt < 6; ++pt) {
                uint64_t bb = b->pieces[c][pt];
                while (bb) {
                    int sq = _tzcnt_u64(bb);
                    bb &= bb - 1;
                    int w_feat = white_feature_idx(pt, c, sq);
                    int b_feat = black_feature_idx(pt, c, sq);
                    add_feature(acc, w_feat, b_feat);
                }
            }
        }
        acc.computed = true;
    }

    // Incremental Update for a Legal Move
    static void update_move(const NativeBoard* b_before, uint16_t move, const Accumulator& in_acc, Accumulator& out_acc) {
        // Copy starting state
        std::memcpy(&out_acc, &in_acc, sizeof(Accumulator));

        int from = move_from(move);
        int to = move_to(move);
        int flag = move_flag(move);
        int promo = move_promo(move);
        int stm = b_before->side_to_move;

        // Find moving piece type
        int moving_pt = -1;
        for (int pt = 0; pt < 6; ++pt) {
            if ((b_before->pieces[stm][pt] >> from) & 1ULL) {
                moving_pt = pt;
                break;
            }
        }
        if (moving_pt == -1) {
            // Fallback safety
            full_recompute(b_before, out_acc);
            return;
        }

        // 1. Remove moving piece from 'from' square
        int w_rem_from = white_feature_idx(moving_pt, stm, from);
        int b_rem_from = black_feature_idx(moving_pt, stm, from);
        sub_feature(out_acc, w_rem_from, b_rem_from);

        // 2. Normal capture on 'to' square
        if (flag != 2) { // Not en passant
            int enemy = 1 - stm;
            for (int pt = 0; pt < 6; ++pt) {
                if ((b_before->pieces[enemy][pt] >> to) & 1ULL) {
                    int w_cap = white_feature_idx(pt, enemy, to);
                    int b_cap = black_feature_idx(pt, enemy, to);
                    sub_feature(out_acc, w_cap, b_cap);
                    break;
                }
            }
        }

        // 3. En passant capture
        if (flag == 2) {
            int ep_victim_sq = (stm == 0) ? (to - 8) : (to + 8);
            int enemy = 1 - stm;
            int w_ep = white_feature_idx(0, enemy, ep_victim_sq); // Pawn
            int b_ep = black_feature_idx(0, enemy, ep_victim_sq);
            sub_feature(out_acc, w_ep, b_ep);
        }

        // 4. Castling rook move
        if (flag == 1) {
            if (to == 6) { // White O-O: Rook h1 -> f1
                sub_feature(out_acc, white_feature_idx(3, 0, 7), black_feature_idx(3, 0, 7));
                add_feature(out_acc, white_feature_idx(3, 0, 5), black_feature_idx(3, 0, 5));
            } else if (to == 2) { // White O-O-O: Rook a1 -> d1
                sub_feature(out_acc, white_feature_idx(3, 0, 0), black_feature_idx(3, 0, 0));
                add_feature(out_acc, white_feature_idx(3, 0, 3), black_feature_idx(3, 0, 3));
            } else if (to == 62) { // Black O-O: Rook h8 -> f8
                sub_feature(out_acc, white_feature_idx(3, 1, 63), black_feature_idx(3, 1, 63));
                add_feature(out_acc, white_feature_idx(3, 1, 61), black_feature_idx(3, 1, 61));
            } else if (to == 58) { // Black O-O-O: Rook a8 -> d8
                sub_feature(out_acc, white_feature_idx(3, 1, 56), black_feature_idx(3, 1, 56));
                add_feature(out_acc, white_feature_idx(3, 1, 59), black_feature_idx(3, 1, 59));
            }
        }

        // 5. Piece arriving on 'to' square (with promotion)
        int arriving_pt = (flag == 3) ? (promo + 1) : moving_pt;
        int w_add_to = white_feature_idx(arriving_pt, stm, to);
        int b_add_to = black_feature_idx(arriving_pt, stm, to);
        add_feature(out_acc, w_add_to, b_add_to);

        out_acc.computed = true;
    }

    // Forward Evaluation from Accumulator
    static int evaluate(const NativeBoard* b, const Accumulator& acc) {
        const int16_t* friendly = (b->side_to_move == 0) ? acc.white : acc.black;
        const int16_t* enemy    = (b->side_to_move == 0) ? acc.black : acc.white;

        // Input layer: clipped ReLU of friendly followed by enemy [0, SCALE_FT]
        int16_t input[256];
        for (int i = 0; i < 128; ++i) {
            input[i]       = static_cast<int16_t>(std::clamp<int>(friendly[i], 0, SCALE_FT));
            input[i + 128] = static_cast<int16_t>(std::clamp<int>(enemy[i], 0, SCALE_FT));
        }

        // Hidden Layer 1: [256] -> [32]
        int16_t l1_act[32];
        for (int k = 0; k < 32; ++k) {
            int32_t sum = nnue_embedded::L1_BIASES[k];
            const int16_t* w_row = &nnue_embedded::L1_WEIGHTS[k * 256];
            for (int j = 0; j < 256; ++j) {
                sum += static_cast<int32_t>(w_row[j]) * static_cast<int32_t>(input[j]);
            }
            // Scale down by SCALE_FT (256) and clamp to [0, SCALE_L1] (128)
            l1_act[k] = static_cast<int16_t>(std::clamp<int32_t>(sum / SCALE_FT, 0, SCALE_L1));
        }

        // Output Layer L2: [32] -> [1]
        int32_t sum_l2 = nnue_embedded::L2_BIAS;
        for (int k = 0; k < 32; ++k) {
            sum_l2 += static_cast<int32_t>(nnue_embedded::L2_WEIGHTS[k]) * static_cast<int32_t>(l1_act[k]);
        }

        // Convert fixed-point logit to centipawns:
        // q_logit = sum_l2 / (SCALE_L1 * SCALE_L2) = sum_l2 / 16384
        // cp = q_logit * (400 / ln(10)) = sum_l2 * 173.7178 / 16384
        double cp_val = (static_cast<double>(sum_l2) * (400.0 / 2.302585092994046)) / 16384.0;
        int cp = static_cast<int>(std::round(cp_val));

        // Clamped safety range
        return std::clamp(cp, -27000, 27000);
    }

    // Direct Full Evaluation
    static int evaluate_full(const NativeBoard* b) {
        Accumulator acc;
        full_recompute(b, acc);
        return evaluate(b, acc);
    }
};

} // namespace r1
