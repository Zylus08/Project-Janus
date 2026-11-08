#include "nnue_v3.h"
#include <fstream>
#include <iostream>
#include <cassert>
#include <algorithm>

namespace janus {
namespace nnue_v3 {

NNUEEvaluatorV3::NNUEEvaluatorV3()
    : m_loaded(false), m_cpu_has_avx2(false), m_use_avx2(false), m_fc2_bias(0) {
    std::memset(&m_header, 0, sizeof(m_header));
    m_cpu_has_avx2 = detect_cpu_avx2();
    m_use_avx2 = m_cpu_has_avx2;
}

bool NNUEEvaluatorV3::detect_cpu_avx2() {
#if defined(__AVX2__)
    return true;
#elif defined(_MSC_VER)
    int cpu_info[4];
    __cpuid(cpu_info, 0);
    int num_ids = cpu_info[0];
    if (num_ids >= 7) {
        __cpuidex(cpu_info, 7, 0);
        return (cpu_info[1] & (1 << 5)) != 0; // Bit 5 of EBX is AVX2
    }
    return false;
#else
    return false;
#endif
}

bool NNUEEvaluatorV3::load_model(const std::string& filepath) {
    std::ifstream file(filepath, std::ios::binary);
    if (!file.is_open()) return false;

    file.read(reinterpret_cast<char*>(&m_header), sizeof(ModelHeaderV3));
    if (!file.good()) return false;

    if (m_header.magic != NNUE_MAGIC || m_header.version != NNUE_VERSION) return false;
    if (m_header.accum_dim != ACCUM_DIM || m_header.l1_dim != L1_DIM || m_header.sef_dim != SEF_DIM) return false;

    file.read(reinterpret_cast<char*>(m_ft_weights), sizeof(m_ft_weights));
    file.read(reinterpret_cast<char*>(m_ft_biases), sizeof(m_ft_biases));
    file.read(reinterpret_cast<char*>(m_fc1_weights), sizeof(m_fc1_weights));
    file.read(reinterpret_cast<char*>(m_fc1_biases), sizeof(m_fc1_biases));
    file.read(reinterpret_cast<char*>(m_fc2_weights), sizeof(m_fc2_weights));
    file.read(reinterpret_cast<char*>(&m_fc2_bias), sizeof(m_fc2_bias));

    if (!file.good()) return false;

    m_loaded = true;
    return true;
}

void NNUEEvaluatorV3::full_refresh(const uint64_t pieces[2][6], int stm, AccumulatorV3* acc) const {
    assert(m_loaded);
    std::memcpy(acc->values[0], m_ft_biases, sizeof(m_ft_biases));
    std::memcpy(acc->values[1], m_ft_biases, sizeof(m_ft_biases));

    for (int color = 0; color < 2; ++color) {
        for (int pt = 0; pt < 6; ++pt) {
            uint64_t bb = pieces[color][pt];
            while (bb) {
                int sq = static_cast<int>(TZCNT64(bb));
                bb &= bb - 1;

                int ft_white = color * 384 + pt * 64 + sq;
                int sq_black = sq ^ 56;
                int ft_black = (1 - color) * 384 + pt * 64 + sq_black;

                const int16_t* w_weights = &m_ft_weights[ft_white * ACCUM_DIM];
                const int16_t* b_weights = &m_ft_weights[ft_black * ACCUM_DIM];

                if (m_use_avx2) {
                    for (int v = 0; v < ACCUM_DIM / 16; ++v) {
                        __m256i acc_w = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc->values[0] + v * 16));
                        __m256i w_vec = _mm256_load_si256(reinterpret_cast<const __m256i*>(w_weights + v * 16));
                        _mm256_store_si256(reinterpret_cast<__m256i*>(acc->values[0] + v * 16), _mm256_add_epi16(acc_w, w_vec));

                        __m256i acc_b = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc->values[1] + v * 16));
                        __m256i b_vec = _mm256_load_si256(reinterpret_cast<const __m256i*>(b_weights + v * 16));
                        _mm256_store_si256(reinterpret_cast<__m256i*>(acc->values[1] + v * 16), _mm256_add_epi16(acc_b, b_vec));
                    }
                } else {
                    for (int i = 0; i < ACCUM_DIM; ++i) {
                        acc->values[0][i] += w_weights[i];
                        acc->values[1][i] += b_weights[i];
                    }
                }
            }
        }
    }
}

void NNUEEvaluatorV3::update_quiet(
    AccumulatorV3* next_acc, const AccumulatorV3* prev_acc,
    int stm, int pt, int from_sq, int to_sq,
    const uint64_t pieces[2][6]
) const {
    int ft_sub_w = stm * 384 + pt * 64 + from_sq;
    int ft_add_w = stm * 384 + pt * 64 + to_sq;
    int ft_sub_b = (1 - stm) * 384 + pt * 64 + (from_sq ^ 56);
    int ft_add_b = (1 - stm) * 384 + pt * 64 + (to_sq ^ 56);

    const int16_t* w_sub = &m_ft_weights[ft_sub_w * ACCUM_DIM];
    const int16_t* w_add = &m_ft_weights[ft_add_w * ACCUM_DIM];
    const int16_t* b_sub = &m_ft_weights[ft_sub_b * ACCUM_DIM];
    const int16_t* b_add = &m_ft_weights[ft_add_b * ACCUM_DIM];

    if (m_use_avx2) {
        for (int v = 0; v < ACCUM_DIM / 16; ++v) {
            __m256i prev_w = _mm256_load_si256(reinterpret_cast<const __m256i*>(prev_acc->values[0] + v * 16));
            __m256i sub_w = _mm256_load_si256(reinterpret_cast<const __m256i*>(w_sub + v * 16));
            __m256i add_w = _mm256_load_si256(reinterpret_cast<const __m256i*>(w_add + v * 16));
            __m256i res_w = _mm256_add_epi16(_mm256_sub_epi16(prev_w, sub_w), add_w);
            _mm256_store_si256(reinterpret_cast<__m256i*>(next_acc->values[0] + v * 16), res_w);

            __m256i prev_b = _mm256_load_si256(reinterpret_cast<const __m256i*>(prev_acc->values[1] + v * 16));
            __m256i sub_b = _mm256_load_si256(reinterpret_cast<const __m256i*>(b_sub + v * 16));
            __m256i add_b = _mm256_load_si256(reinterpret_cast<const __m256i*>(b_add + v * 16));
            __m256i res_b = _mm256_add_epi16(_mm256_sub_epi16(prev_b, sub_b), add_b);
            _mm256_store_si256(reinterpret_cast<__m256i*>(next_acc->values[1] + v * 16), res_b);
        }
    } else {
        for (int i = 0; i < ACCUM_DIM; ++i) {
            next_acc->values[0][i] = prev_acc->values[0][i] - w_sub[i] + w_add[i];
            next_acc->values[1][i] = prev_acc->values[1][i] - b_sub[i] + b_add[i];
        }
    }
}

void NNUEEvaluatorV3::update_capture(
    AccumulatorV3* next_acc, const AccumulatorV3* prev_acc,
    int stm, int pt, int from_sq, int to_sq,
    int victim_color, int victim_pt,
    const uint64_t pieces[2][6]
) const {
    int ft_sub_w = stm * 384 + pt * 64 + from_sq;
    int ft_add_w = stm * 384 + pt * 64 + to_sq;
    int ft_cap_w = victim_color * 384 + victim_pt * 64 + to_sq;

    int ft_sub_b = (1 - stm) * 384 + pt * 64 + (from_sq ^ 56);
    int ft_add_b = (1 - stm) * 384 + pt * 64 + (to_sq ^ 56);
    int ft_cap_b = (1 - victim_color) * 384 + victim_pt * 64 + (to_sq ^ 56);

    const int16_t* w_sub = &m_ft_weights[ft_sub_w * ACCUM_DIM];
    const int16_t* w_add = &m_ft_weights[ft_add_w * ACCUM_DIM];
    const int16_t* w_cap = &m_ft_weights[ft_cap_w * ACCUM_DIM];

    const int16_t* b_sub = &m_ft_weights[ft_sub_b * ACCUM_DIM];
    const int16_t* b_add = &m_ft_weights[ft_add_b * ACCUM_DIM];
    const int16_t* b_cap = &m_ft_weights[ft_cap_b * ACCUM_DIM];

    if (m_use_avx2) {
        for (int v = 0; v < ACCUM_DIM / 16; ++v) {
            __m256i prev_w = _mm256_load_si256(reinterpret_cast<const __m256i*>(prev_acc->values[0] + v * 16));
            __m256i sub_w = _mm256_load_si256(reinterpret_cast<const __m256i*>(w_sub + v * 16));
            __m256i add_w = _mm256_load_si256(reinterpret_cast<const __m256i*>(w_add + v * 16));
            __m256i cap_w = _mm256_load_si256(reinterpret_cast<const __m256i*>(w_cap + v * 16));
            __m256i res_w = _mm256_sub_epi16(_mm256_add_epi16(_mm256_sub_epi16(prev_w, sub_w), add_w), cap_w);
            _mm256_store_si256(reinterpret_cast<__m256i*>(next_acc->values[0] + v * 16), res_w);

            __m256i prev_b = _mm256_load_si256(reinterpret_cast<const __m256i*>(prev_acc->values[1] + v * 16));
            __m256i sub_b = _mm256_load_si256(reinterpret_cast<const __m256i*>(b_sub + v * 16));
            __m256i add_b = _mm256_load_si256(reinterpret_cast<const __m256i*>(b_add + v * 16));
            __m256i cap_b = _mm256_load_si256(reinterpret_cast<const __m256i*>(b_cap + v * 16));
            __m256i res_b = _mm256_sub_epi16(_mm256_add_epi16(_mm256_sub_epi16(prev_b, sub_b), add_b), cap_b);
            _mm256_store_si256(reinterpret_cast<__m256i*>(next_acc->values[1] + v * 16), res_b);
        }
    } else {
        for (int i = 0; i < ACCUM_DIM; ++i) {
            next_acc->values[0][i] = prev_acc->values[0][i] - w_sub[i] + w_add[i] - w_cap[i];
            next_acc->values[1][i] = prev_acc->values[1][i] - b_sub[i] + b_add[i] - b_cap[i];
        }
    }
}

int NNUEEvaluatorV3::evaluate(const AccumulatorV3* acc, const janus::nnue::BoardBitboards& b, int stm) const {
    if (m_use_avx2) {
        return evaluate_avx2(acc, b, stm);
    } else {
        return evaluate_scalar(acc, b, stm);
    }
}

int NNUEEvaluatorV3::evaluate_scalar(const AccumulatorV3* acc, const janus::nnue::BoardBitboards& b, int stm) const {
    assert(m_loaded);
    const int16_t* acc_stm = acc->values[stm];
    const int16_t* acc_opp = acc->values[1 - stm];

    alignas(32) uint8_t input_act[L1_INPUT_DIM]; // 288 bytes

    for (int i = 0; i < ACCUM_DIM; ++i) {
        int16_t v = acc_stm[i];
        input_act[i] = (v <= 0) ? 0 : ((v >= 127) ? 127 : static_cast<uint8_t>(v));
    }
    for (int i = 0; i < ACCUM_DIM; ++i) {
        int16_t v = acc_opp[i];
        input_act[ACCUM_DIM + i] = (v <= 0) ? 0 : ((v >= 127) ? 127 : static_cast<uint8_t>(v));
    }

    // Extract SEF features (32 dims)
    float sef[32];
    janus::nnue::ExtractSEFFeatures(b, sef);

    // If STM is Black, rotate SEF perspective: 16..31 first, then 0..15
    for (int i = 0; i < 32; ++i) {
        int src_idx = (stm == 0) ? i : ((i < 16) ? (i + 16) : (i - 16));
        float val = sef[src_idx] * 127.0f;
        int iv = static_cast<int>(std::round(val));
        input_act[2 * ACCUM_DIM + i] = (iv <= 0) ? 0 : ((iv >= 127) ? 127 : static_cast<uint8_t>(iv));
    }

    // Layer 1 (288 -> 32)
    alignas(32) uint8_t l1_act[L1_DIM];
    for (int j = 0; j < L1_DIM; ++j) {
        int32_t sum = m_fc1_biases[j];
        const int8_t* w_row = &m_fc1_weights[j * L1_INPUT_DIM];
        for (int i = 0; i < L1_INPUT_DIM; ++i) {
            sum += static_cast<int32_t>(input_act[i]) * static_cast<int32_t>(w_row[i]);
        }
        sum /= 128; // scale
        l1_act[j] = (sum <= 0) ? 0 : ((sum >= 127) ? 127 : static_cast<uint8_t>(sum));
    }

    // Layer 2 (32 -> 1)
    int32_t l2_sum = m_fc2_bias;
    for (int j = 0; j < L1_DIM; ++j) {
        l2_sum += static_cast<int32_t>(l1_act[j]) * static_cast<int32_t>(m_fc2_weights[j]);
    }

    int score_cp = static_cast<int>((static_cast<int64_t>(l2_sum) * m_header.eval_scale) / 8192);
    return std::clamp(score_cp, -29000, 29000);
}

int NNUEEvaluatorV3::evaluate_avx2(const AccumulatorV3* acc, const janus::nnue::BoardBitboards& b, int stm) const {
    assert(m_loaded);
    const int16_t* acc_stm = acc->values[stm];
    const int16_t* acc_opp = acc->values[1 - stm];

    alignas(32) uint8_t input_act[L1_INPUT_DIM + 32]; // padded to 320 for clean AVX2 32-byte chunks

    const __m256i v_clamp_max = _mm256_set1_epi8(127);

    // Vectorized pack & clamp for STM and Opponent (256 bytes)
    for (int v = 0; v < ACCUM_DIM / 16; v += 2) {
        __m256i stm_lo = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc_stm + v * 16));
        __m256i stm_hi = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc_stm + (v + 1) * 16));
        __m256i packed_stm = _mm256_packus_epi16(stm_lo, stm_hi);
        __m256i clamped_stm = _mm256_min_epu8(packed_stm, v_clamp_max);
        __m256i perm_stm = _mm256_permute4x64_epi64(clamped_stm, _MM_SHUFFLE(3, 1, 2, 0));
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(input_act + v * 16), perm_stm);

        __m256i opp_lo = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc_opp + v * 16));
        __m256i opp_hi = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc_opp + (v + 1) * 16));
        __m256i packed_opp = _mm256_packus_epi16(opp_lo, opp_hi);
        __m256i clamped_opp = _mm256_min_epu8(packed_opp, v_clamp_max);
        __m256i perm_opp = _mm256_permute4x64_epi64(clamped_opp, _MM_SHUFFLE(3, 1, 2, 0));
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(input_act + ACCUM_DIM + v * 16), perm_opp);
    }

    // Extract SEF features & pack into remaining 32 bytes
    float sef[32];
    janus::nnue::ExtractSEFFeatures(b, sef);
    for (int i = 0; i < 32; ++i) {
        int src_idx = (stm == 0) ? i : ((i < 16) ? (i + 16) : (i - 16));
        float val = sef[src_idx] * 127.0f;
        int iv = static_cast<int>(std::round(val));
        input_act[2 * ACCUM_DIM + i] = (iv <= 0) ? 0 : ((iv >= 127) ? 127 : static_cast<uint8_t>(iv));
    }
    // Pad remaining 32 bytes with zeros
    for (int i = 0; i < 32; ++i) input_act[L1_INPUT_DIM + i] = 0;

    // Vectorized Layer 1: 32 outputs x 288 inputs (9 vector loads per output)
    alignas(32) uint8_t l1_act[L1_DIM];
    const __m256i v_ones = _mm256_set1_epi16(1);

    for (int j = 0; j < L1_DIM; ++j) {
        __m256i sum_vec = _mm256_setzero_si256();
        const int8_t* w_row = &m_fc1_weights[j * L1_INPUT_DIM];

        for (int v = 0; v < 9; ++v) { // 9 x 32 = 288
            __m256i a = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(input_act + v * 32));
            __m256i w = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(w_row + v * 32));
            __m256i prod = _mm256_maddubs_epi16(a, w);
            __m256i prod_32 = _mm256_madd_epi16(prod, v_ones);
            sum_vec = _mm256_add_epi32(sum_vec, prod_32);
        }

        // Horizontal sum of 8 x 32-bit integers
        __m128i lo = _mm256_castsi256_si128(sum_vec);
        __m128i hi = _mm256_extracti128_si256(sum_vec, 1);
        __m128i s4 = _mm_add_epi32(lo, hi);
        s4 = _mm_hadd_epi32(s4, s4);
        s4 = _mm_hadd_epi32(s4, s4);
        int32_t dot = _mm_cvtsi128_si32(s4) + m_fc1_biases[j];
        dot /= 128;
        l1_act[j] = (dot <= 0) ? 0 : ((dot >= 127) ? 127 : static_cast<uint8_t>(dot));
    }

    // Layer 2 AVX2 dot-product (32 dimensions)
    __m256i act256 = _mm256_load_si256(reinterpret_cast<const __m256i*>(l1_act));
    __m256i w256 = _mm256_load_si256(reinterpret_cast<const __m256i*>(m_fc2_weights));
    __m256i prod = _mm256_maddubs_epi16(act256, w256);
    __m256i prod32 = _mm256_madd_epi16(prod, v_ones);

    __m128i lo = _mm256_castsi256_si128(prod32);
    __m128i hi = _mm256_extracti128_si256(prod32, 1);
    __m128i s4 = _mm_add_epi32(lo, hi);
    s4 = _mm_hadd_epi32(s4, s4);
    s4 = _mm_hadd_epi32(s4, s4);
    int32_t l2_sum = _mm_cvtsi128_si32(s4) + m_fc2_bias;

    int score_cp = static_cast<int>((static_cast<int64_t>(l2_sum) * m_header.eval_scale) / 8192);
    return std::clamp(score_cp, -29000, 29000);
}

} // namespace nnue_v3
} // namespace janus
