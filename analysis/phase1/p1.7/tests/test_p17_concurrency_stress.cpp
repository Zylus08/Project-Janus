#include <iostream>
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cassert>
#include <cstring>
#include <immintrin.h>

struct TTEntry {
    uint64_t key;
    int16_t score;
    int8_t depth;
    uint8_t flag;
    uint8_t age;
    uint16_t best_move;
};

// 64-byte packed cluster: exactly 1 cache line
struct alignas(64) TTCluster {
    std::atomic_flag lock;
    uint8_t pad[4];
    TTEntry entries[3]; // 3 * 16 = 48 bytes. Total = 4 + 4 + 48 = 56 <= 64 bytes
    uint8_t tail_pad[8];
};

constexpr size_t NUM_TT_CLUSTERS = 262144; // 16.7 MB for stress testing

class PackedTranspositionTable {
public:
    TTCluster* clusters{nullptr};
    std::atomic<uint8_t> current_age{0};

    PackedTranspositionTable() {
        clusters = new TTCluster[NUM_TT_CLUSTERS];
        clear();
    }
    ~PackedTranspositionTable() {
        delete[] clusters;
    }
    void clear() {
        for (size_t i = 0; i < NUM_TT_CLUSTERS; ++i) {
            clusters[i].lock.clear();
            std::memset(clusters[i].entries, 0, sizeof(clusters[i].entries));
        }
    }
    bool probe(uint64_t key, int depth, int& out_score, uint16_t& out_move) {
        size_t c_idx = (key ^ (key >> 32)) % NUM_TT_CLUSTERS;
        TTCluster& c = clusters[c_idx];
        while (c.lock.test_and_set(std::memory_order_acquire)) {
            _mm_pause();
        }
        bool hit = false;
        out_move = 0;
        for (int i = 0; i < 3; ++i) {
            if (c.entries[i].key == key) {
                out_move = c.entries[i].best_move;
                if (c.entries[i].depth >= depth) {
                    out_score = c.entries[i].score;
                    hit = true;
                }
                break;
            }
        }
        c.lock.clear(std::memory_order_release);
        return hit;
    }
    void store(uint64_t key, int score, int8_t depth, uint8_t flag, uint16_t best_move) {
        size_t c_idx = (key ^ (key >> 32)) % NUM_TT_CLUSTERS;
        TTCluster& c = clusters[c_idx];
        uint8_t age = current_age.load(std::memory_order_relaxed);

        while (c.lock.test_and_set(std::memory_order_acquire)) {
            _mm_pause();
        }

        int replace_idx = -1;
        int oldest_score = -999999;

        for (int i = 0; i < 3; ++i) {
            if (c.entries[i].key == key) {
                if (depth < c.entries[i].depth && age == c.entries[i].age && flag != 0 /* not exact */) {
                    if (c.entries[i].best_move == 0 && best_move != 0) c.entries[i].best_move = best_move;
                    c.lock.clear(std::memory_order_release);
                    return;
                }
                replace_idx = i;
                break;
            }
            if (c.entries[i].key == 0) {
                replace_idx = i;
                break;
            }
            int age_diff = (int)age - (int)c.entries[i].age;
            int s = (age_diff * 8) - (int)c.entries[i].depth;
            if (s > oldest_score) {
                oldest_score = s;
                replace_idx = i;
            }
        }

        if (replace_idx >= 0) {
            c.entries[replace_idx].key = key;
            c.entries[replace_idx].score = (int16_t)score;
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

constexpr int NUM_THREADS = 4;
constexpr uint64_t OPS_PER_THREAD = 5000000; // 20M operations total

int main() {
    std::cout << "[STRESS] Starting Packed Transposition Table Concurrency Stress Test..." << std::endl;
    std::cout << "[STRESS] sizeof(TTCluster) = " << sizeof(TTCluster) << " bytes (Cache-line aligned: " << (sizeof(TTCluster) == 64 ? "YES" : "NO") << ")" << std::endl;

    PackedTranspositionTable tt;
    std::atomic<uint64_t> corrupted_reads{0};
    std::atomic<uint64_t> successful_probes{0};
    std::atomic<uint64_t> successful_stores{0};

    auto t_start = std::chrono::steady_clock::now();
    std::vector<std::thread> workers;

    for (int t = 0; t < NUM_THREADS; ++t) {
        workers.emplace_back([&tt, t, &corrupted_reads, &successful_probes, &successful_stores]() {
            uint64_t seed = 0x9e3779b97f4a7c15ULL * (t + 1);
            auto rng = [&seed]() {
                seed ^= (seed << 13);
                seed ^= (seed >> 7);
                seed ^= (seed << 17);
                return seed;
            };

            for (uint64_t i = 0; i < OPS_PER_THREAD; ++i) {
                uint64_t k = (rng() % 100000) + 1; // High key overlap to force cluster collisions
                int d = (rng() % 16) + 1;
                int score = (int)(k & 0x7FFF); // Store predictable score tied to key

                if (i % 2 == 0) {
                    tt.store(k, score, (int8_t)d, 1, (uint16_t)(k & 0xFFFF));
                    successful_stores.fetch_add(1, std::memory_order_relaxed);
                } else {
                    int out_s = 0;
                    uint16_t out_m = 0;
                    if (tt.probe(k, d, out_s, out_m)) {
                        // Check data integrity: score must match key's predictable pattern!
                        if (out_s != (int)(k & 0x7FFF)) {
                            corrupted_reads.fetch_add(1, std::memory_order_relaxed);
                        }
                    }
                    successful_probes.fetch_add(1, std::memory_order_relaxed);
                }

                if ((i & 524287) == 0 && t == 0) {
                    tt.current_age.fetch_add(1, std::memory_order_relaxed);
                }
            }
        });
    }

    for (auto& w : workers) {
        if (w.joinable()) w.join();
    }

    auto t_end = std::chrono::steady_clock::now();
    double elapsed = std::chrono::duration<double>(t_end - t_start).count();
    uint64_t total_ops = NUM_THREADS * OPS_PER_THREAD;

    std::cout << "[STRESS] Completed " << total_ops << " operations across " << NUM_THREADS << " threads in " << elapsed << "s" << std::endl;
    std::cout << "[STRESS] Throughput: " << (double)total_ops / elapsed / 1000000.0 << " million ops/sec" << std::endl;
    std::cout << "[STRESS] Corrupted reads: " << corrupted_reads.load() << std::endl;
    std::cout << "[STRESS] Result: " << (corrupted_reads.load() == 0 ? "PASSED (100% DATA INTEGRITY)" : "FAILED (DATA RACES DETECTED)") << std::endl;

    return (corrupted_reads.load() == 0) ? 0 : 1;
}
