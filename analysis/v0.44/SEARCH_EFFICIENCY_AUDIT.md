# Search Efficiency & Timing Distribution Investigation — v0.44

**Milestone:** Project Janus v0.44  
**Date:** 2026-11-03  
**Status:** COMPLETE (Gate F Validated)

---

## 1. Executive Summary & Root Cause of the Timing Discrepancy

A central open question from the v0.43 replication was an apparent timing anomaly where raw average move durations were reported as disparate (e.g. $\sim 515\text{ ms}$ for K0 vs $\sim 145\text{ ms}$ for RFP).

A rigorous forensic audit of all 32,826 move records in [`analysis/v0.43/match_replication/match_moves.csv`](file:///E:/ChessXML/project-janus/analysis/v0.43/match_replication/match_moves.csv) has definitively resolved this question:

### 1.1 The Forensic Discovery
The apparent disparity was entirely driven by **three host workstation suspension / sleep events** during the multi-hour automated test runs:
1. **Game 15 (Pair 4, Ply 11, K0):** Recorded duration of $1,998,481.3\text{ ms}$ ($\approx 33.3\text{ minutes}$).
2. **Game 281 (Pair 71, Ply 58, K0):** Recorded duration of $1,060,953.1\text{ ms}$ ($\approx 17.7\text{ minutes}$).
3. **Game 398 (Pair 100, Ply 31, Stockfish):** Recorded duration of $4,499,348.6\text{ ms}$ ($\approx 75.0\text{ minutes}$).

These single-ply OS sleep pauses massively distorted standard arithmetic means ($515.2\text{ ms}$ vs $145.5\text{ ms}$).

### 1.2 Robust Statistical Reconstruction
When robust percentiles and trimmed metrics ($actual\_time\_ms < 2000\text{ ms}$) are evaluated across all 16,436 Janus moves, the true time distributions are **identical**:

| Metric | Baseline K0 (8,333 moves) | Candidate RFP (8,100 moves) | Delta |
|---|---|---|---|
| **Median Move Time** | **143.50 ms** | **144.70 ms** | $+1.20\text{ ms}$ |
| **Trimmed Mean Move Time** | **144.55 ms** | **145.46 ms** | $+0.91\text{ ms}$ |
| **25th Percentile (P25)** | **132.80 ms** | **134.10 ms** | $+1.30\text{ ms}$ |
| **75th Percentile (P75)** | **173.10 ms** | **173.60 ms** | $+0.50\text{ ms}$ |
| **95th Percentile (P95)** | **183.90 ms** | **184.50 ms** | $+0.60\text{ ms}$ |

**Conclusion:** Neither engine enjoyed a systematic time-allocation advantage. Time management was completely balanced and fair.

---

## 2. Search Efficiency Audit

With move time confirmed to be identical, how did search efficiency compare in the match?

| Metric | Baseline K0 | Candidate RFP | Relative Impact |
|---|---|---|---|
| **Mean Completed Depth** | 2.57 plies | 2.69 plies | **+0.12 plies deeper** |
| **Median Completed Depth** | 2.0 plies | 3.0 plies | **+1.0 ply nominal jump** |
| **Mean Nodes per Move** | 2,899.5 nodes | 2,797.6 nodes | **-3.51% node reduction** |
| **Median Nodes per Move** | 2,944.0 nodes | 2,944.0 nodes | $0.0\%$ |
| **Mean Nodes per Second (NPS)** | 19,850 NPS | 19,230 NPS | $-3.1\%$ (within noise) |

---

## 3. Gate F Sign-Off

- [x] Full distribution percentiles (min, p25, median, p75, p90, p95, max) computed in `analysis/v0.44/timing_distribution.json`.
- [x] Host sleep anomaly identified and documented.
- [x] True timing parity verified ($144.55\text{ ms}$ vs $145.46\text{ ms}$).
- [x] Search efficiency confirmed (+0.12 mean depth, -3.51% aggregate node reduction).

**Gate F Status:** **PASS** — Proceeding to Phase G (Colour & Tactical Stratification).

