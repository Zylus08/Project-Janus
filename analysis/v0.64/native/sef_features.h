#pragma once

#include <cstdint>
#include <array>
#include <cmath>
#include <algorithm>

#if defined(_MSC_VER)
#include <intrin.h>
#define POPCOUNT64(x) __popcnt64(x)
#define TZCNT64(x) _tzcnt_u64(x)
#else
#define POPCOUNT64(x) __builtin_popcountll(x)
#define TZCNT64(x) __builtin_ctzll(x)
#endif

namespace janus {
namespace nnue {

// File masks
constexpr uint64_t FILE_A = 0x0101010101010101ULL;
constexpr uint64_t FILE_MASKS[8] = {
    FILE_A << 0, FILE_A << 1, FILE_A << 2, FILE_A << 3,
    FILE_A << 4, FILE_A << 5, FILE_A << 6, FILE_A << 7
};

// Rank masks
constexpr uint64_t RANK_1 = 0x00000000000000FFULL;
constexpr uint64_t RANK_MASKS[8] = {
    RANK_1 << (8 * 0), RANK_1 << (8 * 1), RANK_1 << (8 * 2), RANK_1 << (8 * 3),
    RANK_1 << (8 * 4), RANK_1 << (8 * 5), RANK_1 << (8 * 6), RANK_1 << (8 * 7)
};

inline int ChebyshevDist(int sq1, int sq2) {
    int r1 = sq1 / 8, f1 = sq1 % 8;
    int r2 = sq2 / 8, f2 = sq2 % 8;
    return std::max(std::abs(r1 - r2), std::abs(f1 - f2));
}

struct BoardBitboards {
    uint64_t w_pawns;
    uint64_t b_pawns;
    uint64_t w_knights;
    uint64_t b_knights;
    uint64_t w_bishops;
    uint64_t b_bishops;
    uint64_t w_rooks;
    uint64_t b_rooks;
    uint64_t w_queens;
    uint64_t b_queens;
    int w_king_sq;
    int b_king_sq;
    bool white_to_move;
};

// Extracts 32 normalized SEF features into out[32]
inline void ExtractSEFFeatures(const BoardBitboards& b, float out[32]) {
    for (int i = 0; i < 32; ++i) out[i] = 0.0f;

    // ---------------- White Perspective (0..15) ----------------
    int w_passed_count = 0;
    int w_passed_rank_sum = 0;
    int w_protected_passed = 0;

    int w_passed_sqs[8];
    uint64_t wp = b.w_pawns;

    while (wp) {
        int sq = static_cast<int>(TZCNT64(wp));
        wp &= wp - 1;
        int f = sq % 8;
        int r = sq / 8;

        uint64_t adj_files = (f > 0 ? FILE_MASKS[f - 1] : 0ULL) | FILE_MASKS[f] | (f < 7 ? FILE_MASKS[f + 1] : 0ULL);
        uint64_t front_ranks = 0ULL;
        for (int ra = r + 1; ra < 8; ++ra) front_ranks |= RANK_MASKS[ra];

        if ((b.b_pawns & adj_files & front_ranks) == 0ULL) {
            w_passed_sqs[w_passed_count++] = sq;
            w_passed_rank_sum += (r - 1);

            int defenders = 0;
            if (f > 0 && r > 0 && (b.w_pawns & (1ULL << (sq - 9)))) defenders++;
            if (f < 7 && r > 0 && (b.w_pawns & (1ULL << (sq - 7)))) defenders++;
            if (defenders > 0) w_protected_passed++;
        }
    }

    out[0] = static_cast<float>(w_passed_count) / 8.0f;
    out[1] = static_cast<float>(w_passed_rank_sum) / 24.0f;
    out[2] = static_cast<float>(w_protected_passed) / 8.0f;

    // Isolated pawns
    int w_isolated = 0;
    wp = b.w_pawns;
    while (wp) {
        int sq = static_cast<int>(TZCNT64(wp));
        wp &= wp - 1;
        int f = sq % 8;
        uint64_t adj_files = (f > 0 ? FILE_MASKS[f - 1] : 0ULL) | (f < 7 ? FILE_MASKS[f + 1] : 0ULL);
        if ((b.w_pawns & adj_files) == 0ULL) w_isolated++;
    }
    out[3] = static_cast<float>(w_isolated) / 8.0f;

    // Doubled pawns
    int w_doubled = 0;
    for (int f = 0; f < 8; ++f) {
        int c = POPCOUNT64(b.w_pawns & FILE_MASKS[f]);
        if (c > 1) w_doubled += (c - 1);
    }
    out[4] = static_cast<float>(w_doubled) / 8.0f;

    // King centralization & shelter
    if (b.w_king_sq >= 0 && b.w_king_sq < 64) {
        int kr = b.w_king_sq / 8, kf = b.w_king_sq % 8;
        float w_cent = 4.0f - std::max(std::abs(kr - 3.5f), std::abs(kf - 3.5f));
        out[6] = w_cent / 4.0f;

        if (w_passed_count > 0) {
            int min_d = 7;
            for (int i = 0; i < w_passed_count; ++i) {
                int d = ChebyshevDist(b.w_king_sq, w_passed_sqs[i]);
                if (d < min_d) min_d = d;
            }
            out[7] = static_cast<float>(7 - min_d) / 7.0f;
        }

        if (b.b_king_sq >= 0 && w_passed_count > 0) {
            int min_d = 7;
            for (int i = 0; i < w_passed_count; ++i) {
                int d = ChebyshevDist(b.b_king_sq, w_passed_sqs[i]);
                if (d < min_d) min_d = d;
            }
            out[8] = static_cast<float>(7 - min_d) / 7.0f;
        }

        uint64_t shelter_mask = 0ULL;
        for (int df = -1; df <= 1; ++df) {
            if (kf + df >= 0 && kf + df <= 7) {
                for (int dr = 1; dr <= 2; ++dr) {
                    if (kr + dr >= 0 && kr + dr <= 7) {
                        shelter_mask |= (1ULL << ((kr + dr) * 8 + (kf + df)));
                    }
                }
            }
        }
        out[9] = static_cast<float>(POPCOUNT64(b.w_pawns & shelter_mask)) / 6.0f;
    }

    // Open & Semi-open files for rooks
    int w_open_rooks = 0, w_semi_rooks = 0;
    uint64_t wr = b.w_rooks;
    while (wr) {
        int sq = static_cast<int>(TZCNT64(wr));
        wr &= wr - 1;
        int f = sq % 8;
        bool has_w = (b.w_pawns & FILE_MASKS[f]) != 0ULL;
        bool has_b = (b.b_pawns & FILE_MASKS[f]) != 0ULL;
        if (!has_w && !has_b) w_open_rooks++;
        else if (!has_w && has_b) w_semi_rooks++;
    }
    out[10] = static_cast<float>(w_open_rooks) / 2.0f;
    out[11] = static_cast<float>(w_semi_rooks) / 2.0f;

    // Bishop pair
    out[12] = (POPCOUNT64(b.w_bishops) >= 2) ? 1.0f : 0.0f;

    // Material
    int w_npm = POPCOUNT64(b.w_knights) * 1 + POPCOUNT64(b.w_bishops) * 1 + POPCOUNT64(b.w_rooks) * 2 + POPCOUNT64(b.w_queens) * 4;
    out[13] = static_cast<float>(w_npm) / 16.0f;
    out[14] = static_cast<float>(POPCOUNT64(b.w_pawns)) / 8.0f;
    out[15] = b.white_to_move ? 1.0f : 0.0f;

    // ---------------- Black Perspective (16..31) ----------------
    int b_passed_count = 0;
    int b_passed_rank_sum = 0;
    int b_protected_passed = 0;
    int b_passed_sqs[8];

    uint64_t bp = b.b_pawns;
    while (bp) {
        int sq = static_cast<int>(TZCNT64(bp));
        bp &= bp - 1;
        int f = sq % 8;
        int r = sq / 8;

        uint64_t adj_files = (f > 0 ? FILE_MASKS[f - 1] : 0ULL) | FILE_MASKS[f] | (f < 7 ? FILE_MASKS[f + 1] : 0ULL);
        uint64_t front_ranks = 0ULL;
        for (int ra = 0; ra < r; ++ra) front_ranks |= RANK_MASKS[ra];

        if ((b.w_pawns & adj_files & front_ranks) == 0ULL) {
            b_passed_sqs[b_passed_count++] = sq;
            b_passed_rank_sum += (6 - r);

            int defenders = 0;
            if (f > 0 && r < 7 && (b.b_pawns & (1ULL << (sq + 7)))) defenders++;
            if (f < 7 && r < 7 && (b.b_pawns & (1ULL << (sq + 9)))) defenders++;
            if (defenders > 0) b_protected_passed++;
        }
    }

    out[16] = static_cast<float>(b_passed_count) / 8.0f;
    out[17] = static_cast<float>(b_passed_rank_sum) / 24.0f;
    out[18] = static_cast<float>(b_protected_passed) / 8.0f;

    int b_isolated = 0;
    bp = b.b_pawns;
    while (bp) {
        int sq = static_cast<int>(TZCNT64(bp));
        bp &= bp - 1;
        int f = sq % 8;
        uint64_t adj_files = (f > 0 ? FILE_MASKS[f - 1] : 0ULL) | (f < 7 ? FILE_MASKS[f + 1] : 0ULL);
        if ((b.b_pawns & adj_files) == 0ULL) b_isolated++;
    }
    out[19] = static_cast<float>(b_isolated) / 8.0f;

    int b_doubled = 0;
    for (int f = 0; f < 8; ++f) {
        int c = POPCOUNT64(b.b_pawns & FILE_MASKS[f]);
        if (c > 1) b_doubled += (c - 1);
    }
    out[20] = static_cast<float>(b_doubled) / 8.0f;

    if (b.b_king_sq >= 0 && b.b_king_sq < 64) {
        int kr = b.b_king_sq / 8, kf = b.b_king_sq % 8;
        float b_cent = 4.0f - std::max(std::abs(kr - 3.5f), std::abs(kf - 3.5f));
        out[22] = b_cent / 4.0f;

        if (b_passed_count > 0) {
            int min_d = 7;
            for (int i = 0; i < b_passed_count; ++i) {
                int d = ChebyshevDist(b.b_king_sq, b_passed_sqs[i]);
                if (d < min_d) min_d = d;
            }
            out[23] = static_cast<float>(7 - min_d) / 7.0f;
        }

        if (b.w_king_sq >= 0 && b_passed_count > 0) {
            int min_d = 7;
            for (int i = 0; i < b_passed_count; ++i) {
                int d = ChebyshevDist(b.w_king_sq, b_passed_sqs[i]);
                if (d < min_d) min_d = d;
            }
            out[24] = static_cast<float>(7 - min_d) / 7.0f;
        }

        uint64_t shelter_mask = 0ULL;
        for (int df = -1; df <= 1; ++df) {
            if (kf + df >= 0 && kf + df <= 7) {
                for (int dr = -1; dr >= -2; --dr) {
                    if (kr + dr >= 0 && kr + dr <= 7) {
                        shelter_mask |= (1ULL << ((kr + dr) * 8 + (kf + df)));
                    }
                }
            }
        }
        out[25] = static_cast<float>(POPCOUNT64(b.b_pawns & shelter_mask)) / 6.0f;
    }

    int b_open_rooks = 0, b_semi_rooks = 0;
    uint64_t br = b.b_rooks;
    while (br) {
        int sq = static_cast<int>(TZCNT64(br));
        br &= br - 1;
        int f = sq % 8;
        bool has_w = (b.w_pawns & FILE_MASKS[f]) != 0ULL;
        bool has_b = (b.b_pawns & FILE_MASKS[f]) != 0ULL;
        if (!has_w && !has_b) b_open_rooks++;
        else if (!has_b && has_w) b_semi_rooks++;
    }
    out[26] = static_cast<float>(b_open_rooks) / 2.0f;
    out[27] = static_cast<float>(b_semi_rooks) / 2.0f;

    out[28] = (POPCOUNT64(b.b_bishops) >= 2) ? 1.0f : 0.0f;

    int b_npm = POPCOUNT64(b.b_knights) * 1 + POPCOUNT64(b.b_bishops) * 1 + POPCOUNT64(b.b_rooks) * 2 + POPCOUNT64(b.b_queens) * 4;
    out[29] = static_cast<float>(b_npm) / 16.0f;
    out[30] = static_cast<float>(POPCOUNT64(b.b_pawns)) / 8.0f;
    out[31] = !b.white_to_move ? 1.0f : 0.0f;
}

} // namespace nnue
} // namespace janus
