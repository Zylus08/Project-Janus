#pragma once

#include <cstdint>
#include <string>
#include <cstring>
#include <vector>
#include <immintrin.h>
#include "sef_features.h"

namespace janus {
namespace nnue_v3 {

constexpr uint32_t NNUE_MAGIC = 0x4A4E5533; // 'JNU3'
constexpr uint32_t NNUE_VERSION = 3;
constexpr int ACCUM_DIM = 128;
constexpr int SEF_DIM = 32;
constexpr int L1_INPUT_DIM = 2 * ACCUM_DIM + SEF_DIM; // 288
constexpr int L1_DIM = 32;

#pragma pack(push, 1)
struct ModelHeaderV3 {
    uint32_t magic;
    uint32_t version;
    uint32_t arch_id;
    uint32_t feature_dim;
    uint32_t accum_dim;
    uint32_t sef_dim;
    uint32_t l1_dim;
    uint32_t output_dim;
    uint32_t eval_scale;
    uint32_t crc32;
    uint8_t reserved[24];
};
#pragma pack(pop)

struct alignas(32) AccumulatorV3 {
    int16_t values[2][ACCUM_DIM]; // [0] = White, [1] = Black
};

class NNUEEvaluatorV3 {
public:
    NNUEEvaluatorV3();
    ~NNUEEvaluatorV3() = default;

    bool load_model(const std::string& filepath);
    bool is_loaded() const { return m_loaded; }
    const ModelHeaderV3& get_header() const { return m_header; }

    static bool detect_cpu_avx2();
    void set_use_avx2(bool enable) { m_use_avx2 = enable && m_cpu_has_avx2; }
    bool is_using_avx2() const { return m_use_avx2; }

    // Board Refresh & Accumulator Updates
    void full_refresh(const uint64_t pieces[2][6], int stm, AccumulatorV3* acc) const;
    void update_quiet(AccumulatorV3* next_acc, const AccumulatorV3* prev_acc,
                      int stm, int pt, int from_sq, int to_sq,
                      const uint64_t pieces[2][6]) const;
    void update_capture(AccumulatorV3* next_acc, const AccumulatorV3* prev_acc,
                        int stm, int pt, int from_sq, int to_sq,
                        int victim_color, int victim_pt,
                        const uint64_t pieces[2][6]) const;

    // Evaluation Dispatch
    int evaluate(const AccumulatorV3* acc, const janus::nnue::BoardBitboards& b, int stm) const;
    int evaluate_scalar(const AccumulatorV3* acc, const janus::nnue::BoardBitboards& b, int stm) const;
    int evaluate_avx2(const AccumulatorV3* acc, const janus::nnue::BoardBitboards& b, int stm) const;

private:
    bool m_loaded;
    bool m_cpu_has_avx2;
    bool m_use_avx2;
    ModelHeaderV3 m_header;

    alignas(32) int16_t m_ft_weights[768 * ACCUM_DIM];
    alignas(32) int16_t m_ft_biases[ACCUM_DIM];
    alignas(32) int8_t  m_fc1_weights[L1_DIM * L1_INPUT_DIM]; // 32 x 288
    alignas(32) int32_t m_fc1_biases[L1_DIM];
    alignas(32) int8_t  m_fc2_weights[L1_DIM];
    int32_t             m_fc2_bias;
};

} // namespace nnue_v3
} // namespace janus
