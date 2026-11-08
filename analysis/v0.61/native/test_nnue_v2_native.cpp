#include "nnue_v2.h"
#include <iostream>
#include <chrono>
#include <cassert>
#include <random>

using namespace nnue_v2;

int main(int argc, char** argv) {
    std::cout << "============================================================" << std::endl;
    std::cout << "PROJECT JANUS v0.61 — NNUE-V2 AVX2 & SCALAR BENCHMARK HARNESS" << std::endl;
    std::cout << "============================================================" << std::endl;

    std::string model_path = "analysis/v0.61/models/janus_nnue_v2_small.jnnue";
    if (argc > 1) {
        model_path = argv[1];
    }

    NNUEEvaluatorV2 nnue;
    if (!nnue.load_model(model_path)) {
        std::cerr << "Failed to load model from: " << model_path << std::endl;
        return 1;
    }

    const auto& h = nnue.get_header();
    std::cout << "Model Loaded Successfully:" << std::endl;
    std::cout << "  Arch ID:     " << h.arch_id << std::endl;
    std::cout << "  Feature Dim: " << h.feature_dim << std::endl;
    std::cout << "  Accum Dim:   " << h.accum_dim << std::endl;
    std::cout << "  L1 Dim:      " << h.l1_dim << std::endl;
    std::cout << "  CPU AVX2:    " << (nnue_v2::NNUEEvaluatorV2::detect_cpu_avx2() ? "SUPPORTED" : "NOT DETECTED") << std::endl;

    // Standard starting position bitboards
    uint64_t pieces[2][6] = { 0 };
    pieces[0][0] = 0x000000000000FF00ULL; // White pawns
    pieces[0][1] = 0x0000000000000042ULL; // White knights
    pieces[0][2] = 0x0000000000000024ULL; // White bishops
    pieces[0][3] = 0x0000000000000081ULL; // White rooks
    pieces[0][4] = 0x0000000000000008ULL; // White queen
    pieces[0][5] = 0x0000000000000010ULL; // White king

    pieces[1][0] = 0x00FF000000000000ULL; // Black pawns
    pieces[1][1] = 0x4200000000000000ULL; // Black knights
    pieces[1][2] = 0x2400000000000000ULL; // Black bishops
    pieces[1][3] = 0x8100000000000000ULL; // Black rooks
    pieces[1][4] = 0x0800000000000000ULL; // Black queen
    pieces[1][5] = 0x1000000000000000ULL; // Black king

    Accumulator acc_start_scalar, acc_start_avx2;
    nnue.set_use_avx2(false);
    nnue.full_refresh(pieces, 0, &acc_start_scalar);

    nnue.set_use_avx2(true);
    nnue.full_refresh(pieces, 0, &acc_start_avx2);

    // 1. Bit-Exact Parity Check: Scalar vs AVX2
    for (int p = 0; p < 2; p++) {
        for (int j = 0; j < (int)h.accum_dim; j++) {
            if (acc_start_scalar.values[p][j] != acc_start_avx2.values[p][j]) {
                std::cerr << "PARITY FAILURE on full refresh! p=" << p << " j=" << j
                          << " scalar=" << acc_start_scalar.values[p][j]
                          << " avx2=" << acc_start_avx2.values[p][j] << std::endl;
                return 1;
            }
        }
    }
    std::cout << "[PASS] Full Refresh Parity: Scalar == AVX2 (Bit-Exact)" << std::endl;

    int eval_scalar = nnue.evaluate_scalar(&acc_start_scalar, 0);
    int eval_avx2 = nnue.evaluate_avx2(&acc_start_avx2, 0);
    std::cout << "Starting Position Eval: Scalar = " << eval_scalar << " cp | AVX2 = " << eval_avx2 << " cp" << std::endl;
    if (std::abs(eval_scalar - eval_avx2) > 1) {
        std::cerr << "PARITY FAILURE on evaluate! Diff = " << std::abs(eval_scalar - eval_avx2) << std::endl;
        return 1;
    }
    std::cout << "[PASS] Evaluation Parity: Scalar == AVX2 (Diff <= 1 cp)" << std::endl;

    // 2. Incremental Move Updates Parity
    Accumulator acc_move_scalar, acc_move_avx2;
    nnue.set_use_avx2(false);
    nnue.update_quiet(&acc_move_scalar, &acc_start_scalar, 0, 0, 12, 28, pieces);

    nnue.set_use_avx2(true);
    nnue.update_quiet(&acc_move_avx2, &acc_start_avx2, 0, 0, 12, 28, pieces);

    for (int p = 0; p < 2; p++) {
        for (int j = 0; j < (int)h.accum_dim; j++) {
            if (acc_move_scalar.values[p][j] != acc_move_avx2.values[p][j]) {
                std::cerr << "PARITY FAILURE on 1. e4 quiet update! p=" << p << " j=" << j
                          << " scalar=" << acc_move_scalar.values[p][j]
                          << " avx2=" << acc_move_avx2.values[p][j] << std::endl;
                return 1;
            }
        }
    }
    std::cout << "[PASS] Incremental Quiet Move Parity: Scalar == AVX2 (Bit-Exact)" << std::endl;

    // 3. Performance Microbenchmarking (1,000,000 iterations)
    constexpr int ITERS = 1000000;
    std::cout << "\nRunning Benchmark Suites (" << ITERS << " iterations per test)..." << std::endl;

    // A. Full Refresh Benchmark
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < 50000; i++) {
        nnue.set_use_avx2(false);
        nnue.full_refresh(pieces, 0, &acc_start_scalar);
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double refresh_scalar_ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / 50000.0;

    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < 50000; i++) {
        nnue.set_use_avx2(true);
        nnue.full_refresh(pieces, 0, &acc_start_avx2);
    }
    t1 = std::chrono::high_resolution_clock::now();
    double refresh_avx2_ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / 50000.0;

    // B. Incremental Move Update Benchmark
    Accumulator acc_bench = acc_start_scalar;
    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERS; i++) {
        nnue.set_use_avx2(false);
        nnue.update_quiet(&acc_bench, &acc_bench, 0, 0, 12, 28, pieces);
    }
    t1 = std::chrono::high_resolution_clock::now();
    double update_scalar_ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / ITERS;

    acc_bench = acc_start_avx2;
    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERS; i++) {
        nnue.set_use_avx2(true);
        nnue.update_quiet(&acc_bench, &acc_bench, 0, 0, 12, 28, pieces);
    }
    t1 = std::chrono::high_resolution_clock::now();
    double update_avx2_ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / ITERS;

    // C. Feedforward Inference Benchmark
    volatile int dummy = 0;
    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERS; i++) {
        dummy += nnue.evaluate_scalar(&acc_start_scalar, 0);
    }
    t1 = std::chrono::high_resolution_clock::now();
    double eval_scalar_ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / ITERS;

    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERS; i++) {
        dummy += nnue.evaluate_avx2(&acc_start_avx2, 0);
    }
    t1 = std::chrono::high_resolution_clock::now();
    double eval_avx2_ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / ITERS;

    double total_leaf_scalar = update_scalar_ns + eval_scalar_ns;
    double total_leaf_avx2 = update_avx2_ns + eval_avx2_ns;

    std::cout << "\n============================================================" << std::endl;
    std::cout << "BENCHMARK RESULTS SUMMARY:" << std::endl;
    std::cout << "============================================================" << std::endl;
    std::cout << "Component                     | Scalar C++17 | AVX2 SIMD   | Speedup" << std::endl;
    std::cout << "------------------------------+--------------+-------------+--------" << std::endl;
    std::cout << "Full Refresh Latency:         | " << refresh_scalar_ns << " ns    | " << refresh_avx2_ns << " ns   | "
              << (refresh_scalar_ns / refresh_avx2_ns) << "x" << std::endl;
    std::cout << "Incremental Quiet Update:     | " << update_scalar_ns << " ns     | " << update_avx2_ns << " ns    | "
              << (update_scalar_ns / update_avx2_ns) << "x" << std::endl;
    std::cout << "Feedforward Inference (L1+L2):| " << eval_scalar_ns << " ns    | " << eval_avx2_ns << " ns    | "
              << (eval_scalar_ns / eval_avx2_ns) << "x" << std::endl;
    std::cout << "End-to-End Leaf Latency:      | " << total_leaf_scalar << " ns    | " << total_leaf_avx2 << " ns    | "
              << (total_leaf_scalar / total_leaf_avx2) << "x" << std::endl;
    std::cout << "Isolated Leaf Throughput:     | " << (1e9 / total_leaf_scalar / 1e6) << "M/s   | "
              << (1e9 / total_leaf_avx2 / 1e6) << "M/s  | "
              << (total_leaf_scalar / total_leaf_avx2) << "x" << std::endl;
    std::cout << "============================================================" << std::endl;

    return 0;
}

