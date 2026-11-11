#include <iostream>
#include <iomanip>
#include <cstdint>
#include <vector>
#include <chrono>
#include <windows.h>

struct PawnHashEntry {
    uint64_t key;
    int16_t mg[2];
    int16_t eg[2];
    uint64_t passed_pawns[2];
};

void query_cpu_cache() {
    std::cout << "=== CPU HARDWARE CACHE HIERARCHY AUDIT ===" << std::endl;
    DWORD buffer_size = 0;
    GetLogicalProcessorInformation(nullptr, &buffer_size);
    if (buffer_size == 0) {
        std::cout << "Failed to get buffer size for processor info" << std::endl;
        return;
    }

    std::vector<SYSTEM_LOGICAL_PROCESSOR_INFORMATION> buffer(buffer_size / sizeof(SYSTEM_LOGICAL_PROCESSOR_INFORMATION));
    if (!GetLogicalProcessorInformation(buffer.data(), &buffer_size)) {
        std::cout << "Failed to query GetLogicalProcessorInformation" << std::endl;
        return;
    }

    DWORD l1_d_size = 0, l1_i_size = 0, l2_size = 0, l3_size = 0;
    int l1_count = 0, l2_count = 0, l3_count = 0;

    for (const auto& info : buffer) {
        if (info.Relationship == RelationCache) {
            const CACHE_DESCRIPTOR& cache = info.Cache;
            if (cache.Level == 1) {
                if (cache.Type == CacheData) { l1_d_size = cache.Size; l1_count++; }
                else if (cache.Type == CacheInstruction) { l1_i_size = cache.Size; }
            } else if (cache.Level == 2) {
                l2_size = cache.Size;
                l2_count++;
            } else if (cache.Level == 3) {
                l3_size = cache.Size;
                l3_count++;
            }
        }
    }

    std::cout << "  L1 Data Cache per Core:        " << (l1_d_size / 1024) << " KB (Line size: 64B)" << std::endl;
    std::cout << "  L2 Unified Cache per Core:     " << (l2_size / 1024) << " KB (" << (l2_size / (1024 * 1024.0)) << " MB)" << std::endl;
    std::cout << "  L3 Shared Cache:               " << (l3_size / (1024 * 1024)) << " MB" << std::endl;
    std::cout << "  Active L2 Slices Count:        " << l2_count << " slices" << std::endl;
}

int main() {
    query_cpu_cache();

    std::cout << "\n=== PAWN HASH MEMORY STRUCTURE AUDIT ===" << std::endl;
    std::cout << "  sizeof(PawnHashEntry):         " << sizeof(PawnHashEntry) << " bytes" << std::endl;
    std::cout << "  alignof(PawnHashEntry):        " << alignof(PawnHashEntry) << " bytes" << std::endl;
    std::cout << "  offsetof(key):                 " << offsetof(PawnHashEntry, key) << " bytes" << std::endl;
    std::cout << "  offsetof(mg):                  " << offsetof(PawnHashEntry, mg) << " bytes" << std::endl;
    std::cout << "  offsetof(eg):                  " << offsetof(PawnHashEntry, eg) << " bytes" << std::endl;
    std::cout << "  offsetof(passed_pawns):        " << offsetof(PawnHashEntry, passed_pawns) << " bytes" << std::endl;

    constexpr size_t SIZE_16K = 16384;
    constexpr size_t BYTES_16K = SIZE_16K * sizeof(PawnHashEntry);
    constexpr size_t SIZE_64K = 65536;
    constexpr size_t BYTES_64K = SIZE_64K * sizeof(PawnHashEntry);

    std::cout << "\n  16K Entries Total Footprint:   " << (BYTES_16K / 1024) << " KB (" << (BYTES_16K / (1024.0 * 1024.0)) << " MB)" << std::endl;
    std::cout << "  64K Entries Total Footprint:   " << (BYTES_64K / 1024) << " KB (" << (BYTES_64K / (1024.0 * 1024.0)) << " MB)" << std::endl;

    // Latency micro-benchmark: 10,000,000 random probes
    std::vector<PawnHashEntry> table_16k(SIZE_16K);
    std::vector<PawnHashEntry> table_64k(SIZE_64K);

    constexpr int ITERATIONS = 10000000;
    uint64_t dummy = 0;

    // Benchmark 16K
    auto t0 = std::chrono::high_resolution_clock::now();
    uint64_t key = 0x987654321ULL;
    for (int i = 0; i < ITERATIONS; i++) {
        key ^= (key << 13); key ^= (key >> 7); key ^= (key << 17);
        size_t idx = key & (SIZE_16K - 1);
        dummy += table_16k[idx].key + table_16k[idx].mg[0];
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double dur_16k = std::chrono::duration<double, std::milli>(t1 - t0).count();

    // Benchmark 64K
    t0 = std::chrono::high_resolution_clock::now();
    key = 0x987654321ULL;
    for (int i = 0; i < ITERATIONS; i++) {
        key ^= (key << 13); key ^= (key >> 7); key ^= (key << 17);
        size_t idx = key & (SIZE_64K - 1);
        dummy += table_64k[idx].key + table_64k[idx].mg[0];
    }
    t1 = std::chrono::high_resolution_clock::now();
    double dur_64k = std::chrono::duration<double, std::milli>(t1 - t0).count();

    std::cout << "\n=== RANDOM ACCESS PROBING BENCHMARK (10M Probes) ===" << std::endl;
    std::cout << "  16K Table (512 KB):            " << dur_16k << " ms (" << (dur_16k / ITERATIONS * 1e6) << " ns/probe) [Dummy: " << dummy << "]" << std::endl;
    std::cout << "  64K Table (2048 KB):           " << dur_64k << " ms (" << (dur_64k / ITERATIONS * 1e6) << " ns/probe)" << std::endl;
    std::cout << "  Latency Ratio (64K / 16K):     " << (dur_64k / dur_16k) << "x" << std::endl;

    return 0;
}

