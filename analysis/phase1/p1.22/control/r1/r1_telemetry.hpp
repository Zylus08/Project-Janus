#pragma once
/**
 * r1_telemetry.hpp
 * Janus Classical R1 — High-Resolution Search Telemetry & Performance Counters.
 */

#include <cstdint>
#include <string>
#include <sstream>

namespace r1 {

struct SearchTelemetry {
    uint64_t main_nodes = 0;
    uint64_t qsearch_nodes = 0;
    uint64_t tt_probes = 0;
    uint64_t tt_hits = 0;
    uint64_t tt_cutoffs = 0;
    uint64_t nmp_probes = 0;
    uint64_t nmp_cutoffs = 0;
    uint64_t rfp_probes = 0;
    uint64_t rfp_cutoffs = 0;
    uint64_t lmr_probes = 0;
    uint64_t lmr_researches = 0;
    uint64_t lmp_cutoffs = 0;
    uint64_t aspiration_researches = 0;

    void reset() {
        main_nodes = 0;
        qsearch_nodes = 0;
        tt_probes = 0;
        tt_hits = 0;
        tt_cutoffs = 0;
        nmp_probes = 0;
        nmp_cutoffs = 0;
        rfp_probes = 0;
        rfp_cutoffs = 0;
        lmr_probes = 0;
        lmr_researches = 0;
        lmp_cutoffs = 0;
        aspiration_researches = 0;
    }

    uint64_t total_nodes() const {
        return main_nodes + qsearch_nodes;
    }

    double qsearch_ratio() const {
        uint64_t tot = total_nodes();
        return tot > 0 ? (double)qsearch_nodes / tot : 0.0;
    }

    double tt_hit_rate() const {
        return tt_probes > 0 ? (double)tt_hits / tt_probes : 0.0;
    }
};

} // namespace r1
