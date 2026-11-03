# Project Janus v0.43 — RFP Replication Execution Report (Phase F)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Harness:** `scripts/match_v043_replication.py`  
**Execution Timestamp:** 2026-11-03  
**Status:** COMPLETE — 100 COMPLETE PAIRS (400 VALID GAMES)  

---

## 1. Execution Summary

Under the preregistered protocol frozen at commit `e44ca4e`, Project Janus conducted an independent, counterbalanced, colour-reversed replication match comparing **Baseline K0** against **Candidate RFP** (`rfp_max_depth=2`, `rfp_margin_per_depth=120`) across 100 master opening positions from `analysis/v0.43/openings_v043_100.json`.

### Operational Metrics
- **Opening Pairs Attempted:** 100
- **Opening Pairs Completed:** 100 (100.0%)
- **Total Games Played:** 400 (200 games for K0, 200 games for RFP)
- **Infrastructure Failures:** 0 (0 crashes, 0 protocol timeouts, 0 invalid moves)
- **Total Plies Played:** 32,826 plies
- **Move Telemetry Rows:** 32,826 recorded in `match_moves.csv`
- **Negative Clocks:** 0
- **Illegal Moves:** 0

---

## 2. Order Counterbalancing Execution

To eliminate ordering artifacts, engine execution alternated across pairs:
- **Even Pairs (Pairs 2, 4, ..., 100):**
  1. RFP as White vs Stockfish 19
  2. RFP as Black vs Stockfish 19
  3. K0 as White vs Stockfish 19
  4. K0 as Black vs Stockfish 19
- **Odd Pairs (Pairs 1, 3, ..., 99):**
  1. K0 as White vs Stockfish 19
  2. K0 as Black vs Stockfish 19
  3. RFP as White vs Stockfish 19
  4. RFP as Black vs Stockfish 19

Both engines were subjected to strictly identical hardware, CPU temperatures, thermal profiles, and virtual environment allocations.

---

## 3. High-Level Performance Metrics

| Engine Arm | Total Games | Wins (W) | Draws (D) | Losses (L) | Total Points | Score % | White Score | Black Score |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline K0** | 200 | 116 | 14 | 70 | **123.0 / 200** | **61.50%** | 64.5 / 100 (64.5%) | 58.5 / 100 (58.5%) |
| **Candidate RFP** | 200 | 113 | 13 | 74 | **119.5 / 200** | **59.75%** | 64.5 / 100 (64.5%) | 55.0 / 100 (55.0%) |
| **Delta (RFP - K0)** | — | -3 | -1 | +4 | **-3.5 pts** | **-1.75%** | 0.0 pts (0.0%) | -3.5 pts (-3.5%) |

---

## 4. Integrity and Compliance Checklist

- [x] All 400 games parsed and verified via `chess.pgn`.
- [x] Every move in `match_results.pgn` confirmed strictly legal.
- [x] Clocks non-negative throughout in `match_moves.csv`.
- [x] All 400 attempts logged with zero unrecorded exclusions in `attempt_log.json`.
- [x] Master opening hash matched frozen preregistration digest (`2f929719ab8377e1...`).

