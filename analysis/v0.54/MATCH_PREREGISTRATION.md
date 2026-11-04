# PROJECT JANUS v0.54 — TOURNAMENT MATCH PREREGISTRATION

**Document Type:** Formal Experimental Preregistration  
**Milestone:** v0.54  
**Date:** 2026-11-05  
**Protocol:** Controlled Head-to-Head Strength Ablation (Candidate N5 C3 vs. Baseline N3 C0)  

---

## 1. Experimental Objective

Evaluate whether native move ordering intelligence (two killer move slots per ply plus a saturated history heuristic) confers a statistically significant playing-strength improvement over the frozen production baseline Janus Native N3 under strict Fischer time controls and verified FIDE tournament adjudications.

This match protocol is preregistered prior to conducting the tournament to prevent post-hoc bias or selective reporting.

---

## 2. Competing Engine Configurations

Both configurations execute using the identical native binary `janus_native_engine.exe`, parameterized exclusively via UCI options prior to each game:

### Control: Janus Native N3 (C0 Baseline)
- **Binary:** `janus_native_engine.exe` (SHA-256: `09ca0f64df9dcfc0d23da9a3b47821a296ba95ff70ab94ddc0f545472cf35737`)
- **UCI Options:**
  - `setoption name UseKillerOrdering value false`
  - `setoption name UseHistoryOrdering value false`
  - `setoption name UseLMR value true`
  - `setoption name UsePVS value false`
  - `setoption name LMRMinDepth value 3`
  - `setoption name LMRMoveThreshold value 4`
  - `setoption name LMRBaseReduction value 1`

### Candidate: Janus Native N5 (C3 Combined)
- **Binary:** `janus_native_engine.exe` (SHA-256: `09ca0f64df9dcfc0d23da9a3b47821a296ba95ff70ab94ddc0f545472cf35737`)
- **UCI Options:**
  - `setoption name UseKillerOrdering value true`
  - `setoption name UseHistoryOrdering value true`
  - `setoption name UseLMR value true`
  - `setoption name UsePVS value false`
  - `setoption name LMRMinDepth value 3`
  - `setoption name LMRMoveThreshold value 4`
  - `setoption name LMRBaseReduction value 1`

---

## 3. Cryptographic Artifact Integrity

| Component | Path | SHA-256 Checksum |
| :--- | :--- | :--- |
| **C++ Search Engine Source** | `analysis/v0.54/native/janus_native.cpp` | `fa3bdf7193af49c75910915d5d3a92a19fb02436a3ae5b9f799647fd29d5ae6a` |
| **Engine Binary** | `analysis/v0.54/native/janus_native_engine.exe` | `09ca0f64df9dcfc0d23da9a3b47821a296ba95ff70ab94ddc0f545472cf35737` |
| **Engine Shared Library** | `analysis/v0.54/native/janus_native.dll` | `59bea0b3bb95795b901cddd99e8510c68031277546e9deed82ac597db32861fe` |
| **Opening Suite (100 pairs)** | `analysis/v0.54/corpus/openings_v052_100.json` | `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b` |
| **Tournament Controller** | `analysis/v0.54/tests/tournament_controller.py` | `d46f868c8d7789c8593f7a5bf47e3509a7cee53dcc8b1fc78ccb21be10dbc9fe` |

---

## 4. Tournament Structure & Rules

- **Total Rounds:** 100 opening pairs (200 total games).
- **Color Inversion:** Strict alternating colors per pair:
  - Game 1: White = C3 (N5), Black = C0 (N3).
  - Game 2: White = C0 (N3), Black = C3 (N5).
- **Time Control:** Fischer 3.0s base + 100ms increment (`wtime 3000 btime 3000 winc 100 binc 100`).
- **Opening Corpus:** 100 balanced openings (2 to 4 plies) from `openings_v052_100.json`.
- **Transposition Table:** Reset via `ucinewgame` before every single game.
- **Killer & History Reset:** Reset via `ucinewgame` before every single game.
- **Adjudication Engine:** `tournament_controller.py`:
  - FIDE Checkmate (1-0 / 0-1)
  - FIDE Stalemate (1/2-1/2)
  - FIDE Insufficient Material (1/2-1/2)
  - FIDE Threefold Repetition Claim (1/2-1/2)
  - FIDE Fivefold Repetition Mandatory (1/2-1/2)
  - FIDE 50-Move Rule Claim (1/2-1/2)
  - FIDE 75-Move Rule Mandatory (1/2-1/2)
  - Emergency Circuit Breaker: 300 plies (150 full moves) without termination $\rightarrow$ Draw (`safety_limit_300_plies`).
- **Parallelization:** 8 worker processes on the 16-thread host architecture.

---

## 5. Statistical Hypotheses & Success Criteria

- **Null Hypothesis ($H_0$):** Improved move ordering does not improve playing strength ($\Delta \text{Elo} \le 0$, mean paired difference $\mu_d \le 0$).
- **Alternative Hypothesis ($H_1$):** Improved move ordering improves playing strength ($\Delta \text{Elo} > 0$, $\mu_d > 0$).
- **Primary Metric:** Paired opening-difference score:
  $$d_i = \text{Score}_{C3, i} - \text{Score}_{C0, i} \in \{-2, -1.5, -1, -0.5, 0, +0.5, +1, +1.5, +2\}$$
- **Significance Test:** Two-sided Student's paired $t$-test ($df = 99$), with $\alpha = 0.05$.
- **Secondary Evaluation:** 100,000 paired bootstrap resamples to establish the 95% confidence interval of the mean point delta and Elo advantage.
- **Promotion Threshold:** Only Category A ($\mu_d > 0, p < 0.05$, CI lower bound $> 0$) authorizes promoting C3 to production default.

