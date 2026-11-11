#include <iostream>
#include <cstdint>
#include <atomic>
#include <cstddef>

#pragma pack(push, 1)
// Check packing of TTEntry if needed
#pragma pack(pop)

struct TTEntry {
    uint64_t key;       // 8 bytes
    uint16_t best_move; // 2 bytes
    int16_t  score;     // 2 bytes
    int8_t   depth;     // 1 byte
    uint8_t  flags;     // 1 byte
    uint8_t  age;       // 1 byte
    uint8_t  pad;       // 1 byte
};                      // Total: 16 bytes

struct alignas(64) TTCluster {
    std::atomic_flag lock;  // 4 bytes on MSVC
    uint8_t pad[4];         // 4 bytes
    TTEntry entries[3];     // 3 * 16 = 48 bytes
    uint8_t tail_pad[8];    // 8 bytes
};                          // Total: 64 bytes

int main() {
    std::cout << "=== TT MEMORY LAYOUT AUDIT ===" << std::endl;
    std::cout << "sizeof(TTEntry): " << sizeof(TTEntry) << " (expected 16)" << std::endl;
    std::cout << "sizeof(std::atomic_flag): " << sizeof(std::atomic_flag) << std::endl;
    std::cout << "sizeof(TTCluster): " << sizeof(TTCluster) << " (expected 64)" << std::endl;
    std::cout << "alignof(TTCluster): " << alignof(TTCluster) << " (expected 64)" << std::endl;
    std::cout << "offsetof(lock): " << offsetof(TTCluster, lock) << std::endl;
    std::cout << "offsetof(pad): " << offsetof(TTCluster, pad) << std::endl;
    std::cout << "offsetof(entries): " << offsetof(TTCluster, entries) << std::endl;
    std::cout << "offsetof(tail_pad): " << offsetof(TTCluster, tail_pad) << std::endl;
    
    constexpr size_t NUM_CLUSTERS = 524288;
    size_t total_bytes = NUM_CLUSTERS * sizeof(TTCluster);
    size_t total_entries = NUM_CLUSTERS * 3;
    std::cout << "Total allocation: " << total_bytes << " bytes (" << (total_bytes / (1024 * 1024)) << " MB)" << std::endl;
    std::cout << "Total entries: " << total_entries << std::endl;

    bool passed = (sizeof(TTEntry) == 16) && 
                  (sizeof(TTCluster) == 64) && 
                  (alignof(TTCluster) == 64) &&
                  (offsetof(TTCluster, lock) == 0) &&
                  (offsetof(TTCluster, entries) == 8);

    std::cout << "Audit Verdict: " << (passed ? "PASSED" : "FAILED") << std::endl;
    return passed ? 0 : 1;
}

