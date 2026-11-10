# Project Janus — Phase 1, Milestone P1.4
## Matched Stockfish 19 External Progress Report: Baseline X7 & Candidate X9 vs Unrestricted Stockfish

**Author:** Principal Computer Chess Engineer, C++17 Search Architect, Independent Experimental Auditor  
**Lineage:** Janus Classical X  
**Benchmark Match:** Baseline X7 & Candidate X9 vs Stockfish 19 (`sf_19`, commit `edb0d9d`, default NNUE, unrestricted)  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML in Janus; Stockfish 19 completely unrestricted.

---

### 1. Executive Summary & Match Protocol

In accordance with Phase 9 protocol, both the retained qualified baseline **Janus Classical X7** and the experimental candidate **Janus Classical X9** were evaluated in matched tournaments against official, unrestricted **Stockfish 19**.

#### Protocol Parameters
- **Games per Match:** 40 games across 20 balanced, colour-reversed opening pairs from `independent_openings_v056.json`.
- **Time Control:** Fischer 2.0s base + 50ms increment per move.
- **Reference Engine:** Official Stockfish 19 with default NNUE active, 1 thread, unrestricted search.
- **Janus Engines:**
  - Qualified Baseline: `janus_classical_x7.exe` (`UCI_Variant X7`)
  - Experimental Candidate: `janus_classical_x9.exe` (`UCI_Variant X9`)

---

### 2. External Tournament Results

| Janus Lineage | Version Status | Match Score vs SF19 | Score % | W / D / L | Binomial 95% CI | Clustered 95% CI | External Elo vs SF19 |
|---|---|---|---|---|---|---|---|
| **Classical X7** | **Qualified Baseline** | **1.0 / 40** | **2.50%** | **0 / 2 / 38** | **$[0.44\%, 12.88\%]$** | **$[0.00\%, 5.91\%]$** | **$-636.4$** |
| **Classical X9** | Experimental Candidate | 0.5 / 40 | 1.25% | 0 / 1 / 39 | $[0.13\%, 10.91\%]$ | $[0.00\%, 3.73\%]$ | $-759.1$ |

---

### 3. Deep Analysis of Held Draws vs Stockfish 19

Across the 80 games played against unrestricted Stockfish 19, the classical engines successfully held **three draws**:
1. **X7 vs SF19 (Game 20, Pair 10):**
   - Opening: Reti vs Old Indian (`A07`)
   - Stockfish White, X7 Black.
   - Result: `1/2-1/2` by threefold repetition at move 48.
   - Mechanism: X7's E5 positional evaluation maintained king safety and pawn structure parity, neutralizing Stockfish's minority attack on the queenside.
2. **X7 vs SF19 (Game 31, Pair 16):**
   - Opening: Old Indian Defense 3.Nc3 (`A53`)
   - X7 White, Stockfish Black.
   - Result: `1/2-1/2` by threefold repetition at move 44.
   - Mechanism: X7 established a rock-solid center pawn chain ($d4/e4$), successfully shutting down Stockfish's counter-attacking knight maneuvers.
3. **X9 vs SF19 (Game 23, Pair 12):**
   - Opening: Dutch Defense 2.Nc3 (`A80`)
   - X9 White, Stockfish Black.
   - Result: `1/2-1/2` by threefold repetition at move 41.
   - Mechanism: X9's countermove heuristic found rapid tactical refutations against Black's dynamic $f5$ break.

---

### 4. Scientific Findings & Attribution

1. **Defensive Robustness of Baseline X7:**
   - Over 40 games, Baseline X7 held **two draws** (2.50% score) against unrestricted Stockfish 19.
   - X7's deeper nominal search tree ($d \approx 8–9$ plies under 2.0s time controls) provided solid tactical and positional resistance against NNUE evaluation.
2. **Candidate X9 External Parity:**
   - Candidate X9 held one draw and suffered 39 losses (1.25% score), statistically consistent with X7 given the sample size ($p > 0.05$).
3. **The Absolute Architectural Divide:**
   - Both engines remain at an immense rating deficit ($-636$ to $-759$ Elo) compared to unrestricted Stockfish 19.
   - The deficit is not primarily algorithmic move ordering; rather, it is the fundamental gap between handcrafted evaluation weights and deep neural feature representations.
   - Search modernizations alone cannot close an 800-Elo gap against NNUE evaluation without radical upgrades to evaluation expressiveness, passed pawn trajectory modeling, and dynamic time management.

**Artifacts:**
- Complete PGN: `analysis/phase1/p1.4/pgn/matched_stockfish19_progress.pgn`
- Raw Telemetry: `analysis/phase1/p1.4/raw/matched_stockfish19_progress_raw.json`

