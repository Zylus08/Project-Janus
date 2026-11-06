#pragma once
#ifndef NNUE_V1_H
#define NNUE_V1_H

#include <cstdint>
#include <cstddef>
#include <vector>
#include <string>
#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>

// Alignment macro for SIMD/cache lines
#if defined(_MSC_VER)
#define ALIGN64 __declspec(align(64))
#else
#define ALIGN64 __attribute__((aligned(64)))
#endif

constexpr uint32_t NNUE_MAGIC = 0x4A4E5545; // 'JNUE'
constexpr uint32_t NNUE_VERSION = 1;
constexpr int MAX_ACCUM_DIM = 128;
constexpr int MAX_L1_DIM = 32;

// 64-byte binary header
#pragma pack(push, 1)
struct NNUEHeader {
    uint32_t magic;           // 0x4A4E5545 ("JNUE")
    uint32_t version;         // 1
    uint32_t arch_id;         // 1 = V1-Small, 2 = V1-Compact
    uint32_t feature_dim;     // 768 or 3072
    uint32_t accum_dim;       // 64 or 128
    uint32_t l1_dim;          // 16 or 32
    uint32_t output_dim;      // 1
    uint32_t scale_accum;     // 256
    uint32_t scale_l1;        // 64
    uint32_t scale_output;    // 128
    uint32_t eval_scale;      // 600
    uint32_t checksum_crc32;  // CRC32 of weight payload
    uint8_t  reserved[16];    // 64-byte total header
};
#pragma pack(pop)

// Incremental Accumulator state per ply
struct ALIGN64 Accumulator {
    int16_t values[2][MAX_ACCUM_DIM]; // [WHITE=0, BLACK=1][accum_dim]
    bool computed[2];
};

class NNUEEvaluator {
public:
    NNUEEvaluator();
    ~NNUEEvaluator();

    bool load_model(const std::string& path);
    void unload_model();
    bool is_loaded() const { return m_loaded; }

    const NNUEHeader& get_header() const { return m_header; }

    // Full accumulator refresh (root or cold-start)
    void full_refresh(const uint64_t pieces[2][6], int side_to_move, Accumulator* acc) const;

    // Incremental accumulator updates
    void update_quiet(
        Accumulator* next_acc, const Accumulator* prev_acc,
        int mover_color, int piece, int from_sq, int to_sq,
        const uint64_t pieces[2][6]
    ) const;

    void update_capture(
        Accumulator* next_acc, const Accumulator* prev_acc,
        int mover_color, int piece, int from_sq, int to_sq,
        int victim_color, int victim_piece,
        const uint64_t pieces[2][6]
    ) const;

    void update_promotion(
        Accumulator* next_acc, const Accumulator* prev_acc,
        int mover_color, int from_sq, int to_sq, int promo_piece,
        bool is_capture, int victim_color, int victim_piece,
        const uint64_t pieces[2][6]
    ) const;

    void update_en_passant(
        Accumulator* next_acc, const Accumulator* prev_acc,
        int mover_color, int from_sq, int to_sq, int ep_captured_sq,
        const uint64_t pieces[2][6]
    ) const;

    void update_castling(
        Accumulator* next_acc, const Accumulator* prev_acc,
        int mover_color, int k_from, int k_to, int r_from, int r_to,
        const uint64_t pieces[2][6]
    ) const;

    // Native integer feedforward inference (centipawns from perspective of side_to_move)
    int evaluate(const Accumulator* acc, int side_to_move) const;

private:
    bool m_loaded;
    NNUEHeader m_header;

    // Model weight buffers
    std::vector<int16_t> m_ft_weights; // [feature_dim, accum_dim] in contiguous rows
    std::vector<int16_t> m_ft_biases;  // [accum_dim]
    std::vector<int8_t>  m_fc1_weights; // [l1_dim, 2 * accum_dim]
    std::vector<int32_t> m_fc1_biases;  // [l1_dim]
    std::vector<int8_t>  m_fc2_weights; // [1, l1_dim]
    int32_t              m_fc2_bias;

    // Feature index helper
    int get_feature_index(int perspective, int color, int piece, int sq, int king_sq) const;
};

#endif // NNUE_V1_H
