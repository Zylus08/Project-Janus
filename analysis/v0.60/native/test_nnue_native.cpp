#include "nnue_v1.h"
#include <iostream>
#include <cassert>
#include <chrono>
#include <random>

// Standalone verification and benchmark harness for NNUE native core
int main(int argc, char** argv) {
    std::cout << "============================================================" << std::endl;
    std::cout << "PROJECT JANUS v0.60 — NNUE NATIVE VERIFICATION & BENCHMARK" << std::endl;
    std::cout << "============================================================" << std::endl;

    std::string model_path = "analysis/v0.60/models/janus_nnue_v1_small.jnnue";
    if (argc > 1) {
        model_path = argv[1];
    }

    NNUEEvaluator nnue;
    if (!nnue.load_model(model_path)) {
        std::cerr << "Failed to load model from: " << model_path << std::endl;
        return 1;
    }

    const auto& h = nnue.get_header();
    std::cout << "Model Loaded Successfully:" << std::endl;
    std::cout << "  Arch ID: " << h.arch_id << std::endl;
    std::cout << "  Feature Dim: " << h.feature_dim << std::endl;
    std::cout << "  Accum Dim: " << h.accum_dim << std::endl;
    std::cout << "  L1 Dim: " << h.l1_dim << std::endl;
    std::cout << "  Eval Scale: " << h.eval_scale << std::endl;

    // Test starting position
    // Initial standard board bitboards
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

    Accumulator acc_start;
    nnue.full_refresh(pieces, 0 /*WHITE*/, &acc_start);

    int start_eval = nnue.evaluate(&acc_start, 0 /*WHITE*/);
    std::cout << "Starting Position Eval (White STM): " << start_eval << " cp" << std::endl;

    // Symmetry check: from Black STM, starting pos should be symmetric
    int start_eval_b = nnue.evaluate(&acc_start, 1 /*BLACK*/);
    std::cout << "Starting Position Eval (Black STM): " << start_eval_b << " cp" << std::endl;

    // 1. Invariant Test: 1. e2-e4 quiet move
    // Remove e2 (sq 12), Add e4 (sq 28)
    Accumulator acc_e4_inc;
    nnue.update_quiet(&acc_e4_inc, &acc_start, 0 /*WHITE*/, 0 /*PAWN*/, 12, 28, pieces);

    // Apply move to bitboards
    uint64_t pieces_e4[2][6];
    std::memcpy(pieces_e4, pieces, sizeof(pieces));
    pieces_e4[0][0] &= ~(1ULL << 12);
    pieces_e4[0][0] |= (1ULL << 28);

    Accumulator acc_e4_full;
    nnue.full_refresh(pieces_e4, 1 /*BLACK*/, &acc_e4_full);

    // Assert exact equality between incremental and full refresh
    for (int p = 0; p < 2; p++) {
        for (int j = 0; j < (int)h.accum_dim; j++) {
            if (acc_e4_inc.values[p][j] != acc_e4_full.values[p][j]) {
                std::cerr << "INVARIANT FAILURE on 1. e4: p=" << p << " j=" << j
                          << " inc=" << acc_e4_inc.values[p][j]
                          << " full=" << acc_e4_full.values[p][j] << std::endl;
                return 1;
            }
        }
    }
    std::cout << "[PASS] Invariant Verified: Quiet Move (1. e4) Incremental == Full Refresh" << std::endl;

    // 2. Invariant Test: Capture move
    // Setup a legal pawn to capture at sq 35 (d5)
    pieces_e4[1][0] |= (1ULL << 35);
    nnue.full_refresh(pieces_e4, 0, &acc_e4_inc);

    Accumulator acc_cap_inc;
    nnue.update_capture(&acc_cap_inc, &acc_e4_inc, 0 /*WHITE*/, 0 /*PAWN*/, 28 /*e4*/, 35 /*d5*/, 1 /*BLACK*/, 0 /*PAWN*/, pieces_e4);

    uint64_t pieces_cap[2][6];
    std::memcpy(pieces_cap, pieces_e4, sizeof(pieces_e4));
    pieces_cap[0][0] &= ~(1ULL << 28);
    pieces_cap[0][0] |= (1ULL << 35);
    pieces_cap[1][0] &= ~(1ULL << 35); // Captured

    Accumulator acc_cap_full;
    nnue.full_refresh(pieces_cap, 1, &acc_cap_full);

    for (int p = 0; p < 2; p++) {
        for (int j = 0; j < (int)h.accum_dim; j++) {
            if (acc_cap_inc.values[p][j] != acc_cap_full.values[p][j]) {
                std::cerr << "INVARIANT FAILURE on capture: p=" << p << " j=" << j
                          << " inc=" << acc_cap_inc.values[p][j]
                          << " full=" << acc_cap_full.values[p][j] << std::endl;
                return 1;
            }
        }
    }
    std::cout << "[PASS] Invariant Verified: Capture Move Incremental == Full Refresh" << std::endl;

    // 3. CPU Latency Benchmark
    constexpr int ITERS = 1000000;
    std::cout << "\nBenchmarking CPU Performance (" << ITERS << " iterations)..." << std::endl;

    // A. Full Refresh Benchmark
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < 50000; i++) {
        nnue.full_refresh(pieces, 0, &acc_start);
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double full_ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / 50000.0;

    // B. Incremental Update Benchmark
    Accumulator acc_bench = acc_start;
    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERS; i++) {
        nnue.update_quiet(&acc_bench, &acc_bench, 0, 0, 12, 28, pieces);
    }
    t1 = std::chrono::high_resolution_clock::now();
    double inc_ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / ITERS;

    // C. Quantized Feedforward Inference Benchmark
    volatile int dummy = 0;
    t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERS; i++) {
        dummy += nnue.evaluate(&acc_start, 0);
    }
    t1 = std::chrono::high_resolution_clock::now();
    double eval_ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / ITERS;

    std::cout << "Performance Results:" << std::endl;
    std::cout << "  Full Accumulator Refresh: " << full_ns << " ns" << std::endl;
    std::cout << "  Incremental Move Update:  " << inc_ns << " ns" << std::endl;
    std::cout << "  Feedforward Evaluation:   " << eval_ns << " ns" << std::endl;
    std::cout << "  End-to-End Leaf Latency:  " << (inc_ns + eval_ns) << " ns ("
              << (1e9 / (inc_ns + eval_ns)) << " evals/sec)" << std::endl;

    std::cout << "\nALL NATIVE VERIFICATION GATES PASSED." << std::endl;
    return 0;
}
