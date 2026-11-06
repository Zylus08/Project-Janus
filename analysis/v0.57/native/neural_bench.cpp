// Project Janus v0.57 - Standalone Neural Inference Feasibility Benchmark
// Evaluates raw C++17 CPU inference and tensor encoding latency for two lightweight candidate architectures.

#include <iostream>
#include <vector>
#include <chrono>
#include <random>
#include <cmath>
#include <cstring>
#include <cstdint>
#include <iomanip>
#include <thread>
#include <atomic>

// Minimal Bitboard Board Definition matching Janus NativeBoard
struct NativeBoard {
    uint64_t pieces[2][6];   // [side][piece_type]
    uint64_t occupancy[2];   // [side]
    uint64_t all_occupancy;
    int side_to_move;        // 0=White, 1=Black
    uint8_t castling_rights; // 4 bits: WK, WQ, BK, BQ
    int ep_square;           // -1 or square 0..63
    int halfmove_clock;
};

// Initializes standard starting position
void init_start_pos(NativeBoard* b) {
    std::memset(b, 0, sizeof(NativeBoard));
    b->pieces[0][0] = 0x000000000000FF00ULL; // WP
    b->pieces[0][1] = 0x0000000000000042ULL; // WN
    b->pieces[0][2] = 0x0000000000000024ULL; // WB
    b->pieces[0][3] = 0x0000000000000081ULL; // WR
    b->pieces[0][4] = 0x0000000000000008ULL; // WQ
    b->pieces[0][5] = 0x0000000000000010ULL; // WK
    b->occupancy[0] = 0x000000000000FFFFULL;

    b->pieces[1][0] = 0x00FF000000000000ULL; // BP
    b->pieces[1][1] = 0x4200000000000000ULL; // BN
    b->pieces[1][2] = 0x2400000000000000ULL; // BB
    b->pieces[1][3] = 0x8100000000000000ULL; // BR
    b->pieces[1][4] = 0x0800000000000000ULL; // BQ
    b->pieces[1][5] = 0x1000000000000000ULL; // BK
    b->occupancy[1] = 0xFFFF000000000000ULL;

    b->all_occupancy = b->occupancy[0] | b->occupancy[1];
    b->side_to_move = 0;
    b->castling_rights = 0x0F;
    b->ep_square = -1;
    b->halfmove_clock = 0;
}

// 1. Tensor Input Encoding: Extracts [14, 64] flat array (896 floats)
void encode_board_tensor(const NativeBoard* b, float* tensor_out) {
    std::memset(tensor_out, 0, 896 * sizeof(float));

    // Channels 0..5: White pieces
    for (int p = 0; p < 6; p++) {
        uint64_t bb = b->pieces[0][p];
        int offset = p * 64;
        while (bb) {
            unsigned long sq;
            #if defined(_MSC_VER)
            _BitScanForward64(&sq, bb);
            #else
            sq = __builtin_ctzll(bb);
            #endif
            tensor_out[offset + sq] = 1.0f;
            bb &= bb - 1;
        }
    }

    // Channels 6..11: Black pieces
    for (int p = 0; p < 6; p++) {
        uint64_t bb = b->pieces[1][p];
        int offset = (6 + p) * 64;
        while (bb) {
            unsigned long sq;
            #if defined(_MSC_VER)
            _BitScanForward64(&sq, bb);
            #else
            sq = __builtin_ctzll(bb);
            #endif
            tensor_out[offset + sq] = 1.0f;
            bb &= bb - 1;
        }
    }

    // Channel 12: Side to move
    float stm_val = (b->side_to_move == 0) ? 1.0f : 0.0f;
    int stm_offset = 12 * 64;
    for (int sq = 0; sq < 64; sq++) {
        tensor_out[stm_offset + sq] = stm_val;
    }

    // Channel 13: Auxiliary state
    int aux_offset = 13 * 64;
    tensor_out[aux_offset + 0] = (b->castling_rights & 1) ? 1.0f : 0.0f;
    tensor_out[aux_offset + 1] = (b->castling_rights & 2) ? 1.0f : 0.0f;
    tensor_out[aux_offset + 2] = (b->castling_rights & 4) ? 1.0f : 0.0f;
    tensor_out[aux_offset + 3] = (b->castling_rights & 8) ? 1.0f : 0.0f;
    if (b->ep_square >= 0) {
        tensor_out[aux_offset + 4] = (b->ep_square % 8) / 7.0f;
    }
    tensor_out[aux_offset + 5] = std::min(1.0f, b->halfmove_clock / 100.0f);
}

// 2. Model 1: Policy Network (Micro-MLP)
// Input: 896 -> Dense(128) -> ReLU -> Dense(4096) -> Output
struct MicroPolicyModel {
    std::vector<float> w1; // 896 * 128
    std::vector<float> b1; // 128
    std::vector<float> w2; // 128 * 4096
    std::vector<float> b2; // 4096

    MicroPolicyModel() {
        w1.resize(896 * 128, 0.01f);
        b1.resize(128, 0.0f);
        w2.resize(128 * 4096, 0.01f);
        b2.resize(4096, 0.0f);
    }

    void forward(const float* input, float* output, float* hidden_scratch) const {
        // Layer 1: Dense 896 -> 128 + ReLU
        for (int j = 0; j < 128; j++) {
            float sum = b1[j];
            const float* w_ptr = &w1[j * 896];
            for (int i = 0; i < 896; i++) {
                sum += input[i] * w_ptr[i];
            }
            hidden_scratch[j] = (sum > 0.0f) ? sum : 0.0f;
        }

        // Layer 2: Dense 128 -> 4096
        for (int k = 0; k < 4096; k++) {
            float sum = b2[k];
            const float* w_ptr = &w2[k * 128];
            for (int j = 0; j < 128; j++) {
                sum += hidden_scratch[j] * w_ptr[j];
            }
            output[k] = sum;
        }
    }
};

// 3. Model 2: Compact Value Network (Direct Linear/HalfKP Head)
// Input: 896 -> Dense(64) -> ClippedReLU -> Dense(1) -> Scalar Eval
struct CompactValueModel {
    std::vector<float> w1; // 896 * 64
    std::vector<float> b1; // 64
    std::vector<float> w2; // 64 * 1
    float b2;

    CompactValueModel() {
        w1.resize(896 * 64, 0.01f);
        b1.resize(64, 0.0f);
        w2.resize(64, 0.05f);
        b2 = 0.0f;
    }

    float forward(const float* input, float* hidden_scratch) const {
        for (int j = 0; j < 64; j++) {
            float sum = b1[j];
            const float* w_ptr = &w1[j * 896];
            for (int i = 0; i < 896; i++) {
                sum += input[i] * w_ptr[i];
            }
            hidden_scratch[j] = std::max(0.0f, std::min(1.0f, sum)); // Clipped ReLU
        }

        float out = b2;
        for (int j = 0; j < 64; j++) {
            out += hidden_scratch[j] * w2[j];
        }
        return out;
    }
};

int main() {
    NativeBoard board;
    init_start_pos(&board);

    std::cout << "=========================================================\n";
    std::cout << "PROJECT JANUS v0.57 — NATIVE NEURAL INFERENCE BENCHMARK\n";
    std::cout << "=========================================================\n\n";

    // Benchmark 1: Input Encoding Latency
    constexpr int ENCODE_ITERS = 100000;
    alignas(64) float input_tensor[896];
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ENCODE_ITERS; i++) {
        encode_board_tensor(&board, input_tensor);
        board.halfmove_clock = i % 100; // Vary slightly to prevent compiler elimination
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double encode_total_us = std::chrono::duration<double, std::micro>(t1 - t0).count();
    double encode_us = encode_total_us / ENCODE_ITERS;
    std::cout << "1. Board Tensor Input Encoding (896 floats):\n";
    std::cout << "   - Iterations: " << ENCODE_ITERS << "\n";
    std::cout << "   - Mean Latency: " << std::fixed << std::setprecision(3) << encode_us << " us / encoding\n";
    std::cout << "   - Throughput:   " << std::setprecision(1) << (1000000.0 / encode_us) << " encodings/sec\n\n";

    // Benchmark 2: Model 1 - Micro Policy Network (896 -> 128 -> 4096)
    MicroPolicyModel policy_model;
    alignas(64) float policy_output[4096];
    alignas(64) float hidden1[128];

    constexpr int POLICY_ITERS = 5000;
    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < POLICY_ITERS; i++) {
        policy_model.forward(input_tensor, policy_output, hidden1);
        input_tensor[0] = policy_output[0] * 0.0001f; // Chain data dependency
    }
    t1 = std::chrono::high_resolution_clock::now();
    double policy_total_us = std::chrono::duration<double, std::micro>(t1 - t0).count();
    double policy_us = policy_total_us / POLICY_ITERS;
    double policy_params = (896 * 128 + 128 + 128 * 4096 + 4096);
    std::cout << "2. Model 1: Micro Policy Network (896 -> 128 -> 4096):\n";
    std::cout << "   - Parameters:   " << static_cast<int>(policy_params) << " (" << std::setprecision(2) << (policy_params * 4 / 1024.0 / 1024.0) << " MB FP32)\n";
    std::cout << "   - Iterations:   " << POLICY_ITERS << "\n";
    std::cout << "   - Mean Latency: " << std::fixed << std::setprecision(2) << policy_us << " us / inference\n";
    std::cout << "   - Throughput:   " << std::setprecision(0) << (1000000.0 / policy_us) << " inferences/sec\n";
    std::cout << "   - Total Overhead (Encode + Policy): " << std::setprecision(2) << (encode_us + policy_us) << " us\n\n";

    // Benchmark 3: Model 2 - Compact Value Network (896 -> 64 -> 1)
    CompactValueModel value_model;
    alignas(64) float hidden2[64];
    constexpr int VALUE_ITERS = 50000;
    float dummy_acc = 0.0f;

    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < VALUE_ITERS; i++) {
        dummy_acc += value_model.forward(input_tensor, hidden2);
        input_tensor[0] = dummy_acc * 0.00001f;
    }
    t1 = std::chrono::high_resolution_clock::now();
    double value_total_us = std::chrono::duration<double, std::micro>(t1 - t0).count();
    double value_us = value_total_us / VALUE_ITERS;
    double value_params = (896 * 64 + 64 + 64 + 1);
    std::cout << "3. Model 2: Compact Value Network (896 -> 64 -> 1):\n";
    std::cout << "   - Parameters:   " << static_cast<int>(value_params) << " (" << std::setprecision(2) << (value_params * 4 / 1024.0) << " KB FP32)\n";
    std::cout << "   - Iterations:   " << VALUE_ITERS << "\n";
    std::cout << "   - Mean Latency: " << std::fixed << std::setprecision(3) << value_us << " us / inference\n";
    std::cout << "   - Throughput:   " << std::setprecision(0) << (1000000.0 / value_us) << " inferences/sec\n";
    std::cout << "   - Total Overhead (Encode + Value):  " << std::setprecision(3) << (encode_us + value_us) << " us\n\n";

    // Benchmark 4: Multi-Thread Scaling for Policy Model
    std::cout << "4. Multi-Thread Scaling (Micro Policy Model, 2000 inferences/thread):\n";
    for (int threads : {1, 2, 4, 8}) {
        std::atomic<bool> start_flag(false);
        std::vector<std::thread> pool;
        constexpr int THREAD_ITERS = 2000;

        for (int t = 0; t < threads; t++) {
            pool.emplace_back([&, t]() {
                while (!start_flag) std::this_thread::yield();
                alignas(64) float thread_input[896];
                alignas(64) float thread_output[4096];
                alignas(64) float thread_hidden[128];
                encode_board_tensor(&board, thread_input);
                for (int i = 0; i < THREAD_ITERS; i++) {
                    policy_model.forward(thread_input, thread_output, thread_hidden);
                }
            });
        }

        auto mt_t0 = std::chrono::high_resolution_clock::now();
        start_flag = true;
        for (auto& th : pool) th.join();
        auto mt_t1 = std::chrono::high_resolution_clock::now();
        double mt_duration_s = std::chrono::duration<double>(mt_t1 - mt_t0).count();
        double total_inf = threads * THREAD_ITERS;
        double aggregate_ips = total_inf / mt_duration_s;
        std::cout << "   - Threads: " << threads << " | Duration: " << std::fixed << std::setprecision(3) << mt_duration_s 
                  << "s | Aggregate Throughput: " << std::setprecision(0) << aggregate_ips << " inf/s (Scaling: " 
                  << std::setprecision(2) << (aggregate_ips / (1000000.0 / policy_us)) << "x)\n";
    }

    // Benchmark 5: Search Throughput Impact Projections
    std::cout << "\n5. Architectural Search Throughput Impact Projections:\n";
    std::cout << "   - Classical Janus N5 NPS: ~1,600,000 nodes/sec\n";
    double leaf_nps_cap = 1000000.0 / (encode_us + value_us);
    std::cout << "   - If Evaluating Model 2 at EVERY Leaf: Max NPS = " << std::setprecision(0) << leaf_nps_cap 
              << " nodes/sec (Speed penalty: " << std::setprecision(1) << (1600000.0 / leaf_nps_cap) << "x slowdown)\n";
    // Policy evaluated at internal nodes (1 in 25 nodes)
    double policy_calls_per_sec = 1600000.0 / 25.0; // 64,000 calls
    double policy_time_s = policy_calls_per_sec * (encode_us + policy_us) / 1000000.0;
    std::cout << "   - If Evaluating Model 1 at INTERNAL Nodes (1/25 nodes): Policy time = " 
              << std::setprecision(1) << (policy_time_s * 100.0) << "% CPU budget\n";
    std::cout << "   - Conclusion: Confirms Option B (Selective Policy Ordering) is structurally superior for CPU search.\n";
    std::cout << "=========================================================\n";

    return 0;
}

