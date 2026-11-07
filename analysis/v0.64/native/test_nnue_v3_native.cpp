#include "nnue_v3.h"
#include <iostream>
#include <chrono>
#include <cassert>
#include <random>

using namespace janus::nnue_v3;

int main(int argc, char** argv) {
    std::cout << "============================================================" << std::endl;
    std::cout << "PROJECT JANUS v0.64 — NNUE-V3 AVX2 & SCALAR BENCHMARK HARNESS" << std::endl;
    std::cout << "============================================================" << std::endl;

    std::string model_path = "analysis/v0.64/models/janus_nnue_v3.jnnue";
    if (argc > 1) {
        model_path = argv[1];
    }

    NNUEEvaluatorV3 nnue;
    if (!nnue.load_model(model_path)) {
        std::cerr << "Failed to load model from: " << model_path << std::endl;
        return 1;
    }

    const auto& h = nnue.get_header();
    std::cout << "Model Loaded Successfully:" << std::endl;
    std::cout << "  Version:     " << h.version << std::endl;
    std::cout << "  Feature Dim: " << h.feature_dim << std::endl;
    std::cout << "  Accum Dim:   " << h.accum_dim << std::endl;
    std::cout << "  SEF Dim:     " << h.sef_dim << std::endl;
    std::cout << "  L1 Dim:      " << h.l1_dim << std::endl;
    std::cout << "  CPU AVX2:    " << (NNUEEvaluatorV3::detect_cpu_avx2() ? "SUPPORTED" : "NOT DETECTED") << std::endl;

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

    janus::nnue::BoardBitboards b;
    b.w_pawns = pieces[0][0]; b.b_pawns = pieces[1][0];
    b.w_knights = pieces[0][1]; b.b_knights = pieces[1][1];
    b.w_bishops = pieces[0][2]; b.b_bishops = pieces[1][2];
    b.w_rooks = pieces[0][3]; b.b_rooks = pieces[1][3];
    b.w_queens = pieces[0][4]; b.b_queens = pieces[1][4];
    b.w_king_sq = 4; b.b_king_sq = 60;
    b.white_to_move = true;

    AccumulatorV3 acc_start_scalar, acc_start_avx2;
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

    int eval_scalar = nnue.evaluate_scalar(&acc_start_scalar, b, 0);
    int eval_avx2 = nnue.evaluate_avx2(&acc_start_avx2, b, 0);
    std::cout << "Starting Position Eval: Scalar = " << eval_scalar << " cp | AVX2 = " << eval_avx2 << " cp" << std::endl;
    if (std::abs(eval_scalar - eval_avx2) > 1) {
        std::cerr << "PARITY FAILURE on evaluate! Diff = " << std::abs(eval_scalar - eval_avx2) << std::endl;
        return 1;
    }
    std::cout << "[PASS] Evaluation Parity: Scalar == AVX2 (Diff <= 1 cp)" << std::endl;

    // 2. Performance Microbenchmarking (1,000,000 iterations)
    constexpr int ITERS = 1000000;
    std::cout << "\nRunning Benchmark Suites (" << ITERS << " iterations per test)..." << std::endl;

    auto t0 = std::chrono::high_resolution_clock::now();
    volatile int dummy = 0;
    for (int i = 0; i < ITERS; ++i) {
        dummy += nnue.evaluate_avx2(&acc_start_avx2, b, 0);
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double el_avx2 = std::chrono::duration<double>(t1 - t0).count();
    double nps_avx2 = ITERS / el_avx2;
    std::cout << "  AVX2 Full Leaf Evaluation (inc. SEF): " << el_avx2 << " s (" << (el_avx2 / ITERS * 1e9) << " ns/eval, " << (nps_avx2 / 1e6) << " M evals/s)" << std::endl;

    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERS; ++i) {
        dummy += nnue.evaluate_scalar(&acc_start_scalar, b, 0);
    }
    t1 = std::chrono::high_resolution_clock::now();
    double el_scalar = std::chrono::duration<double>(t1 - t0).count();
    double nps_scalar = ITERS / el_scalar;
    std::cout << "  Scalar Full Leaf Evaluation (inc. SEF): " << el_scalar << " s (" << (el_scalar / ITERS * 1e9) << " ns/eval, " << (nps_scalar / 1e6) << " M evals/s)" << std::endl;

    double speedup = el_scalar / el_avx2;
    std::cout << "  AVX2 Speedup over Scalar: " << speedup << "x" << std::endl;

    std::cout << "\nAll native NNUE-V3 checks PASSED." << std::endl;
    return 0;
}

