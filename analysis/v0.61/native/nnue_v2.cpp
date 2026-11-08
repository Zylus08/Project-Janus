#include "nnue_v2.h"

#include <iostream>
#include <fstream>
#include <algorithm>
#include <cassert>

#ifdef _MSC_VER
#include <intrin.h>
#else
#include <cpuid.h>
#endif

namespace nnue_v2 {

NNUEEvaluatorV2::NNUEEvaluatorV2()
    : m_loaded(false), m_cpu_has_avx2(false), m_use_avx2(false), m_fc2_bias(0) {
    std::memset(&m_header, 0, sizeof(m_header));
    std::memset(m_ft_weights, 0, sizeof(m_ft_weights));
    std::memset(m_ft_biases, 0, sizeof(m_ft_biases));
    std::memset(m_fc1_weights, 0, sizeof(m_fc1_weights));
    std::memset(m_fc1_biases, 0, sizeof(m_fc1_biases));
    std::memset(m_fc2_weights, 0, sizeof(m_fc2_weights));

    m_cpu_has_avx2 = detect_cpu_avx2();
    m_use_avx2 = m_cpu_has_avx2; // Default to AVX2 if supported
}

bool NNUEEvaluatorV2::detect_cpu_avx2() {
#ifdef _MSC_VER
    int cpuInfo[4];
    __cpuid(cpuInfo, 0);
    int nIds = cpuInfo[0];
    if (nIds >= 7) {
        __cpuidex(cpuInfo, 7, 0);
        return (cpuInfo[1] & (1 << 5)) != 0; // AVX2 bit in EBX
    }
    return false;
#else
    unsigned int eax, ebx, ecx, edx;
    if (__get_cpuid(0, &eax, &ebx, &ecx, &edx)) {
        if (eax >= 7) {
            __cpuid_count(7, 0, eax, ebx, ecx, edx);
            return (ebx & (1 << 5)) != 0;
        }
    }
    return false;
#endif
}

bool NNUEEvaluatorV2::load_model(const std::string& filepath) {
    std::ifstream file(filepath, std::ios::binary);
    if (!file.is_open()) {
        std::cerr << "[NNUE-V2] Error: Cannot open model file: " << filepath << std::endl;
        return false;
    }

    file.read(reinterpret_cast<char*>(&m_header), sizeof(ModelHeader));
    if (file.gcount() != sizeof(ModelHeader)) {
        std::cerr << "[NNUE-V2] Error: Failed to read header" << std::endl;
        return false;
    }

    if (m_header.magic != NNUE_MAGIC) {
        std::cerr << "[NNUE-V2] Error: Invalid magic number: 0x" << std::hex << m_header.magic << std::endl;
        return false;
    }

    if (m_header.accum_dim > MAX_ACCUM_DIM || m_header.l1_dim > MAX_L1_DIM) {
        std::cerr << "[NNUE-V2] Error: Model dimensions exceed allocated storage" << std::endl;
        return false;
    }

    // 1. Feature Transformer Weights: [768 * accum_dim] int16
    size_t ft_w_bytes = m_header.feature_dim * m_header.accum_dim * sizeof(int16_t);
    file.read(reinterpret_cast<char*>(m_ft_weights), ft_w_bytes);

    // 2. Feature Transformer Biases: [accum_dim] int16
    size_t ft_b_bytes = m_header.accum_dim * sizeof(int16_t);
    file.read(reinterpret_cast<char*>(m_ft_biases), ft_b_bytes);

    // 3. Dense Layer 1 Weights: [l1_dim * (2 * accum_dim)] int8
    size_t fc1_w_bytes = m_header.l1_dim * (2 * m_header.accum_dim) * sizeof(int8_t);
    file.read(reinterpret_cast<char*>(m_fc1_weights), fc1_w_bytes);

    // 4. Dense Layer 1 Biases: [l1_dim] int32
    size_t fc1_b_bytes = m_header.l1_dim * sizeof(int32_t);
    file.read(reinterpret_cast<char*>(m_fc1_biases), fc1_b_bytes);

    // 5. Dense Layer 2 Weights: [l1_dim] int8
    size_t fc2_w_bytes = m_header.l1_dim * sizeof(int8_t);
    file.read(reinterpret_cast<char*>(m_fc2_weights), fc2_w_bytes);

    // 6. Dense Layer 2 Bias: [1] int32
    file.read(reinterpret_cast<char*>(&m_fc2_bias), sizeof(int32_t));

    if (!file) {
        std::cerr << "[NNUE-V2] Error: Unexpected EOF reading model payload" << std::endl;
        return false;
    }

    m_loaded = true;
    return true;
}

void NNUEEvaluatorV2::full_refresh(const uint64_t pieces[2][6], int stm, Accumulator* acc) const {
    assert(m_loaded);
    // Initialize accumulators from biases
    for (int p = 0; p < 2; p++) {
        std::memcpy(acc->values[p], m_ft_biases, m_header.accum_dim * sizeof(int16_t));
    }

    // Scan all active pieces on the board
    for (int color = 0; color < 2; color++) {
        for (int pt = 0; pt < 6; pt++) {
            uint64_t bb = pieces[color][pt];
            while (bb) {
                int sq = static_cast<int>(_tzcnt_u64(bb));
                bb &= bb - 1;

                // Feature indices: [color * 384 + pt * 64 + sq]
                int c_white = (color == 0) ? 0 : 1;
                int sq_white = sq;
                int feat_white = c_white * 384 + pt * 64 + sq_white;

                int c_black = (color == 1) ? 0 : 1;
                int sq_black = sq ^ 56;
                int feat_black = c_black * 384 + pt * 64 + sq_black;

                if (m_use_avx2) {
                    update_accumulator_vector_avx2(acc->values[0], acc->values[0], -1, feat_white);
                    update_accumulator_vector_avx2(acc->values[1], acc->values[1], -1, feat_black);
                } else {
                    update_accumulator_vector(acc->values[0], acc->values[0], -1, feat_white);
                    update_accumulator_vector(acc->values[1], acc->values[1], -1, feat_black);
                }
            }
        }
    }
}

void NNUEEvaluatorV2::update_accumulator_vector(int16_t* dst, const int16_t* src,
                                                int feature_sub, int feature_add) const {
    const int16_t* w_sub = (feature_sub >= 0) ? (m_ft_weights + feature_sub * m_header.accum_dim) : nullptr;
    const int16_t* w_add = (feature_add >= 0) ? (m_ft_weights + feature_add * m_header.accum_dim) : nullptr;

    for (int i = 0; i < (int)m_header.accum_dim; i++) {
        int16_t val = src[i];
        if (w_sub) val -= w_sub[i];
        if (w_add) val += w_add[i];
        dst[i] = val;
    }
}

void NNUEEvaluatorV2::update_accumulator_vector_avx2(int16_t* dst, const int16_t* src,
                                                     int feature_sub, int feature_add) const {
    const int16_t* w_sub = (feature_sub >= 0) ? (m_ft_weights + feature_sub * m_header.accum_dim) : nullptr;
    const int16_t* w_add = (feature_add >= 0) ? (m_ft_weights + feature_add * m_header.accum_dim) : nullptr;

    int num_vectors = m_header.accum_dim / 16;
    for (int v = 0; v < num_vectors; v++) {
        __m256i val = _mm256_load_si256(reinterpret_cast<const __m256i*>(src + v * 16));
        if (w_sub) {
            __m256i sub_v = _mm256_load_si256(reinterpret_cast<const __m256i*>(w_sub + v * 16));
            val = _mm256_sub_epi16(val, sub_v);
        }
        if (w_add) {
            __m256i add_v = _mm256_load_si256(reinterpret_cast<const __m256i*>(w_add + v * 16));
            val = _mm256_add_epi16(val, add_v);
        }
        _mm256_store_si256(reinterpret_cast<__m256i*>(dst + v * 16), val);
    }
}

void NNUEEvaluatorV2::update_quiet(Accumulator* next_acc, const Accumulator* prev_acc,
                                   int stm, int pt, int from_sq, int to_sq,
                                   const uint64_t pieces[2][6]) const {
    int feat_w_sub = ((stm == 0) ? 0 : 1) * 384 + pt * 64 + from_sq;
    int feat_w_add = ((stm == 0) ? 0 : 1) * 384 + pt * 64 + to_sq;

    int feat_b_sub = ((stm == 1) ? 0 : 1) * 384 + pt * 64 + (from_sq ^ 56);
    int feat_b_add = ((stm == 1) ? 0 : 1) * 384 + pt * 64 + (to_sq ^ 56);

    if (m_use_avx2) {
        update_accumulator_vector_avx2(next_acc->values[0], prev_acc->values[0], feat_w_sub, feat_w_add);
        update_accumulator_vector_avx2(next_acc->values[1], prev_acc->values[1], feat_b_sub, feat_b_add);
    } else {
        update_accumulator_vector(next_acc->values[0], prev_acc->values[0], feat_w_sub, feat_w_add);
        update_accumulator_vector(next_acc->values[1], prev_acc->values[1], feat_b_sub, feat_b_add);
    }
}

void NNUEEvaluatorV2::update_capture(Accumulator* next_acc, const Accumulator* prev_acc,
                                     int stm, int pt, int from_sq, int to_sq,
                                     int victim_color, int victim_pt,
                                     const uint64_t pieces[2][6]) const {
    // Two-step accumulator update: first quiet, then subtract captured piece
    update_quiet(next_acc, prev_acc, stm, pt, from_sq, to_sq, pieces);

    int feat_w_vic = ((victim_color == 0) ? 0 : 1) * 384 + victim_pt * 64 + to_sq;
    int feat_b_vic = ((victim_color == 1) ? 0 : 1) * 384 + victim_pt * 64 + (to_sq ^ 56);

    if (m_use_avx2) {
        update_accumulator_vector_avx2(next_acc->values[0], next_acc->values[0], feat_w_vic, -1);
        update_accumulator_vector_avx2(next_acc->values[1], next_acc->values[1], feat_b_vic, -1);
    } else {
        update_accumulator_vector(next_acc->values[0], next_acc->values[0], feat_w_vic, -1);
        update_accumulator_vector(next_acc->values[1], next_acc->values[1], feat_b_vic, -1);
    }
}

int NNUEEvaluatorV2::evaluate(const Accumulator* acc, int stm) const {
    if (m_use_avx2) {
        return evaluate_avx2(acc, stm);
    } else {
        return evaluate_scalar(acc, stm);
    }
}

int NNUEEvaluatorV2::evaluate_scalar(const Accumulator* acc, int stm) const {
    assert(m_loaded);
    const int16_t* acc_stm = acc->values[stm];
    const int16_t* acc_opp = acc->values[1 - stm];

    alignas(32) uint8_t dual_act[2 * MAX_ACCUM_DIM];
    int accum_dim = (int)m_header.accum_dim;

    for (int i = 0; i < accum_dim; i++) {
        int16_t v = acc_stm[i];
        dual_act[i] = (v <= 0) ? 0 : ((v >= 127) ? 127 : static_cast<uint8_t>(v));
    }
    for (int i = 0; i < accum_dim; i++) {
        int16_t v = acc_opp[i];
        dual_act[accum_dim + i] = (v <= 0) ? 0 : ((v >= 127) ? 127 : static_cast<uint8_t>(v));
    }

    int l1_dim = (int)m_header.l1_dim;
    int total_accum = 2 * accum_dim;
    alignas(32) int32_t l1_act[MAX_L1_DIM];

    for (int j = 0; j < l1_dim; j++) {
        const int8_t* w_row = m_fc1_weights + j * total_accum;
        int32_t sum = m_fc1_biases[j];
        for (int i = 0; i < total_accum; i++) {
            sum += static_cast<int32_t>(dual_act[i]) * static_cast<int32_t>(w_row[i]);
        }
        int32_t act = sum >> 6;
        l1_act[j] = (act <= 0) ? 0 : ((act >= 127) ? 127 : act);
    }

    int32_t l2_sum = m_fc2_bias;
    for (int j = 0; j < l1_dim; j++) {
        l2_sum += l1_act[j] * static_cast<int32_t>(m_fc2_weights[j]);
    }

    int score_cp = static_cast<int>((static_cast<int64_t>(l2_sum) * m_header.eval_scale) / 8192);
    return std::clamp(score_cp, -29000, 29000);
}

int NNUEEvaluatorV2::evaluate_avx2(const Accumulator* acc, int stm) const {
    assert(m_loaded);
    const int16_t* acc_stm = acc->values[stm];
    const int16_t* acc_opp = acc->values[1 - stm];

    alignas(32) uint8_t dual_act[2 * MAX_ACCUM_DIM];
    int accum_dim = (int)m_header.accum_dim;
    const __m256i v_clamp_max = _mm256_set1_epi8(127);

    // 1. Vectorized Clipped ReLU for Accumulators
    int num_acc_vecs = accum_dim / 16;
    for (int v = 0; v < num_acc_vecs; v += 2) {
        __m256i stm_lo = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc_stm + v * 16));
        __m256i stm_hi = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc_stm + (v + 1) * 16));
        __m256i packed_stm = _mm256_packus_epi16(stm_lo, stm_hi);
        __m256i clamped_stm = _mm256_min_epu8(packed_stm, v_clamp_max);
        
        // Fix cross-lane order of _mm256_packus_epi16
        __m256i perm_stm = _mm256_permute4x64_epi64(clamped_stm, _MM_SHUFFLE(3, 1, 2, 0));
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(dual_act + v * 16), perm_stm);

        __m256i opp_lo = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc_opp + v * 16));
        __m256i opp_hi = _mm256_load_si256(reinterpret_cast<const __m256i*>(acc_opp + (v + 1) * 16));
        __m256i packed_opp = _mm256_packus_epi16(opp_lo, opp_hi);
        __m256i clamped_opp = _mm256_min_epu8(packed_opp, v_clamp_max);
        __m256i perm_opp = _mm256_permute4x64_epi64(clamped_opp, _MM_SHUFFLE(3, 1, 2, 0));
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(dual_act + accum_dim + v * 16), perm_opp);
    }

    // 2. Vectorized Dense L1 Dot Product using _mm256_maddubs_epi16
    int l1_dim = (int)m_header.l1_dim;
    int total_accum = 2 * accum_dim;
    alignas(32) int32_t l1_act[MAX_L1_DIM];
    const __m256i v_ones = _mm256_set1_epi16(1);

    for (int j = 0; j < l1_dim; j++) {
        const int8_t* w_row = m_fc1_weights + j * total_accum;
        __m256i acc32 = _mm256_setzero_si256();

        for (int i = 0; i < total_accum; i += 32) {
            __m256i act_v = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(dual_act + i));
            __m256i w_v = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(w_row + i));

            // Unsigned 8-bit * Signed 8-bit -> Signed 16-bit
            __m256i prod16 = _mm256_maddubs_epi16(act_v, w_v);
            // Signed 16-bit * 1 + Signed 16-bit * 1 -> Signed 32-bit
            __m256i prod32 = _mm256_madd_epi16(prod16, v_ones);
            acc32 = _mm256_add_epi32(acc32, prod32);
        }

        // Horizontal sum of the 8 lanes of acc32
        __m128i lo = _mm256_castsi256_si128(acc32);
        __m128i hi = _mm256_extracti128_si256(acc32, 1);
        __m128i sum128 = _mm_add_epi32(lo, hi);
        sum128 = _mm_hadd_epi32(sum128, sum128);
        sum128 = _mm_hadd_epi32(sum128, sum128);

        int32_t sum = _mm_cvtsi128_si32(sum128) + m_fc1_biases[j];
        int32_t act = sum >> 6;
        l1_act[j] = (act <= 0) ? 0 : ((act >= 127) ? 127 : act);
    }

    // 3. Dense L2 Dot Product (16 or 32 elements)
    int32_t l2_sum = m_fc2_bias;
    for (int j = 0; j < l1_dim; j++) {
        l2_sum += l1_act[j] * static_cast<int32_t>(m_fc2_weights[j]);
    }

    int score_cp = static_cast<int>((static_cast<int64_t>(l2_sum) * m_header.eval_scale) / 8192);
    return std::clamp(score_cp, -29000, 29000);
}

} // namespace nnue_v2
