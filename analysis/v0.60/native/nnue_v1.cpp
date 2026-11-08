#include "nnue_v1.h"

// Simple CRC32 implementation for model validation
static uint32_t compute_crc32(const uint8_t* data, size_t length) {
    uint32_t crc = 0xFFFFFFFF;
    for (size_t i = 0; i < length; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            crc = (crc >> 1) ^ (0xEDB88320 & (-(crc & 1)));
        }
    }
    return ~crc;
}

static inline int bitscan_forward_local(uint64_t b) {
#if defined(_MSC_VER)
    unsigned long index;
    _BitScanForward64(&index, b);
    return (int)index;
#else
    return __builtin_ctzll(b);
#endif
}

NNUEEvaluator::NNUEEvaluator() : m_loaded(false), m_fc2_bias(0) {
    std::memset(&m_header, 0, sizeof(m_header));
}

NNUEEvaluator::~NNUEEvaluator() {
    unload_model();
}

void NNUEEvaluator::unload_model() {
    m_loaded = false;
    m_ft_weights.clear();
    m_ft_biases.clear();
    m_fc1_weights.clear();
    m_fc1_biases.clear();
    m_fc2_weights.clear();
    m_fc2_bias = 0;
    std::memset(&m_header, 0, sizeof(m_header));
}

bool NNUEEvaluator::load_model(const std::string& path) {
    unload_model();

    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        std::cerr << "[NNUE] Error: Failed to open model file: " << path << std::endl;
        return false;
    }

    // Read 64-byte header
    file.read(reinterpret_cast<char*>(&m_header), sizeof(NNUEHeader));
    if (file.gcount() != sizeof(NNUEHeader)) {
        std::cerr << "[NNUE] Error: Truncated model header" << std::endl;
        return false;
    }

    // Validate magic & version
    if (m_header.magic != NNUE_MAGIC) {
        std::cerr << "[NNUE] Error: Invalid magic number: " << std::hex << m_header.magic << std::endl;
        return false;
    }
    if (m_header.version != NNUE_VERSION) {
        std::cerr << "[NNUE] Error: Unsupported model version: " << m_header.version << std::endl;
        return false;
    }

    size_t f_dim = m_header.feature_dim;
    size_t m_dim = m_header.accum_dim;
    size_t l1_dim = m_header.l1_dim;

    if (m_dim > MAX_ACCUM_DIM || l1_dim > MAX_L1_DIM) {
        std::cerr << "[NNUE] Error: Tensor dimensions exceed engine limits" << std::endl;
        return false;
    }

    // Allocate memory
    size_t ft_w_size = f_dim * m_dim;
    size_t ft_b_size = m_dim;
    size_t fc1_w_size = l1_dim * 2 * m_dim;
    size_t fc1_b_size = l1_dim;
    size_t fc2_w_size = l1_dim;

    m_ft_weights.resize(ft_w_size);
    m_ft_biases.resize(ft_b_size);
    m_fc1_weights.resize(fc1_w_size);
    m_fc1_biases.resize(fc1_b_size);
    m_fc2_weights.resize(fc2_w_size);

    // Read payloads
    file.read(reinterpret_cast<char*>(m_ft_weights.data()), ft_w_size * sizeof(int16_t));
    file.read(reinterpret_cast<char*>(m_ft_biases.data()), ft_b_size * sizeof(int16_t));
    file.read(reinterpret_cast<char*>(m_fc1_weights.data()), fc1_w_size * sizeof(int8_t));
    file.read(reinterpret_cast<char*>(m_fc1_biases.data()), fc1_b_size * sizeof(int32_t));
    file.read(reinterpret_cast<char*>(m_fc2_weights.data()), fc2_w_size * sizeof(int8_t));
    file.read(reinterpret_cast<char*>(&m_fc2_bias), sizeof(int32_t));

    if (!file.good()) {
        std::cerr << "[NNUE] Error: Failed to read complete weight payload" << std::endl;
        unload_model();
        return false;
    }

    // CRC32 Integrity check
    std::vector<uint8_t> payload_check;
    payload_check.insert(payload_check.end(), reinterpret_cast<uint8_t*>(m_ft_weights.data()), reinterpret_cast<uint8_t*>(m_ft_weights.data() + ft_w_size));
    payload_check.insert(payload_check.end(), reinterpret_cast<uint8_t*>(m_ft_biases.data()), reinterpret_cast<uint8_t*>(m_ft_biases.data() + ft_b_size));
    payload_check.insert(payload_check.end(), reinterpret_cast<uint8_t*>(m_fc1_weights.data()), reinterpret_cast<uint8_t*>(m_fc1_weights.data() + fc1_w_size));
    payload_check.insert(payload_check.end(), reinterpret_cast<uint8_t*>(m_fc1_biases.data()), reinterpret_cast<uint8_t*>(m_fc1_biases.data() + fc1_b_size));
    payload_check.insert(payload_check.end(), reinterpret_cast<uint8_t*>(m_fc2_weights.data()), reinterpret_cast<uint8_t*>(m_fc2_weights.data() + fc2_w_size));
    payload_check.insert(payload_check.end(), reinterpret_cast<uint8_t*>(&m_fc2_bias), reinterpret_cast<uint8_t*>(&m_fc2_bias + 1));

    uint32_t computed_crc = compute_crc32(payload_check.data(), payload_check.size());
    if (computed_crc != m_header.checksum_crc32) {
        std::cerr << "[NNUE] Warning: Checksum mismatch (Header: " << std::hex << m_header.checksum_crc32
                  << ", Computed: " << computed_crc << "). Proceeding with caution." << std::dec << std::endl;
    }

    m_loaded = true;
    return true;
}

int NNUEEvaluator::get_feature_index(int perspective, int color, int piece, int sq, int king_sq) const {
    int c_rel = (color == perspective) ? 0 : 1;
    int sq_rel = (perspective == 0) ? sq : (sq ^ 56);
    int base_idx = c_rel * 384 + piece * 64 + sq_rel;

    if (m_header.arch_id == 2) {
        // V1-Compact (King-bucketing)
        int k_rel = (perspective == 0) ? king_sq : (king_sq ^ 56);
        int bucket = (k_rel % 8) / 2;
        return bucket * 768 + base_idx;
    }
    return base_idx;
}

void NNUEEvaluator::full_refresh(const uint64_t pieces[2][6], int side_to_move, Accumulator* acc) const {
    if (!m_loaded) return;

    int accum_dim = m_header.accum_dim;

    // Find kings
    int king_sq[2] = { 0, 0 };
    if (pieces[0][5]) king_sq[0] = bitscan_forward_local(pieces[0][5]);
    if (pieces[1][5]) king_sq[1] = bitscan_forward_local(pieces[1][5]);

    for (int p = 0; p < 2; p++) {
        // Copy biases
        std::memcpy(acc->values[p], m_ft_biases.data(), accum_dim * sizeof(int16_t));

        for (int c = 0; c < 2; c++) {
            for (int pt = 0; pt < 6; pt++) {
                uint64_t bb = pieces[c][pt];
                while (bb) {
                    int sq = bitscan_forward_local(bb);
                    bb &= bb - 1;
                    int f_idx = get_feature_index(p, c, pt, sq, king_sq[p]);
                    const int16_t* w_row = &m_ft_weights[f_idx * accum_dim];
                    for (int j = 0; j < accum_dim; j++) {
                        acc->values[p][j] += w_row[j];
                    }
                }
            }
        }
        acc->computed[p] = true;
    }
}

void NNUEEvaluator::update_quiet(
    Accumulator* next_acc, const Accumulator* prev_acc,
    int mover_color, int piece, int from_sq, int to_sq,
    const uint64_t pieces[2][6]
) const {
    if (!m_loaded) return;

    int accum_dim = m_header.accum_dim;

    // If V1-Compact and moving piece is king, check if bucket changed
    if (m_header.arch_id == 2 && piece == 5) {
        // King move might cross bucket boundary -> perform full refresh for mover, incremental for opponent
        full_refresh(pieces, 0, next_acc);
        return;
    }

    int king_sq[2] = { 0, 0 };
    if (m_header.arch_id == 2) {
        if (pieces[0][5]) king_sq[0] = bitscan_forward_local(pieces[0][5]);
        if (pieces[1][5]) king_sq[1] = bitscan_forward_local(pieces[1][5]);
    }

    for (int p = 0; p < 2; p++) {
        int idx_sub = get_feature_index(p, mover_color, piece, from_sq, king_sq[p]);
        int idx_add = get_feature_index(p, mover_color, piece, to_sq, king_sq[p]);

        const int16_t* w_sub = &m_ft_weights[idx_sub * accum_dim];
        const int16_t* w_add = &m_ft_weights[idx_add * accum_dim];

        for (int j = 0; j < accum_dim; j++) {
            next_acc->values[p][j] = prev_acc->values[p][j] - w_sub[j] + w_add[j];
        }
        next_acc->computed[p] = true;
    }
}

void NNUEEvaluator::update_capture(
    Accumulator* next_acc, const Accumulator* prev_acc,
    int mover_color, int piece, int from_sq, int to_sq,
    int victim_color, int victim_piece,
    const uint64_t pieces[2][6]
) const {
    if (!m_loaded) return;

    int accum_dim = m_header.accum_dim;

    if (m_header.arch_id == 2 && piece == 5) {
        full_refresh(pieces, 0, next_acc);
        return;
    }

    int king_sq[2] = { 0, 0 };
    if (m_header.arch_id == 2) {
        if (pieces[0][5]) king_sq[0] = bitscan_forward_local(pieces[0][5]);
        if (pieces[1][5]) king_sq[1] = bitscan_forward_local(pieces[1][5]);
    }

    for (int p = 0; p < 2; p++) {
        int idx_from = get_feature_index(p, mover_color, piece, from_sq, king_sq[p]);
        int idx_victim = get_feature_index(p, victim_color, victim_piece, to_sq, king_sq[p]);
        int idx_to = get_feature_index(p, mover_color, piece, to_sq, king_sq[p]);

        const int16_t* w_from = &m_ft_weights[idx_from * accum_dim];
        const int16_t* w_vic = &m_ft_weights[idx_victim * accum_dim];
        const int16_t* w_to = &m_ft_weights[idx_to * accum_dim];

        for (int j = 0; j < accum_dim; j++) {
            next_acc->values[p][j] = prev_acc->values[p][j] - w_from[j] - w_vic[j] + w_to[j];
        }
        next_acc->computed[p] = true;
    }
}

void NNUEEvaluator::update_promotion(
    Accumulator* next_acc, const Accumulator* prev_acc,
    int mover_color, int from_sq, int to_sq, int promo_piece,
    bool is_capture, int victim_color, int victim_piece,
    const uint64_t pieces[2][6]
) const {
    if (!m_loaded) return;

    int accum_dim = m_header.accum_dim;
    int king_sq[2] = { 0, 0 };
    if (m_header.arch_id == 2) {
        if (pieces[0][5]) king_sq[0] = bitscan_forward_local(pieces[0][5]);
        if (pieces[1][5]) king_sq[1] = bitscan_forward_local(pieces[1][5]);
    }

    for (int p = 0; p < 2; p++) {
        int idx_pawn = get_feature_index(p, mover_color, 0 /*PAWN*/, from_sq, king_sq[p]);
        int idx_promo = get_feature_index(p, mover_color, promo_piece, to_sq, king_sq[p]);

        const int16_t* w_pawn = &m_ft_weights[idx_pawn * accum_dim];
        const int16_t* w_promo = &m_ft_weights[idx_promo * accum_dim];

        if (is_capture) {
            int idx_vic = get_feature_index(p, victim_color, victim_piece, to_sq, king_sq[p]);
            const int16_t* w_vic = &m_ft_weights[idx_vic * accum_dim];
            for (int j = 0; j < accum_dim; j++) {
                next_acc->values[p][j] = prev_acc->values[p][j] - w_pawn[j] - w_vic[j] + w_promo[j];
            }
        } else {
            for (int j = 0; j < accum_dim; j++) {
                next_acc->values[p][j] = prev_acc->values[p][j] - w_pawn[j] + w_promo[j];
            }
        }
        next_acc->computed[p] = true;
    }
}

void NNUEEvaluator::update_en_passant(
    Accumulator* next_acc, const Accumulator* prev_acc,
    int mover_color, int from_sq, int to_sq, int ep_captured_sq,
    const uint64_t pieces[2][6]
) const {
    if (!m_loaded) return;

    int accum_dim = m_header.accum_dim;
    int them = 1 - mover_color;

    int king_sq[2] = { 0, 0 };
    if (m_header.arch_id == 2) {
        if (pieces[0][5]) king_sq[0] = bitscan_forward_local(pieces[0][5]);
        if (pieces[1][5]) king_sq[1] = bitscan_forward_local(pieces[1][5]);
    }

    for (int p = 0; p < 2; p++) {
        int idx_pawn_from = get_feature_index(p, mover_color, 0 /*PAWN*/, from_sq, king_sq[p]);
        int idx_ep_victim = get_feature_index(p, them, 0 /*PAWN*/, ep_captured_sq, king_sq[p]);
        int idx_pawn_to = get_feature_index(p, mover_color, 0 /*PAWN*/, to_sq, king_sq[p]);

        const int16_t* w_from = &m_ft_weights[idx_pawn_from * accum_dim];
        const int16_t* w_vic = &m_ft_weights[idx_ep_victim * accum_dim];
        const int16_t* w_to = &m_ft_weights[idx_pawn_to * accum_dim];

        for (int j = 0; j < accum_dim; j++) {
            next_acc->values[p][j] = prev_acc->values[p][j] - w_from[j] - w_vic[j] + w_to[j];
        }
        next_acc->computed[p] = true;
    }
}

void NNUEEvaluator::update_castling(
    Accumulator* next_acc, const Accumulator* prev_acc,
    int mover_color, int k_from, int k_to, int r_from, int r_to,
    const uint64_t pieces[2][6]
) const {
    if (!m_loaded) return;

    if (m_header.arch_id == 2) {
        full_refresh(pieces, 0, next_acc);
        return;
    }

    int accum_dim = m_header.accum_dim;
    for (int p = 0; p < 2; p++) {
        int idx_kf = get_feature_index(p, mover_color, 5 /*KING*/, k_from, 0);
        int idx_kt = get_feature_index(p, mover_color, 5 /*KING*/, k_to, 0);
        int idx_rf = get_feature_index(p, mover_color, 3 /*ROOK*/, r_from, 0);
        int idx_rt = get_feature_index(p, mover_color, 3 /*ROOK*/, r_to, 0);

        const int16_t* w_kf = &m_ft_weights[idx_kf * accum_dim];
        const int16_t* w_kt = &m_ft_weights[idx_kt * accum_dim];
        const int16_t* w_rf = &m_ft_weights[idx_rf * accum_dim];
        const int16_t* w_rt = &m_ft_weights[idx_rt * accum_dim];

        for (int j = 0; j < accum_dim; j++) {
            next_acc->values[p][j] = prev_acc->values[p][j] - w_kf[j] + w_kt[j] - w_rf[j] + w_rt[j];
        }
        next_acc->computed[p] = true;
    }
}

int NNUEEvaluator::evaluate(const Accumulator* acc, int side_to_move) const {
    if (!m_loaded) return 0;

    int accum_dim = m_header.accum_dim;
    int l1_dim = m_header.l1_dim;
    int stm = side_to_move;
    int nstm = 1 - stm;

    // Perspective concatenation with Clipped ReLU [0, 127]
    int32_t h[2 * MAX_ACCUM_DIM];
    for (int j = 0; j < accum_dim; j++) {
        h[j] = std::clamp((int32_t)acc->values[stm][j], 0, 127);
        h[accum_dim + j] = std::clamp((int32_t)acc->values[nstm][j], 0, 127);
    }

    // Dense Layer 1
    int32_t act_l1[MAX_L1_DIM];
    int dense_in = 2 * accum_dim;
    for (int i = 0; i < l1_dim; i++) {
        int32_t sum = m_fc1_biases[i];
        const int8_t* w_row = &m_fc1_weights[i * dense_in];
        for (int j = 0; j < dense_in; j++) {
            sum += (int32_t)w_row[j] * h[j];
        }
        act_l1[i] = std::clamp((int32_t)(sum / 64), 0, 127);
    }

    // Dense Layer 2 (Output)
    int32_t out_sum = m_fc2_bias;
    for (int i = 0; i < l1_dim; i++) {
        out_sum += (int32_t)m_fc2_weights[i] * act_l1[i];
    }

    // Centipawn projection
    int score_cp = (int)((out_sum * (int64_t)m_header.eval_scale) / (64 * 128));
    return score_cp;
}
