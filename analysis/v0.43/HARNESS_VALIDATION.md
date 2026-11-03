# Project Janus v0.43 — Replication Harness Validation (Phase E)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Harness Script:** `scripts/match_v043_replication.py`  
**Date:** 2026-11-03  
**Status:** VALIDATED & APPROVED FOR FULL EXECUTION  

---

## 1. Harness Architectural Features

The v0.43 replication harness (`scripts/match_v043_replication.py`) was engineered to satisfy all Phase E requirements:

1. **Frozen Manifest Loading:** Ingests `analysis/v0.43/openings_v043_100.json` (SHA-256 verified: `2f929719ab8377e1...`).
2. **True Matched Ablation:** Both Baseline K0 and Candidate RFP play every opening position twice (as White and as Black) against Stockfish 19 Elo 1320.
3. **Execution Counterbalancing:** To prevent sequential execution bias (e.g. system cache warm-up or CPU throttling):
   - Even pair indices: K0(W) → K0(B) → RFP(W) → RFP(B)
   - Odd pair indices:  RFP(W) → RFP(B) → K0(W) → K0(B)
4. **Comprehensive Telemetry:** Captures move-by-move clock allocations, overshoot ms, search depth, node counts, and NPS.
5. **Live Persistence:** Appends every completed game dynamically to `match_results.pgn`, `match_moves.csv`, `attempt_log.json`, and `match_results.json`.
6. **Fault Tolerance:** Automated retry logic (up to 3 attempts per game slot) logging both failed attempts and valid replacement games.

---

## 2. Smoke Test Execution Results

A 1-pair smoke test (4 games total) was conducted in `analysis/v0.43/smoke_test/`:
- **Opening Tested:** `e4_e5_open_game` (`rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2`)

### Smoke Test Match Table

| Game | Pair | Engine Arm | Colour | Opponent | Result | Janus Pts | Plies | Duration | Mean Depth |
|:---:|:---:|:---|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | 1 | K0 Baseline | White | Stockfish 19 | 0-1 (Loss) | 0.0 | 90 | 14.0s | 1.9 |
| 2 | 1 | K0 Baseline | Black | Stockfish 19 | 0-1 (Win) | 1.0 | 50 | 9.4s | 1.8 |
| 3 | 1 | Candidate RFP | White | Stockfish 19 | 1-0 (Win) | 1.0 | 163 | 21.5s | 2.1 |
| 4 | 1 | Candidate RFP | Black | Stockfish 19 | 0-1 (Win) | 1.0 | 36 | 7.4s | 2.2 |

### Score Summary on Smoke Test Pair 1
- **K0 Baseline Score:** 1.0 / 2.0 (50.0%)
- **Candidate RFP Score:** 2.0 / 2.0 (100.0%)
- **Paired Delta ($\Delta_1$):** **+1.0 points**

---

## 3. Telemetry and Compliance Verification

- **PGN Replay & Legality:** 4 games, 339 plies parsed via `chess.pgn.read_game`. **0 illegal moves**.
- **Clock Non-Negativity:** 339 moves audited in `match_moves.csv`. **0 negative clock readings**.
- **Engine Process Lifecycle:** Clean startup and shutdown across 4 supervised subprocess sessions.
- **Retry Mechanism:** Clean pass on first attempts; attempt log properly serialized.

**Verdict:** The replication harness is robust, accurate, and qualified for the full replication experiment.
