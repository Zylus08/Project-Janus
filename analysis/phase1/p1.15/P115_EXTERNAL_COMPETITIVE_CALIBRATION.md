# PHASE 13: EXTERNAL COMPETITIVE CALIBRATION REPORT

**Project:** Project Janus — Phase 1, Milestone P1.15  
**Candidate Evaluated:** Janus Classical X20-S (Single-Thread Candidate, `AF126A...`)  
**External Opponents:** Stockfish 4 (Official), Stockfish 11 (Official), Stockfish 19 (`edb0d9d`, Default NNUE)  
**Date:** November 14, 2026  
**Auditor:** Principal Computer Chess Engine Architect & Independent Statistical Auditor  
**Deliverable:** `analysis/phase1/p1.15/P115_EXTERNAL_COMPETITIVE_CALIBRATION.md`  
**Raw Telemetry:** `analysis/phase1/p1.15/raw/p115_tournaments_raw.json`  
**PGN Repository:** `analysis/phase1/p1.15/pgn/`  

---

## 1. Executive Summary & Calibration Standard

Milestone P1.15 maintains strict external competitive calibration against historical and modern chess engine anchors to monitor the true absolute playing-strength gap:
1. **Historical Step 1 Anchor:** Stockfish 4 (official release, full classical strength, no NNUE).
2. **Peak Classical Milestone:** Stockfish 11 (official release, ultimate classical alpha-beta ceiling prior to NNUE).
3. **Modern Super-Grandmaster Benchmark:** Stockfish 19 (commit `edb0d9d`, unrestricted, default NNUE evaluation enabled).

All matches were conducted under matched, controlled hardware and time conditions:
- **Time Control:** Fischer 1.5s base + 50ms increment per move.
- **Hardware:** 1 thread, 32 MB Hash for Stockfish, 16 MB Hash for Janus X20-S.
- **Openings:** 20 unbiased colour-reversed pairs (40 games per match) from `independent_openings_v056.json`.
- **Governing Standard:** JCTS v2 Classical Testing Protocol.

---

## 2. Match 5: Historical Calibration vs Stockfish 4

**Time Control:** 1.5s + 50ms.  
**Games:** 40 games (20 colour-reversed opening pairs).  
**PGN:** `analysis/phase1/p1.15/pgn/x20_1t_vs_sf4_1t.pgn`  

### Empirical Results:
- **Wins (X20-S):** 0
- **Draws:** 3 (Games 1, 25, 33)
- **Losses (SF4):** 37
- **Total Points:** 1.5 / 40 (**3.75%**)
- **Elo Difference:** **-563.7 Elo**
- **Wilson 95% Confidence Interval:** $[0.97\%, 11.19\%]$
- **Paired 95% Confidence Interval:** **$[0.00\%, 7.76\%]$**
- **Pentanomial Distribution:**
  - `WW` (+2.0 pts): 0 pairs
  - `WD` (+1.5 pts): 0 pairs
  - `DD_WL` (+1.0 pt): 0 pairs
  - `LD` (+0.5 pts): 3 pairs
  - `LL` (0.0 pts): 17 pairs
- **Technical Incidents:** 0 time forfeits, 0 illegal moves.

### Historical Context:
In P1.13, Janus achieved its first verified win against Stockfish 4. In P1.14 and P1.15, Candidate X20-S achieved 3 draws against Stockfish 4 ($1.5 / 40$). While the engine defends tenaciously in quiet endgames, Stockfish 4's superior evaluation weights and King Safety tables consistently convert middlegame imbalances.

---

## 3. Match 6: Peak Classical Calibration vs Stockfish 11

**Time Control:** 1.5s + 50ms.  
**Games:** 40 games (20 colour-reversed opening pairs).  
**PGN:** `analysis/phase1/p1.15/pgn/x20_1t_vs_sf11_1t.pgn`  

### Empirical Results:
- **Wins (X20-S):** 0
- **Draws:** 1
- **Losses (SF11):** 39
- **Total Points:** 0.5 / 40 (**1.25%**)
- **Elo Difference:** **-759.1 Elo**
- **Wilson 95% Confidence Interval:** $[0.06\%, 7.42\%]$
- **Paired 95% Confidence Interval:** **$[0.00\%, 3.70\%]$**
- **Pentanomial Distribution:**
  - `WW`: 0 pairs
  - `WD`: 0 pairs
  - `DD_WL`: 0 pairs
  - `LD`: 1 pair
  - `LL`: 19 pairs
- **Technical Incidents:** 0 time forfeits, 0 illegal moves.

### Forensic Finding:
Stockfish 11 represents the absolute peak of handcrafted classical chess evaluation (Texel-tuned piece-square tables, sophisticated pawn structures, king attack evaluation, and deep singular extensions). Candidate X20-S managed 1 draw (0.5/40), illustrating the substantial evaluation knowledge deficit separating Project Janus from mature classical architectures.

---

## 4. Match 7: Modern Benchmark vs Stockfish 19 (Unrestricted NNUE)

**Time Control:** 1.5s + 50ms.  
**Games:** 40 games (20 colour-reversed opening pairs).  
**PGN:** `analysis/phase1/p1.15/pgn/x20_1t_vs_sf19_1t.pgn`  

### Empirical Results:
- **Wins (X20-S):** 0
- **Draws:** 1 (Game 36: threefold repetition in 52 plies)
- **Losses (SF19):** 39
- **Total Points:** 0.5 / 40 (**1.25%**)
- **Elo Difference:** **-759.1 Elo**
- **Wilson 95% Confidence Interval:** $[0.06\%, 7.42\%]$
- **Paired 95% Confidence Interval:** **$[0.00\%, 3.70\%]$**
- **Pentanomial Distribution:**
  - `WW`: 0 pairs
  - `WD`: 0 pairs
  - `DD_WL`: 0 pairs
  - `LD`: 1 pair
  - `LL`: 19 pairs
- **Technical Incidents:** 0 time forfeits, 0 illegal moves.

### Verified Draw Preservation:
In Game 36, playing with the black pieces in a sharp tactical Sicilian defense, Candidate X20-S navigated all tactical threats and held an exact three-fold repetition draw against Stockfish 19:
> `[x20_1t_vs_sf19_1t] Game 36/40: Stockfish 19 (1T) vs Janus Classical X20-S (1T) -> 1/2-1/2 (threefold_repetition, 52 plies)`

In accordance with Phase 13 scientific integrity guidelines:
- We do **NOT** claim that drawing against Stockfish 19 represents an Elo improvement.
- In a 40-game sample, scoring 0.5 points yields an estimated score of $1.25\%$ with an exact Clopper-Pearson / paired interval of $[0.0\%, 3.7\%]$.
- This confirms that against neural evaluation networks with modern NNUE inference, classical handcrafted evaluation remains at a severe structural disadvantage (approximately $\sim -750$ Elo).

---

## 5. Comprehensive External Calibration Summary Table

| Match | Janus Engine | External Opponent | Engine Type | Games | Score | Score (%) | Elo | Paired 95% CI | Incident Rate |
|---|---|---|---|---|---|---|---|---|---|
| **Match 5** | X20-S (1T) | Stockfish 4 | Classical Historical | 40 | 1.5 / 40 | 3.75% | -563.7 | $[0.00\%, 7.76\%]$ | 0.0% |
| **Match 6** | X20-S (1T) | Stockfish 11 | Classical Peak | 40 | 0.5 / 40 | 1.25% | -759.1 | $[0.00\%, 3.70\%]$ | 0.0% |
| **Match 7** | X20-S (1T) | Stockfish 19 | Modern NNUE | 40 | 0.5 / 40 | 1.25% | -759.1 | $[0.00\%, 3.70\%]$ | 0.0% |

### Synthesis:
The external benchmarks clearly demonstrate that search-tree reductions (such as X20's 98% node reduction) cannot overcome fundamental evaluation knowledge deficits. Classical engine progress in Phase 1 must focus on positional and tactical evaluation accuracy rather than further aggressive move-ordering pruning.

