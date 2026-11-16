#pragma once
/**
 * r1_tt.hpp
 * Janus Classical R1 — High-Performance Transposition Table.
 * Implements 64-byte cacheline-aligned cluster storage with formal TT0/TT1/TT2 contracts.
 */

#include "r1_types.hpp"
#include <cstring>
#include <vector>

namespace r1 {

#pragma pack(push, 1)
struct TTEntry {
    uint64_t key = 0;
    int16_t score = 0;
    int8_t depth = 0;
    uint8_t flag = TT_NONE;
    uint8_t age = 0;
    uint16_t best_move = 0;
    uint8_t padding[1] = {0}; // 8 + 2 + 1 + 1 + 1 + 2 + 1 = 16 bytes
};
#pragma pack(pop)

static_assert(sizeof(TTEntry) == 16, "TTEntry must be exactly 16 bytes for 64-byte cache-line alignment");

struct alignas(64) TTCluster {
    TTEntry entries[4]; // 4 * 16 bytes = 64 bytes (exact cache-line fit)
};

static_assert(sizeof(TTCluster) == 64, "TTCluster must be exactly 64 bytes");

class TranspositionTable {
public:
    TranspositionTable(size_t mb_size = 32) {
        resize(mb_size);
    }

    void resize(size_t mb_size) {
        size_t total_bytes = mb_size * 1024 * 1024;
        num_clusters_ = total_bytes / sizeof(TTCluster);
        if (num_clusters_ == 0) num_clusters_ = 1;
        clusters_.assign(num_clusters_, TTCluster{});
        generation_ = 0;
    }

    void clear() {
        std::fill(clusters_.begin(), clusters_.end(), TTCluster{});
        generation_ = 0;
    }

    void new_search() {
        generation_++;
    }

    // TT0 Contract: authoritative probe with bound validation
    bool probe(uint64_t key, int depth, int ply, int alpha, int beta,
               int& out_score, uint16_t& out_move, bool allow_cutoff,
               TTEntry* out_entry = nullptr) {
        if (num_clusters_ == 0) return false;
        size_t c_idx = (key ^ (key >> 32)) % num_clusters_;
        TTCluster& cluster = clusters_[c_idx];

        for (int i = 0; i < 4; ++i) {
            if (cluster.entries[i].key == key) {
                const TTEntry& e = cluster.entries[i];
                if (out_entry) *out_entry = e;
                out_move = e.best_move;

                if (allow_cutoff && e.depth >= depth && ply > 0) {
                    int tt_score = score_from_tt(e.score, ply);
                    if (e.flag == TT_EXACT) {
                        out_score = tt_score;
                        return true;
                    }
                    if (e.flag == TT_LOWER && tt_score >= beta) {
                        out_score = tt_score;
                        return true;
                    }
                    if (e.flag == TT_UPPER && tt_score <= alpha) {
                        out_score = tt_score;
                        return true;
                    }
                }
                return false; // Found entry, but bound doesn't cut off
            }
        }
        return false; // Not in TT
    }

    // TT2 Contract: authoritative store with replacement policy
    void store(uint64_t key, int score, int8_t depth, uint8_t flag, int ply, uint16_t best_move) {
        if (num_clusters_ == 0) return;
        size_t c_idx = (key ^ (key >> 32)) % num_clusters_;
        TTCluster& cluster = clusters_[c_idx];

        int replace_idx = -1;
        // 1. If key already exists in cluster, update that entry
        for (int i = 0; i < 4; ++i) {
            if (cluster.entries[i].key == key) {
                replace_idx = i;
                break;
            }
        }

        // 2. Otherwise find replacement candidate:
        if (replace_idx == -1) {
            // Check for empty slot
            for (int i = 0; i < 4; ++i) {
                if (cluster.entries[i].key == 0) {
                    replace_idx = i;
                    break;
                }
            }
        }

        if (replace_idx == -1) {
            // Replacement scheme:
            // Slot 0: Depth-preferred (deepest search)
            // Slot 1: Generation age-preferred
            // Slot 2: Shallowest entry
            // Slot 3: Always-replace slot
            int shallowest_idx = 0;
            int oldest_idx = 0;
            int min_depth = 999;
            int max_age_diff = -1;

            for (int i = 0; i < 4; ++i) {
                if (cluster.entries[i].depth < min_depth) {
                    min_depth = cluster.entries[i].depth;
                    shallowest_idx = i;
                }
                int age_diff = (int)generation_ - (int)cluster.entries[i].age;
                if (age_diff > max_age_diff) {
                    max_age_diff = age_diff;
                    oldest_idx = i;
                }
            }

            if (max_age_diff > 2) {
                replace_idx = oldest_idx;
            } else if (depth >= cluster.entries[0].depth) {
                replace_idx = 0; // Replace depth slot if new search is deeper
            } else {
                replace_idx = shallowest_idx;
            }
        }

        TTEntry& target = cluster.entries[replace_idx];
        // If updating existing entry with same key, preserve best move if new move is 0
        uint16_t move_to_store = best_move;
        if (move_to_store == 0 && target.key == key) {
            move_to_store = target.best_move;
        }

        target.key = key;
        target.score = (int16_t)score_to_tt(score, ply);
        target.depth = depth;
        target.flag = flag;
        target.age = generation_;
        target.best_move = move_to_store;
    }

    size_t capacity() const { return num_clusters_ * 4; }
    uint8_t generation() const { return generation_; }

private:
    std::vector<TTCluster> clusters_;
    size_t num_clusters_ = 0;
    uint8_t generation_ = 0;
};

} // namespace r1
