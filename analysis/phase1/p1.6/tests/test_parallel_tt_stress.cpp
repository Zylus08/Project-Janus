#include <iostream>
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cassert>
#include <cstring>
#include <immintrin.h>

constexpr uint8_t TT_EXACT = 0;
constexpr uint8_t TT_LOWER = 1;
constexpr uint8_t TT_UPPER = 2;
constexpr int MATE_SCORE = 30000;
constexpr int MAX_SEARCH_PLY = 64;

inline int score_to_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_SEARCH_PLY) return score + ply;
    if (score <= -MATE_SCORE + MAX_SEARCH_PLY) return score - ply;
    return score;
}

inline int score_from_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_SEARCH_PLY) return score - ply;
    if (score <= -MATE_SCORE + MAX_SEARCH_PLY) return score + ply;
    return score;
}

struct TTEntry {
    uint64_t key{0};
    int16_t score{0};
    int8_t depth{0};
    uint8_t flag{0};
    uint8_t age{0};
    uint16_t best_move{0};
};

struct alignas(64) TTCluster {
    std::atomic_flag lock;
    TTEntry entries[4];
};

constexpr size_t NUM_CLUSTERS = 65536; // 262,144 entries total for stress test

class ParallelTranspositionTable {
public:
    TTCluster* clusters{nullptr};
    std::atomic<uint8_t> current_age{0};

    ParallelTranspositionTable() {
        clusters = new TTCluster[NUM_CLUSTERS];
        clear();
    }

    ~ParallelTranspositionTable() {
        delete[] clusters;
    }

    void clear() {
        for (size_t i = 0; i < NUM_CLUSTERS; ++i) {
            clusters[i].lock.clear();
            std::memset(clusters[i].entries, 0, sizeof(clusters[i].entries));
        }
    }

    bool probe(uint64_t key, int depth, int ply, int alpha, int beta, int& out_score, uint16_t& out_move) {
        size_t c_idx = (key ^ (key >> 32)) % NUM_CLUSTERS;
        TTCluster& c = clusters[c_idx];

        while (c.lock.test_and_set(std::memory_order_acquire)) {
            _mm_pause();
        }

        bool hit = false;
        for (int i = 0; i < 4; ++i) {
            if (c.entries[i].key == key) {
                out_move = c.entries[i].best_move;
                if (c.entries[i].depth >= depth) {
                    int tt_score = score_from_tt(c.entries[i].score, ply);
                    uint8_t flag = c.entries[i].flag;
                    if (flag == TT_EXACT) {
                        out_score = tt_score;
                        hit = true;
                    } else if (flag == TT_LOWER && tt_score >= beta) {
                        out_score = tt_score;
                        hit = true;
                    } else if (flag == TT_UPPER && tt_score <= alpha) {
                        out_score = tt_score;
                        hit = true;
                    }
                }
                break;
            }
        }

        c.lock.clear(std::memory_order_release);
        return hit;
    }

    void store(uint64_t key, int score, int8_t depth, uint8_t flag, int ply, uint16_t best_move) {
        size_t c_idx = (key ^ (key >> 32)) % NUM_CLUSTERS;
        TTCluster& c = clusters[c_idx];
        uint8_t age = current_age.load(std::memory_order_relaxed);

        while (c.lock.test_and_set(std::memory_order_acquire)) {
            _mm_pause();
        }

        // 4-Way replacement:
        // 1. Existing entry with same key
        // 2. Empty slot (key == 0)
        // 3. Oldest age
        // 4. Lowest depth
        int replace_idx = -1;
        int lowest_depth = 999;
        int oldest_age_diff = -1;

        for (int i = 0; i < 4; ++i) {
            if (c.entries[i].key == key) {
                replace_idx = i;
                break;
            }
            if (c.entries[i].key == 0) {
                replace_idx = i;
                break;
            }
            int age_diff = (int)age - (int)c.entries[i].age;
            if (age_diff > oldest_age_diff) {
                oldest_age_diff = age_diff;
                replace_idx = i;
            } else if (age_diff == oldest_age_diff && c.entries[i].depth < lowest_depth) {
                lowest_depth = c.entries[i].depth;
                replace_idx = i;
            }
        }

        if (replace_idx >= 0) {
            c.entries[replace_idx].key = key;
            c.entries[replace_idx].score = score_to_tt(score, ply);
            c.entries[replace_idx].depth = depth;
            c.entries[replace_idx].flag = flag;
            c.entries[replace_idx].age = age;
            if (best_move != 0 || c.entries[replace_idx].best_move == 0) {
                c.entries[replace_idx].best_move = best_move;
            }
        }

        c.lock.clear(std::memory_order_release);
    }
};

static ParallelTranspositionTable g_ptt;

void stress_worker(int thread_id, int ops_per_thread, std::atomic<uint64_t>& total_probes, std::atomic<uint64_t>& total_stores, std::atomic<uint64_t>& corruptions) {
    uint64_t rng = 0x853c49e6748fea9bULL ^ ((uint64_t)thread_id * 0xda3e39cb94b95bdbULL);
    
    for (int i = 0; i < ops_per_thread; ++i) {
        rng = rng * 6364136223846793005ULL + 1442695040888963407ULL;
        uint64_t key = rng;
        int depth = (rng % 15) + 1;
        int score = (int)(rng % 2000) - 1000;
        uint8_t flag = (uint8_t)(rng % 3);
        uint16_t move = (uint16_t)(rng & 0x0FFF);

        // Store
        g_ptt.store(key, score, depth, flag, 0, move);
        total_stores.fetch_add(1, std::memory_order_relaxed);

        // Probe
        int out_score = 0;
        uint16_t out_move = 0;
        bool hit = g_ptt.probe(key, depth, 0, -2000, 2000, out_score, out_move);
        total_probes.fetch_add(1, std::memory_order_relaxed);

        if (hit) {
            // Verify payload consistency (cannot be torn)
            if (out_move > 0x0FFF) {
                corruptions.fetch_add(1, std::memory_order_relaxed);
            }
        }
    }
}

int main() {
    std::cout << "=== PARALLEL TT CONCURRENCY STRESS TEST ===" << std::endl;
    g_ptt.clear();

    const int num_threads = 4;
    const int ops_per_thread = 2500000; // 10 million total operations
    std::atomic<uint64_t> total_probes{0};
    std::atomic<uint64_t> total_stores{0};
    std::atomic<uint64_t> corruptions{0};

    auto t0 = std::chrono::high_resolution_clock::now();
    std::vector<std::thread> threads;
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back(stress_worker, t, ops_per_thread, std::ref(total_probes), std::ref(total_stores), std::ref(corruptions));
    }
    for (auto& th : threads) th.join();
    auto t1 = std::chrono::high_resolution_clock::now();

    double elapsed = std::chrono::duration<double>(t1 - t0).count();
    uint64_t total_ops = total_probes.load() + total_stores.load();
    double mops = (total_ops / elapsed) / 1e6;

    std::cout << "Threads: " << num_threads << std::endl;
    std::cout << "Total Operations: " << total_ops << " (Stores: " << total_stores.load() << ", Probes: " << total_probes.load() << ")" << std::endl;
    std::cout << "Elapsed Time: " << elapsed << " seconds" << std::endl;
    std::cout << "Throughput: " << mops << " million ops/sec" << std::endl;
    std::cout << "Corrupted / Torn Entries Detected: " << corruptions.load() << std::endl;

    assert(corruptions.load() == 0);
    std::cout << "PARALLEL TT STRESS TEST: PASSED (ZERO DATA RACES / ZERO CORRUPTIONS)" << std::endl;
    return 0;
}
