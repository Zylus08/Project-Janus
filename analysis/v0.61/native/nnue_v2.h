#pragma once

#include <cstdint>
#include <string>
#include <cstring>
#include <vector>
#include <immintrin.h>

namespace nnue_v2 {

constexpr uint32_t NNUE_MAGIC = 0x4A4E5545; // 'JNUE'
constexpr uint32_t NNUE_VERSION = 2;
constexpr int MAX_ACCUM_DIM = 128;
constexpr int MAX_L1_DIM = 32;

#pragma pack(push, 1)
struct ModelHeader {
    uint32_t magic;
    uint32_t version;
    uint32_t arch_id;
    uint32_t feature_dim;
    uint32_t accum_dim;
    uint32_t l1_dim;
    uint32_t output_dim;
    uint32_t scale_accum;
    uint32_t scale_l1;
    uint32_t scale_output;
    uint32_t eval_scale;
    uint32_t crc32;
    uint8_t reserved[16];
};
#pragma pack(pop)

// 32-byte aligned accumulator to permit direct AVX2 vector loads/stores
struct alignas(32) Accumulator {
    int16_t values[2][MAX_ACCUM_DIM]; // [0] = White perspective, [1] = Black perspective
};

class NNUEEvaluatorV2 {
public:
    NNUEEvaluatorV2();
    ~NNUEEvaluatorV2() = default;

    bool load_model(const std::string& filepath);
    bool is_loaded() const { return m_loaded; }
    const ModelHeader& get_header() const { return m_header; }

    // SIMD Configuration & Hardware Detection
    static bool detect_cpu_avx2();
    void set_use_avx2(bool enable) { m_use_avx2 = enable && m_cpu_has_avx2; }
    bool is_using_avx2() const { return m_use_avx2; }

    // Board Refresh & Accumulator Maintenance
    void full_refresh(const uint64_t pieces[2][6], int stm, Accumulator* acc) const;
    void update_quiet(Accumulator* next_acc, const Accumulator* prev_acc,
                      int stm, int pt, int from_sq, int to_sq,
                      const uint64_t pieces[2][6]) const;
    void update_capture(Accumulator* next_acc, const Accumulator* prev_acc,
                        int stm, int pt, int from_sq, int to_sq,
                        int victim_color, int victim_pt,
                        const uint64_t pieces[2][6]) const;

    // Evaluation dispatch
    int evaluate(const Accumulator* acc, int stm) const;
    int evaluate_scalar(const Accumulator* acc, int stm) const;
    int evaluate_avx2(const Accumulator* acc, int stm) const;

private:
    bool m_loaded;
    bool m_cpu_has_avx2;
    bool m_use_avx2;
    ModelHeader m_header;

    // 32-byte aligned weights for AVX2 memory operations
    alignas(32) int16_t m_ft_weights[768 * MAX_ACCUM_DIM];
    alignas(32) int16_t m_ft_biases[MAX_ACCUM_DIM];
    alignas(32) int8_t  m_fc1_weights[MAX_L1_DIM * (2 * MAX_ACCUM_DIM)];
    alignas(32) int32_t m_fc1_biases[MAX_L1_DIM];
    alignas(32) int8_t  m_fc2_weights[MAX_L1_DIM];
    int32_t             m_fc2_bias;

    void update_accumulator_vector(int16_t* dst, const int16_t* src,
                                   int feature_sub, int feature_add) const;
    void update_accumulator_vector_avx2(int16_t* dst, const int16_t* src,
                                        int feature_sub, int feature_add) const;
};

} // namespace nnue_v2
